from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .discord_integration import DISCORD_STATE_SESSION_KEY, DiscordIntegrationError
from .models import Notification, Participant, StreamingAccount
from .streaming import TWITCH_STATE_SESSION_KEY


@override_settings(
    DEBUG=False,
    SITE_PUBLIC_URL="https://dev.example.test",
    DISCORD_CLIENT_ID="80351110224678912",
    DISCORD_CLIENT_SECRET="fixture-secret",
    DISCORD_REDIRECT_URI="https://dev.example.test/account/connections/discord/callback/",
    STREAMING_TOKEN_ENCRYPTION_KEY="fixture-key",
)
class ConnectionFeedbackTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create_user(
            "provider-test@example.invalid", "Connection fixture",
            status=Participant.Status.VERIFIED, is_active=True,
        )
        self.client.force_login(self.participant)
        self.settings_url = reverse("registry:account_settings")

    def assert_connection_alert(self, response, expected, title):
        self.assertRedirects(response, self.settings_url)
        alert = response.redirect_chain[-1] if hasattr(response, "redirect_chain") else None
        self.assertEqual(alert, (self.settings_url, 302))
        self.assertContains(response, f'role="alert">{expected}</p>')
        self.assertIn("no-store", response["Cache-Control"])
        self.assertTrue(Notification.objects.filter(
            recipient=self.participant, title=title, message=expected,
            destination=self.settings_url,
        ).exists())

    def test_invalid_discord_client_id_stays_on_settings(self):
        for client_id in ("", "placeholder", "１２３４５６７８９０１２３４５６７", "123",
                          "80351110224678912 ", "18446744073709551616"):
            with self.subTest(client_id=client_id), self.settings(DISCORD_CLIENT_ID=client_id):
                response = self.client.get(reverse("registry:connect_discord"), follow=True)
                self.assert_connection_alert(
                    response, "Discord connection is not configured.", "Discord connection unavailable",
                )
                self.assertNotIn(DISCORD_STATE_SESSION_KEY, self.client.session)

    def test_discord_rejects_unsafe_or_mismatched_callbacks(self):
        good = "https://dev.example.test/account/connections/discord/callback/"
        for callback in ("", "https://[", good.replace("https://", "http://"),
                         good.replace("dev.example.test", "other.example.test"),
                         good.replace("dev.example.test", "dev.example.test:8443"),
                         good.replace("dev.example.test", "user@dev.example.test"),
                         good.replace("connections/", "streaming/"),
                         good + "?extra=1", good + "#fragment", good + " ", good + "\n"):
            with self.subTest(callback=callback), self.settings(DISCORD_REDIRECT_URI=callback):
                response = self.client.get(reverse("registry:connect_discord"))
                self.assertRedirects(response, self.settings_url, fetch_redirect_response=False)
                self.assertNotIn(DISCORD_STATE_SESSION_KEY, self.client.session)

    def test_valid_discord_redirect_uses_exact_callback_and_identity_scope(self):
        response = self.client.get(reverse("registry:connect_discord"))
        self.assertEqual(response.status_code, 302)
        target = urlsplit(response.url)
        self.assertEqual((target.scheme, target.netloc, target.path), ("https", "discord.com", "/oauth2/authorize"))
        query = parse_qs(target.query)
        self.assertEqual(query["redirect_uri"], ["https://dev.example.test/account/connections/discord/callback/"])
        self.assertEqual(query["scope"], ["identify"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["state"], [self.client.session[DISCORD_STATE_SESSION_KEY]["value"]])
        self.assertNotIn("fixture-secret", response.url)

    def test_http_allowed_only_on_explicit_debug_loopback(self):
        path = "/account/connections/discord/callback/"
        for origin, debug, allowed in (
            ("http://127.0.0.1:8001", True, True),
            ("http://[::1]:8001", True, True),
            ("http://127.0.0.1:8001", False, False),
            ("http://dev.example.test", True, False),
            ("https://dev.example.test:", False, False),
            ("https://-bad.example.test", False, False),
        ):
            with self.subTest(origin=origin, debug=debug), self.settings(
                SITE_PUBLIC_URL=origin, DEBUG=debug, DISCORD_REDIRECT_URI=origin + path,
            ):
                response = self.client.get(reverse("registry:connect_discord"))
                self.assertEqual(response.url.startswith("https://discord.com/"), allowed)
                if allowed:
                    self.assertIn(DISCORD_STATE_SESSION_KEY, self.client.session)

    def test_callback_state_errors_alert_without_exchange_or_query_leaks(self):
        for provider in ("discord", "twitch"):
            label = provider.title()
            with self.subTest(provider=provider), patch(f"registry.views.exchange_{provider}_code") as exchange:
                response = self.client.get(reverse(f"registry:{provider}_callback"), {
                    "state": "private-state-marker", "code": "private-code-marker",
                    "error_description": "private-payload-marker",
                }, follow=True)
                self.assert_connection_alert(
                    response, f"The {label} connection request could not be verified.",
                    f"{label} was not connected",
                )
                exchange.assert_not_called()
                for marker in ("private-state-marker", "private-code-marker", "private-payload-marker"):
                    self.assertNotContains(response, marker)

    def test_duplicate_provider_ownership_alert_preserves_existing_link(self):
        other = Participant.objects.create_user("other@example.invalid", "Existing owner")
        fixtures = (
            ("discord", DISCORD_STATE_SESSION_KEY, "account", "fetch_discord_identity",
             {"id": "80351110224678912", "username": "fixture"}),
            ("twitch", TWITCH_STATE_SESSION_KEY, "channel", "validate_twitch_token",
             {"user_id": "80351110224678912", "login": "fixture"}),
        )
        for provider, state_key, thing, lookup, identity in fixtures:
            with self.subTest(provider=provider):
                existing = StreamingAccount.objects.create(
                    participant=other, provider=provider, provider_identity="80351110224678912",
                    display_name="Existing link",
                )
                session = self.client.session
                session[state_key] = {"value": "fixture-state", "created_at": timezone.now().timestamp()}
                session.save()
                with patch(f"registry.views.exchange_{provider}_code", return_value={"access_token": "token-marker"}), \
                        patch(f"registry.views.{lookup}", return_value=identity):
                    response = self.client.get(reverse(f"registry:{provider}_callback"), {
                        "state": "fixture-state", "code": "fixture-code",
                    }, follow=True)
                self.assert_connection_alert(
                    response, f"That {provider.title()} {thing} is already connected to another Rat Race account.",
                    f"{provider.title()} was not connected",
                )
                self.assertNotContains(response, "token-marker")
                self.assertFalse(StreamingAccount.objects.filter(participant=self.participant, provider=provider).exists())
                self.assertTrue(StreamingAccount.objects.filter(pk=existing.pk, participant=other).exists())
                self.assertNotIn(state_key, self.client.session)

    def test_settings_alert_escapes_feedback_and_is_shown_once(self):
        message = "<strong>Fixture alert</strong>"
        with patch("registry.views.begin_discord_authorization", side_effect=DiscordIntegrationError(message)):
            response = self.client.get(reverse("registry:connect_discord"), follow=True)
        alert = 'role="alert">&lt;strong&gt;Fixture alert&lt;/strong&gt;</p>'
        self.assertContains(response, alert)
        self.assertNotContains(response, message)
        self.assertNotContains(self.client.get(self.settings_url), alert)
