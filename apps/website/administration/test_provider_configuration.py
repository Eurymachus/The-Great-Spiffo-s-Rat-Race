from io import StringIO
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from registry.models import Participant
from .forms import ProviderConfigurationForm
from .models import ProviderConfiguration
from .provider_credentials import get_provider_credentials, ProviderConfigurationError, decrypt_secret

KEY = Fernet.generate_key().decode()
ORIGIN = 'https://dev.example.test'
ID = '80351110224678912'
SECRET = 'private-client-secret-marker'


@override_settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=KEY, SITE_PUBLIC_URL=ORIGIN,
                   DISCORD_CLIENT_ID=ID, DISCORD_CLIENT_SECRET='environment-secret',
                   DISCORD_REDIRECT_URI=ORIGIN + '/account/connections/discord/callback/',
                   STREAMING_TOKEN_ENCRYPTION_KEY=KEY)
class ProviderConfigurationTests(TestCase):
    def setUp(self):
        self.owner = Participant.objects.create_superuser('owner@example.invalid', 'Owner', 'test-password')
        self.client.force_login(self.owner)
        self.add_url = reverse('admin:administration_providerconfiguration_add')
        self.data = dict(provider='discord', source='database', client_id=ID,
                         redirect_uri=ORIGIN + reverse('registry:discord_callback'), replacement_secret=SECRET)

    def create_record(self):
        response = self.client.post(self.add_url, self.data)
        self.assertEqual(response.status_code, 302)
        return ProviderConfiguration.objects.get(provider='discord')

    def change_url(self, record):
        return reverse('admin:administration_providerconfiguration_change', args=(record.pk,))

    def test_save_encrypted_secret_never_rendered_or_audited(self):
        record = self.create_record()
        self.assertNotIn(SECRET, record.encrypted_secret)
        self.assertEqual(decrypt_secret(record), SECRET)
        self.assertEqual(get_provider_credentials('discord').client_secret, SECRET)
        self.assertNotIn(SECRET, repr(get_provider_credentials('discord')))
        for url in (self.change_url(record), reverse('admin:administration_providerconfiguration_history', args=(record.pk,)), reverse('admin:administration_providerconfiguration_changelist')):
            page = self.client.get(url)
            self.assertEqual(page.status_code, 200)
            self.assertNotContains(page, SECRET)
            self.assertNotContains(page, record.encrypted_secret)
        entry = LogEntry.objects.filter(user=self.owner).latest('id')
        self.assertIn('replacement_secret', entry.change_message)
        self.assertNotIn(SECRET, entry.change_message)

    def test_staff_with_all_model_permissions_is_denied_get_and_post(self):
        record = self.create_record()
        staff = Participant.objects.create_user('staff@example.invalid', 'Staff', is_staff=True)
        staff.user_permissions.set(Permission.objects.filter(content_type__app_label='administration'))
        self.client.force_login(staff)
        urls = [self.add_url, self.change_url(record), reverse('admin:administration_providerconfiguration_changelist'), reverse('admin:administration_providerconfiguration_history', args=(record.pk,)), reverse('admin:administration_providerconfiguration_delete', args=(record.pk,))]
        for url in urls:
            for method in (self.client.get, self.client.post):
                with self.subTest(url=url, method=method.__name__):
                    self.assertEqual(method(url, self.data if method == self.client.post else {}).status_code, 403)
        self.assertNotContains(self.client.get(reverse('admin:index')), 'Provider configurations')
        self.assertEqual(ProviderConfiguration.objects.count(), 1)

    def test_anonymous_nonstaff_and_inactive_are_blocked(self):
        for user in (None, Participant.objects.create_user('normal@example.invalid', 'Normal'), Participant.objects.create_user('inactive@example.invalid', 'Inactive', is_superuser=True, is_staff=True, is_active=False)):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.post(self.add_url, self.data).status_code, 302)
        self.assertFalse(ProviderConfiguration.objects.exists())

    def test_blank_preserves_secret_and_replacement_applies_immediately(self):
        record = self.create_record()
        initial = record.encrypted_secret
        for secret, expected in (('', SECRET), ('new-secret-marker', 'new-secret-marker')):
            response = self.client.post(self.change_url(record), {**self.data, 'replacement_secret': secret})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(get_provider_credentials('discord').client_secret, expected)
            record.refresh_from_db()
            if not secret:
                self.assertEqual(record.encrypted_secret, initial)

    def test_invalid_form_never_echoes_secret(self):
        response = self.client.post(self.add_url, {**self.data, 'redirect_uri': 'https://evil.example/callback'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'exact provider callback')
        self.assertNotContains(response, SECRET)
        self.assertFalse(ProviderConfiguration.objects.exists())

    def test_invalid_ids_callbacks_and_missing_key_rejected(self):
        for field, value in [('client_id','placeholder'), ('redirect_uri',self.data['redirect_uri']+'?extra=1'), ('replacement_secret','')]:
            form = ProviderConfigurationForm(data={**self.data,field:value})
            self.assertFalse(form.is_valid(), field)
        with self.settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=''):
            self.assertFalse(ProviderConfigurationForm(data=self.data).is_valid())

    def test_wrong_key_corruption_and_foreign_origin_fail_closed(self):
        record = self.create_record()
        with self.settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=Fernet.generate_key().decode()):
            with self.assertRaises(ProviderConfigurationError):
                get_provider_credentials('discord')
        with self.settings(SITE_PUBLIC_URL='https://live.example.test'):
            with self.assertRaises(ProviderConfigurationError):
                get_provider_credentials('discord')
        record.encrypted_secret = 'corrupted'
        record.save()
        with self.assertRaises(ProviderConfigurationError):
            get_provider_credentials('discord')
        response = self.client.get(reverse('registry:connect_discord'), follow=True)
        self.assertContains(response, 'configuration is unavailable')

    def test_ciphertext_is_bound_to_provider_and_origin(self):
        record = self.create_record()
        record.provider = 'twitch'
        with self.assertRaises(ProviderConfigurationError):
            decrypt_secret(record)
        record.provider = 'discord'
        record.site_origin = 'https://live.example.test'
        with self.assertRaises(ProviderConfigurationError):
            decrypt_secret(record)

    def test_explicit_environment_and_disabled_modes(self):
        self.assertEqual(get_provider_credentials('discord').client_secret, 'environment-secret')
        record = self.create_record()
        for source, expected in [('disabled',''), ('environment','environment-secret'), ('database',SECRET)]:
            response = self.client.post(self.change_url(record), {**self.data,'source':source,'replacement_secret':''})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(get_provider_credentials('discord').client_secret, expected)

    def test_client_id_change_requires_secret_and_provider_is_immutable(self):
        record = self.create_record()
        response = self.client.post(self.change_url(record), {**self.data,'provider':'twitch','client_id':'80351110224678913','replacement_secret':''})
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.provider, 'discord')
        self.assertEqual(record.client_id, ID)

    def test_csrf_and_delete_protection(self):
        record = self.create_record()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.change_url(record), self.data).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:administration_providerconfiguration_delete', args=(record.pk,)), {'post':'yes'}).status_code,403)
        self.assertTrue(ProviderConfiguration.objects.exists())

    def test_import_and_rotation_round_trip_and_audit(self):
        output = StringIO()
        call_command('provider_configuration','import',provider=['discord'],actor=self.owner.email,stdout=output)
        self.assertEqual(get_provider_credentials('discord').client_secret,'environment-secret')
        old = ProviderConfiguration.objects.get().encrypted_secret
        new_key = Fernet.generate_key().decode()
        with self.settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=new_key+','+KEY):
            call_command('provider_configuration','rotate',provider=['discord'],actor=self.owner.email,stdout=output)
        with self.settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=new_key):
            call_command('provider_configuration','check',provider=['discord'],stdout=output)
            self.assertEqual(get_provider_credentials('discord').client_secret,'environment-secret')
        self.assertNotEqual(ProviderConfiguration.objects.get().encrypted_secret,old)
        self.assertEqual(LogEntry.objects.filter(user=self.owner).count(),2)
        self.assertNotIn('environment-secret',output.getvalue())
        with self.assertRaises(CommandError):
            call_command('provider_configuration','import',provider=['discord'],actor=self.owner.email,stdout=output)

    def test_import_is_atomic_when_later_provider_is_invalid(self):
        with self.settings(TWITCH_CLIENT_ID='bad'), self.assertRaises(CommandError):
            call_command('provider_configuration','import',provider=['discord','twitch'],actor=self.owner.email,stdout=StringIO())
        self.assertFalse(ProviderConfiguration.objects.exists())

    def test_runtime_exchange_uses_database_credentials(self):
        self.create_record()
        from registry.discord_integration import exchange_discord_code
        with patch('registry.discord_integration._json_request',return_value={}) as request:
            exchange_discord_code('synthetic-code')
        self.assertEqual(request.call_args.kwargs['data']['client_secret'],SECRET)

    def test_all_provider_exchanges_use_database_secret_and_disabled_blocks_network(self):
        from importlib import import_module
        for provider, client_id, module_name in (
            ('discord', ID, 'discord_integration'),
            ('twitch', 'abcdefghij1234567890', 'streaming'),
            ('youtube', '12345-test.apps.googleusercontent.com', 'youtube_integration'),
        ):
            form = ProviderConfigurationForm(data={
                'provider': provider, 'source': 'database', 'client_id': client_id,
                'redirect_uri': ORIGIN + reverse(f'registry:{provider}_callback'),
                'replacement_secret': SECRET,
            })
            self.assertTrue(form.is_valid(), form.errors)
            record = form.save()
            module = import_module('registry.' + module_name)
            exchange = getattr(module, f'exchange_{provider}_code')
            with patch.object(module, '_json_request', return_value={}) as request:
                exchange('fixture-code')
                self.assertEqual(request.call_args.kwargs['data']['client_secret'], SECRET)
                record.source = 'disabled'
                record.save()
                request.reset_mock()
                with self.assertRaises(Exception) as caught:
                    exchange('fixture-code')
                self.assertIn('configuration is unavailable', str(caught.exception))
                request.assert_not_called()

    def test_change_form_uses_native_save_and_blank_password_field(self):
        record = self.create_record()
        response = self.client.get(self.change_url(record))
        self.assertContains(response, 'dataset.adminSaveBypass = "true"')
        self.assertContains(response, 'type="password"')
        self.assertNotContains(response, 'value="' + SECRET + '"')


    def store_integration(self, provider, **values):
        form = ProviderConfigurationForm(data={
            'provider': provider, 'source': 'database', 'replacement_secret': SECRET, **values,
        })
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_graph_uses_database_client_tenant_and_secret(self):
        from config.graph_email import MicrosoftGraphEmailBackend
        from config.test_graph_email import Response
        tenant = '12345678-1234-1234-1234-123456789012'
        client = '87654321-1234-1234-1234-123456789012'
        self.store_integration('graph', client_id=client, tenant_id=tenant)
        with patch('config.graph_email.request.urlopen', return_value=Response(b'{"access_token":"fixture"}')) as send:
            self.assertEqual(MicrosoftGraphEmailBackend()._token(), 'fixture')
        request = send.call_args.args[0]
        self.assertIn(tenant, request.full_url)
        self.assertIn(SECRET.encode(), request.data)
        self.assertIn(client.encode(), request.data)

    def test_turnstile_uses_database_site_key_and_secret_and_fails_closed(self):
        from registry.turnstile import validate_turnstile, turnstile_site_key
        from config.test_graph_email import Response
        site_key = 'real-site-key-fixture-12345'
        record = self.store_integration('turnstile', client_id=site_key)
        self.assertEqual(turnstile_site_key(), site_key)
        with patch('registry.turnstile.urlopen', return_value=Response(b'{"success":true}')) as send:
            self.assertTrue(validate_turnstile('response-token', '127.0.0.1'))
            self.assertIn(SECRET.encode(), send.call_args.args[0].data)
            record.source = 'disabled'
            record.save()
            send.reset_mock()
            self.assertFalse(validate_turnstile('response-token', '127.0.0.1'))
            self.assertEqual(turnstile_site_key(), '')
            send.assert_not_called()

    def test_openai_and_steam_use_database_api_keys(self):
        from registry.avatar_moderation import moderate_avatar
        from registry.steam_workshop import search_project_zomboid_workshop_items
        from config.test_graph_email import Response
        self.store_integration('openai')
        self.store_integration('steam')
        with patch('registry.avatar_moderation.request.urlopen', return_value=Response(b'{"results":[{"flagged":false}]}')) as send:
            self.assertEqual(moderate_avatar(b'fixture')[0], 'approved')
            self.assertEqual(send.call_args.args[0].get_header('Authorization'), 'Bearer ' + SECRET)
        with patch('registry.steam_workshop.urlopen', return_value=Response(b'{"response":{}}')) as send:
            self.assertEqual(search_project_zomboid_workshop_items('fixture'), [])
            self.assertIn('key='+SECRET, send.call_args.args[0].full_url)

    def test_unreadable_openai_queues_manual_review_and_steam_fails_safely(self):
        from registry.avatar_moderation import moderate_avatar
        from registry.steam_workshop import search_project_zomboid_workshop_items, SteamWorkshopError
        self.store_integration('openai')
        self.store_integration('steam')
        with self.settings(PROVIDER_CONFIG_ENCRYPTION_KEYS=''), patch('registry.avatar_moderation.request.urlopen') as send:
            self.assertEqual(moderate_avatar(b'fixture')[0], 'pending')
            send.assert_not_called()
            with self.assertRaises(SteamWorkshopError):
                search_project_zomboid_workshop_items('fixture')

    def test_live_cannot_save_turnstile_test_credentials(self):
        with self.settings(DEBUG=False, STAGING_ENVIRONMENT=False):
            form = ProviderConfigurationForm(data={
                'provider':'turnstile', 'source':'database', 'client_id':'1x00000000000000000000AA',
                'replacement_secret':'1x0000000000000000000000000000000AA',
            })
            self.assertFalse(form.is_valid())


    def test_all_seven_environment_imports_and_checks_are_audited(self):
        with self.settings(
            TWITCH_CLIENT_ID='abcdefghij1234567890', TWITCH_CLIENT_SECRET=SECRET,
            TWITCH_REDIRECT_URI=ORIGIN + reverse('registry:twitch_callback'),
            YOUTUBE_CLIENT_ID='123-test.apps.googleusercontent.com', YOUTUBE_CLIENT_SECRET=SECRET,
            YOUTUBE_REDIRECT_URI=ORIGIN + reverse('registry:youtube_callback'),
            MICROSOFT_GRAPH_CLIENT_ID='87654321-1234-1234-1234-123456789012',
            MICROSOFT_GRAPH_TENANT_ID='12345678-1234-1234-1234-123456789012',
            MICROSOFT_GRAPH_CLIENT_SECRET=SECRET,
            TURNSTILE_SITE_KEY='real-site-key-fixture-12345', TURNSTILE_SECRET_KEY=SECRET,
            OPENAI_API_KEY=SECRET, STEAM_WEB_API_KEY=SECRET,
        ):
            output = StringIO()
            call_command('provider_configuration', 'import', actor=self.owner.email, stdout=output)
            call_command('provider_configuration', 'check', stdout=output)
            self.assertEqual(ProviderConfiguration.objects.count(), 7)
            self.assertEqual(LogEntry.objects.filter(user=self.owner).count(), 7)
            self.assertNotIn(SECRET, output.getvalue())
            for record in ProviderConfiguration.objects.all():
                response = self.client.get(self.change_url(record))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, record.encrypted_secret)
                self.assertNotContains(response, SECRET)
                data = {'source': 'database', 'replacement_secret': '', 'client_id': record.client_id,
                        'tenant_id': record.tenant_id, 'redirect_uri': record.redirect_uri}
                self.assertEqual(self.client.post(self.change_url(record), data).status_code, 302)



class ProviderEnvironmentTests(TestCase):
    def test_database_key_allows_removing_provider_environment_credentials(self):
        from config.tests import valid_environment
        from config.production_environment import validate_production_environment
        environment = valid_environment()
        for name in ('MICROSOFT_GRAPH_CLIENT_ID', 'MICROSOFT_GRAPH_CLIENT_SECRET', 'MICROSOFT_GRAPH_TENANT_ID', 'TURNSTILE_SITE_KEY', 'TURNSTILE_SECRET_KEY', 'OPENAI_API_KEY', 'STEAM_WEB_API_KEY'):
            environment.pop(name)
        for provider in ('DISCORD', 'TWITCH', 'YOUTUBE'):
            for suffix in ('CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI'):
                environment.pop(f'{provider}_{suffix}')
        with self.assertRaises(RuntimeError):
            validate_production_environment(environment)
        environment['PROVIDER_CONFIG_ENCRYPTION_KEYS'] = KEY
        validate_production_environment(environment)
        environment['PROVIDER_CONFIG_ENCRYPTION_KEYS'] = 'bad-key'
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_CONFIG_ENCRYPTION_KEYS'):
            validate_production_environment(environment)
