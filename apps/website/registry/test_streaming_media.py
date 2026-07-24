from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Participant, StreamingAccount, StreamingMedia
from .streaming import (
    decrypt_token,
    encrypt_token,
    refresh_twitch_media,
    refresh_twitch_token,
)


class TwitchMediaTests(TestCase):
    def setUp(self):
        self.token_key = Fernet.generate_key().decode("ascii")
        self.settings = override_settings(
            STREAMING_TOKEN_ENCRYPTION_KEY=self.token_key,
            TWITCH_CLIENT_ID="client-id",
            TWITCH_CLIENT_SECRET="client-secret",
            TWITCH_REDIRECT_URI="http://testserver/callback/",
            TWITCH_HTTP_TIMEOUT_SECONDS=5,
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.account = StreamingAccount.objects.create(
            participant=self.participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-user-42",
            display_name="streamer",
            channel_url="https://www.twitch.tv/streamer",
            encrypted_access_token=encrypt_token("old-access"),
            encrypted_refresh_token=encrypt_token("old-refresh"),
            token_validated_at=timezone.now(),
        )

    @patch("registry.streaming.validate_twitch_token")
    @patch("registry.streaming._json_request")
    def test_refresh_rotates_and_encrypts_credentials(self, request_json, validate):
        request_json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        validate.return_value = {
            "client_id": "client-id",
            "user_id": "twitch-user-42",
            "login": "streamer",
            "scopes": [],
            "expires_in": 3600,
        }

        token = refresh_twitch_token(self.account)

        self.account.refresh_from_db()
        self.assertEqual(token, "new-access")
        self.assertEqual(decrypt_token(self.account.encrypted_access_token), "new-access")
        self.assertEqual(
            decrypt_token(self.account.encrypted_refresh_token), "new-refresh"
        )
        self.assertNotIn("new-access", self.account.encrypted_access_token)

    @patch("registry.streaming._twitch_api")
    def test_refresh_caches_recent_broadcasts_and_clips(self, twitch_api):
        twitch_api.side_effect = [
            [
                {
                    "id": "video-1",
                    "title": "Rat Race attempt",
                    "url": "https://www.twitch.tv/videos/1",
                    "thumbnail_url": "https://example.test/%{width}x%{height}.jpg",
                    "published_at": "2026-07-24T10:00:00Z",
                    "duration": "1h2m3s",
                }
            ],
            [
                {
                    "id": "clip-1",
                    "video_id": "video-1",
                    "title": "Close escape",
                    "url": "https://clips.twitch.tv/close-escape",
                    "thumbnail_url": "https://example.test/clip.jpg",
                    "created_at": "2026-07-24T10:30:00Z",
                    "duration": 27.8,
                    "vod_offset": 1800,
                }
            ],
        ]

        counts = refresh_twitch_media(self.account)

        self.assertEqual(counts, (1, 1))
        video = StreamingMedia.objects.get(kind=StreamingMedia.Kind.VIDEO)
        clip = StreamingMedia.objects.get(kind=StreamingMedia.Kind.CLIP)
        self.assertEqual(video.duration_seconds, 3723)
        self.assertEqual(video.thumbnail_url, "https://example.test/640x360.jpg")
        self.assertEqual(clip.parent_media_id, "video-1")
        self.assertEqual(clip.vod_offset_seconds, 1800)

    @patch("registry.views.refresh_twitch_media", return_value=(3, 4))
    def test_participant_can_refresh_only_their_connected_channel(self, refresh):
        self.client.force_login(self.participant)

        response = self.client.post(reverse("registry:refresh_twitch_media"))

        self.assertRedirects(response, reverse("registry:submit_run"))
        refresh.assert_called_once_with(self.account)
