import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

from cryptography.fernet import Fernet

from .production_environment import (
    TURNSTILE_TEST_SITE_KEY,
    validate_production_environment,
)


def valid_environment():
    return {
        "DJANGO_SECRET_KEY": "a-strong-production-secret-key-with-more-than-fifty-characters",
        "DJANGO_ALLOWED_HOSTS": "tgsrr.com,www.tgsrr.com",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://tgsrr.com,https://www.tgsrr.com",
        "SITE_PUBLIC_URL": "https://tgsrr.com",
        "POSTGRES_DB": "rat_race",
        "POSTGRES_USER": "rat_race",
        "POSTGRES_PASSWORD": "database-secret",
        "POSTGRES_HOST": "database",
        "POSTGRES_PORT": "5432",
        "REDIS_URL": "redis://cache:6379/0",
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": "mailer",
        "EMAIL_HOST_PASSWORD": "mail-secret",
        "DEFAULT_FROM_EMAIL": "Rat Race <no-reply@tgsrr.com>",
        "TURNSTILE_SITE_KEY": "live-site-key",
        "TURNSTILE_SECRET_KEY": "live-secret-key",
        "OPENAI_API_KEY": "openai-key",
        "STREAMING_TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
        "TWITCH_CLIENT_ID": "twitch-id",
        "TWITCH_CLIENT_SECRET": "twitch-secret",
        "TWITCH_REDIRECT_URI": "https://tgsrr.com/account/streaming/twitch/callback/",
        "DISCORD_CLIENT_ID": "discord-id",
        "DISCORD_CLIENT_SECRET": "discord-secret",
        "DISCORD_REDIRECT_URI": "https://tgsrr.com/account/connections/discord/callback/",
        "YOUTUBE_CLIENT_ID": "youtube-id",
        "YOUTUBE_CLIENT_SECRET": "youtube-secret",
        "YOUTUBE_REDIRECT_URI": "https://tgsrr.com/account/streaming/youtube/callback/",
        "STEAMCMD_EXECUTABLE": "/opt/steamcmd/steamcmd.sh",
        "STEAMCMD_USERNAME": "steam-user",
        "STEAM_WEB_API_KEY": "steam-api-key",
        "PZ_REFERENCE_ROOT": "/srv/tgsrr/reference",
        "JAVA_EXECUTABLE": "/srv/tgsrr/reference/jre64/bin/java",
        "VINEFLOWER_JAR": "/opt/vineflower/vineflower.jar",
        "PZ_DECOMPILED_ROOT": "/srv/tgsrr/decompiled",
        "STATIC_ROOT": "/srv/tgsrr/static",
        "MEDIA_ROOT": "/srv/tgsrr/media",
        "AVATAR_QUARANTINE_ROOT": "/srv/tgsrr/private/avatars",
        "RELEASE_ID": "abcdef12",
    }


class ProductionEnvironmentTests(TestCase):
    def test_complete_environment_is_normalised(self):
        result = validate_production_environment(valid_environment())

        self.assertEqual(result["postgres_port"], 5432)
        self.assertEqual(result["email_port"], 587)
        self.assertEqual(result["postgres_conn_max_age"], 60)
        self.assertEqual(result["secure_hsts_seconds"], 3600)
        self.assertTrue(result["email_use_tls"])
        self.assertTrue(result["trust_cloudflare_connecting_ip"])
        self.assertEqual(result["allowed_hosts"], ["tgsrr.com", "www.tgsrr.com"])

    def test_missing_variables_are_reported_by_name_without_values(self):
        environment = valid_environment()
        del environment["POSTGRES_PASSWORD"]
        del environment["VINEFLOWER_JAR"]

        with self.assertRaisesRegex(
            RuntimeError, "POSTGRES_PASSWORD, VINEFLOWER_JAR"
        ):
            validate_production_environment(environment)

    def test_turnstile_test_credentials_are_rejected(self):
        environment = valid_environment()
        environment["TURNSTILE_SITE_KEY"] = TURNSTILE_TEST_SITE_KEY

        with self.assertRaisesRegex(RuntimeError, "localhost test key"):
            validate_production_environment(environment)

    def test_invalid_encryption_key_is_rejected(self):
        environment = valid_environment()
        environment["STREAMING_TOKEN_ENCRYPTION_KEY"] = "not-a-fernet-key"

        with self.assertRaisesRegex(RuntimeError, "valid Fernet key"):
            validate_production_environment(environment)

    def test_production_urls_must_use_https(self):
        environment = valid_environment()
        environment["DISCORD_REDIRECT_URI"] = "http://tgsrr.com/callback/"

        with self.assertRaisesRegex(RuntimeError, "DISCORD_REDIRECT_URI"):
            validate_production_environment(environment)

    def test_public_host_must_be_allowed(self):
        environment = valid_environment()
        environment["DJANGO_ALLOWED_HOSTS"] = "internal.example.com"

        with self.assertRaisesRegex(RuntimeError, "SITE_PUBLIC_URL host"):
            validate_production_environment(environment)

    def test_development_secret_key_is_rejected(self):
        environment = valid_environment()
        environment["DJANGO_SECRET_KEY"] = "django-insecure-not-for-production"

        with self.assertRaisesRegex(RuntimeError, "production-only"):
            validate_production_environment(environment)


class ProductionSettingsImportTests(TestCase):
    def test_complete_environment_loads_production_settings(self):
        website_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment.update(valid_environment())
        environment["DJANGO_SETTINGS_MODULE"] = "config.settings_production"
        environment["PYTHONPATH"] = str(website_root)

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import django; django.setup(); "
                "from django.conf import settings; "
                "print(settings.DEBUG, settings.RELEASE_ID, "
                "'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE)",
            ],
            cwd=website_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False abcdef12 True")
