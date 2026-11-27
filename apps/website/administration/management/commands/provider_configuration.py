"""Operator-only import, verification and key rotation. Outputs contain no values."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from administration.models import ProviderConfiguration
from administration.provider_credentials import (
    ProviderConfigurationError, cipher, decrypt_secret, encrypt_secret,
    environment_credentials, get_provider_credentials, public_origin, validate_application,
)


class Command(BaseCommand):
    help = 'Import, check or rotate encrypted provider configuration without printing credentials.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=('import', 'check', 'rotate'))
        parser.add_argument('--provider', action='append', choices=ProviderConfiguration.Provider.values)
        parser.add_argument('--actor', help='Active superuser email for audited changes.')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            self.run(options)
        except (ProviderConfigurationError, ValidationError):
            raise CommandError('Provider configuration validation or encryption failed. No changes were committed.') from None

    def run(self, options):
        action = options['action']
        providers = options['provider'] or ProviderConfiguration.Provider.values
        actor = None
        if action != 'check':
            actor = get_user_model().objects.filter(email=options['actor'], is_active=True, is_superuser=True).first()
            if not actor:
                raise CommandError('An active superuser actor is required.')
            cipher()
        if not public_origin():
            raise CommandError('A valid public site origin is required.')
        for provider in providers:
            record = ProviderConfiguration.objects.select_for_update().filter(provider=provider).first()
            if action == 'import':
                if record:
                    raise CommandError('Import refused: a selected provider already has a record.')
                credentials = environment_credentials(provider)
                validate_application(provider, credentials.client_id, credentials.redirect_uri, credentials.tenant_id)
                if not credentials.client_secret.strip():
                    raise CommandError('Import refused: a selected provider has no environment secret.')
                record = ProviderConfiguration(
                    provider=provider, source='database', site_origin=public_origin(),
                    client_id=credentials.client_id, redirect_uri=credentials.redirect_uri, tenant_id=credentials.tenant_id,
                    encrypted_secret=encrypt_secret(provider, public_origin(), credentials.client_secret),
                )
                record.save()
            elif action == 'rotate':
                if not record or record.site_origin != public_origin() or not record.encrypted_secret:
                    raise CommandError('Rotation requires an encrypted record bound to this site.')
                record.encrypted_secret = encrypt_secret(provider, record.site_origin, decrypt_secret(record))
                record.save(update_fields=('encrypted_secret', 'updated_at'))
            else:
                credentials = get_provider_credentials(provider)
                if not credentials.client_secret:
                    raise CommandError('A selected provider is disabled or incomplete.')
                validate_application(provider, credentials.client_id, credentials.redirect_uri, credentials.tenant_id)
            if actor:
                LogEntry.objects.log_actions(
                    user_id=actor.pk, queryset=[record],
                    action_flag=ADDITION if action == 'import' else CHANGE,
                    change_message=f'Provider configuration {action}; credential values omitted.',
                    single_object=True,
                )
        self.stdout.write(self.style.SUCCESS(f'Provider configuration {action} succeeded for {len(providers)} provider(s).'))
