import tempfile
from pathlib import Path

from asgiref.sync import async_to_sync
from django.http import Http404
from django.test import AsyncRequestFactory, TestCase, override_settings
from django.urls import reverse

from .media import persistent_media


@override_settings(DEBUG=False, MEDIA_URL="/media/")
class PersistentMediaTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_root = Path(self.media_directory.name)
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def write_media(self, relative_path, content=b"media-content"):
        path = self.media_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    @staticmethod
    async def response_body(response):
        chunks = []
        async for chunk in response.streaming_content:
            chunks.append(chunk)
        return b"".join(chunks)

    def test_catalogue_png_is_served_without_redirect_under_production_settings(self):
        content = b"\x89PNG\r\n\x1a\nproduction-media"
        self.write_media(
            "catalogue/42.20/occupation/Profession_lumberjack.png",
            content,
        )

        response = self.client.get(
            "/media/catalogue/42.20/occupation/Profession_lumberjack.png"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_async)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "public, max-age=3600")
        self.assertEqual(async_to_sync(self.response_body)(response), content)

    def test_nested_branding_and_catalogue_media_are_served(self):
        for relative_path in (
            "branding/library/home/feature.png",
            "catalogue/42.20/trait/icons/Brave.png",
        ):
            with self.subTest(relative_path=relative_path):
                self.write_media(relative_path)
                response = self.client.get(f"/media/{relative_path}")
                self.assertEqual(response.status_code, 200)

    def test_missing_media_is_404_without_append_slash_redirect(self):
        response = self.client.get("/media/catalogue/missing.png")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Location", response)

    def test_traversal_and_symlink_escape_are_rejected(self):
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        outside = Path(outside_directory.name) / "secret.txt"
        outside.write_text("secret", encoding="utf-8")
        request = AsyncRequestFactory().get("/media/escape")

        with self.assertRaises(Http404):
            async_to_sync(persistent_media)(request, "../secret.txt")

        link = self.media_root / "escape.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            return
        response = self.client.get("/media/escape.txt")
        self.assertEqual(response.status_code, 404)

    def test_ordinary_application_routes_are_unchanged(self):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "alive")
