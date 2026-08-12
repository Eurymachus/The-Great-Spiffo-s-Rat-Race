from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from branding.models import validate_brand_image_size
from registry.models import Participant

from .models import WebsiteSettings

class WebsiteSettingsAdminTests(TestCase):
    def setUp(self):
        self.superuser = Participant.objects.create_superuser(
            email="settings-superuser@example.com",
            nickname="Settings Superuser",
            password="test-password-only",
        )
        self.client.force_login(self.superuser)

    def test_default_image_upload_limit_is_ten_megabytes(self):
        self.assertEqual(
            WebsiteSettings.maximum_image_upload_size_mb(),
            10,
        )

    def test_superuser_can_change_image_upload_limit(self):
        settings = WebsiteSettings.current()
        change_url = reverse(
            "admin:administration_websitesettings_change", args=(settings.pk,)
        )
        response = self.client.post(
            change_url,
            {"maximum_image_upload_size": 12, "_continue": "Save and continue editing"},
        )
        self.assertEqual(response.status_code, 302)
        settings.refresh_from_db()
        self.assertEqual(settings.maximum_image_upload_size, 12)

        library = self.client.get(reverse("admin:branding_managedimage_library"))
        self.assertEqual(library.json()["upload_settings"]["maximum_image_size_mb"], 12)

    def test_admin_change_forms_load_background_save_support(self):
        settings = WebsiteSettings.current()
        response = self.client.get(
            reverse("admin:administration_websitesettings_change", args=(settings.pk,))
        )

        self.assertContains(response, "registry/admin_save.js")

    def test_admin_change_forms_offer_one_save_and_continue_action(self):
        settings = WebsiteSettings.current()
        response = self.client.get(
            reverse("admin:administration_websitesettings_change", args=(settings.pk,))
        )

        self.assertContains(response, 'name="_continue"', count=1)
        self.assertContains(response, 'value="Save"', count=1)
        self.assertNotContains(response, 'name="_save"')
        self.assertNotContains(response, 'name="_addanother"')
        self.assertNotContains(response, 'name="_saveasnew"')
        self.assertNotContains(response, "Save and continue editing")
        self.assertNotContains(response, "Save and add another")

    def test_registry_models_are_grouped_by_backend_concern(self):
        response = self.client.get(reverse("admin:index"), follow=True)

        self.assertContains(response, "Participant administration")
        self.assertContains(response, "Challenge configuration")
        self.assertContains(response, "Run moderation")
        self.assertContains(response, "Legacy data")
        self.assertContains(response, "Legacy data imports")
        self.assertContains(response, "Legacy runs")
        self.assertContains(response, "Legacy run submissions")
        self.assertContains(response, "Legacy run claims")
        self.assertContains(response, "Platform integrations")
        content = response.content.decode()
        self.assertLess(
            content.index("Challenge configuration"),
            content.index("Challenge modes"),
        )
        self.assertLess(content.index("Run moderation"), content.index("Challenge runs"))
        self.assertLess(content.index("Legacy data"), content.index("Legacy data imports"))
        self.assertLess(
            content.index("Platform integrations"),
            content.index("Cached streaming media"),
        )

    def test_image_validator_uses_configured_limit(self):
        settings = WebsiteSettings.current()
        settings.maximum_image_upload_size = 1
        settings.save()
        oversized = SimpleUploadedFile(
            "oversized.png", b"x" * (1024 * 1024 + 1), content_type="image/png"
        )

        with self.assertRaisesMessage(
            ValidationError, "Brand images must be 1 MB or smaller."
        ):
            validate_brand_image_size(oversized)

    def test_non_superuser_cannot_access_website_settings(self):
        participant = Participant.objects.create_user(
            email="ordinary-participant@example.com",
            nickname="Ordinary Participant",
            password="test-password-only",
        )
        self.client.force_login(participant)
        settings = WebsiteSettings.current()
        response = self.client.get(
            reverse("admin:administration_websitesettings_change", args=(settings.pk,))
        )
        self.assertEqual(response.status_code, 302)
