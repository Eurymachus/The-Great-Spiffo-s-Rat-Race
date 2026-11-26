from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import URLError

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from operations.models import RateLimitBucket
from operations.runtime_state import rate_limit_exceeded
from .models import Participant


@override_settings(PASSWORD_RESET_IP_RATE_LIMIT=5, PASSWORD_RESET_EMAIL_RATE_LIMIT=3)
class PasswordResetDeliveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Participant.objects.create_user(
            email="reset@example.com", nickname="ResetTester", password="Original-pass-123!",
            status=Participant.Status.VERIFIED, is_active=True,
        )
        self.url = reverse("registry:password_reset")
        self.turnstile = patch("registry.views.validate_turnstile", return_value=True)
        self.turnstile.start()
        self.addCleanup(self.turnstile.stop)

    @override_settings(
        EMAIL_BACKEND="config.staging_email.AllowlistedStagingEmailBackend",
        STAGING_EMAIL_ALLOW_ALL=False, STAGING_EMAIL_ALLOWLIST=set(), DEBUG=False,
    )
    def test_blocked_staging_delivery_is_generic_and_never_calls_provider(self):
        with patch("config.graph_email.MicrosoftGraphEmailBackend.send_messages") as provider:
            with self.assertLogs("registry.views", level="WARNING") as logs:
                response = self.client.post(self.url, {"email": self.user.email})
            unknown = self.client.post(self.url, {"email": "unknown@example.com"})
        self.assertContains(response, "If an active participant account exists")
        self.assertContains(unknown, "If an active participant account exists")
        self.assertFalse(provider.called)
        self.assertNotIn(self.user.email, " ".join(logs.output))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-pass-123!"))

    def test_provider_failure_does_not_expose_error_or_debug_reset_link(self):
        with self.settings(DEBUG=True), patch(
            "registry.views.send_password_reset_email", side_effect=URLError("private-provider-detail"),
        ), self.assertLogs("registry.views", level="WARNING") as logs:
            response = self.client.post(self.url, {"email": self.user.email})
        self.assertContains(response, "If an active participant account exists")
        self.assertIsNone(response.context["development_reset_url"])
        self.assertNotIn("private-provider-detail", " ".join(logs.output))

    def test_retry_time_uses_later_bucket_and_does_not_slide_on_retries(self):
        start = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)
        for backend in ("database", "cache"):
            with self.subTest(backend=backend), self.settings(RUNTIME_STATE_BACKEND=backend):
                cache.clear()
                RateLimitBucket.objects.all().delete()
                with patch("django.utils.timezone.now", return_value=start), patch("time.time", return_value=start.timestamp()):
                    for _ in range(5):
                        rate_limit_exceeded("password-reset-ip", "127.0.0.1", 5, 3600)
                with patch("django.utils.timezone.now", return_value=start + timedelta(minutes=10)), patch("time.time", return_value=(start + timedelta(minutes=10)).timestamp()):
                    for _ in range(3):
                        rate_limit_exceeded("password-reset-email", self.user.email, 3, 3600)
                for minute, remaining in ((20, 3000), (25, 2700)):
                    with patch("django.utils.timezone.now", return_value=start + timedelta(minutes=minute)), patch("time.time", return_value=(start + timedelta(minutes=minute)).timestamp()):
                        response = self.client.post(self.url, {"email": self.user.email})
                    self.assertContains(response, "19:10 UTC on 26 Nov", status_code=429)
                    self.assertEqual(response["Retry-After"], str(remaining))
                    self.assertIn("no-store", response["Cache-Control"])
                with patch("django.utils.timezone.now", return_value=start + timedelta(minutes=71)), patch("time.time", return_value=(start + timedelta(minutes=71)).timestamp()), patch(
                    "registry.views.send_password_reset_email",
                ) as send:
                    response = self.client.post(self.url, {"email": self.user.email})
                self.assertEqual(response.status_code, 200)
                send.assert_called_once()

    def test_email_limit_alone_displays_retry_time(self):
        with self.settings(RUNTIME_STATE_BACKEND="database", PASSWORD_RESET_EMAIL_RATE_LIMIT=1):
            with patch("registry.views.send_password_reset_email"):
                self.client.post(self.url, {"email": self.user.email})
                response = self.client.post(self.url, {"email": self.user.email})
        self.assertContains(response, "Try again after", status_code=429)
        self.assertGreater(int(response["Retry-After"]), 0)
