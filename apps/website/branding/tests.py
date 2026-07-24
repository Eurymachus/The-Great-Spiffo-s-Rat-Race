import tempfile
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from registry.models import Participant
from registry.verification_email import send_verification_email
from pages.models import Page

from .models import ManagedImage, SiteBranding, WebsiteTheme


def png_bytes(colour=(255, 128, 0, 255)):
    output = BytesIO()
    Image.new("RGBA", (2, 2), colour).save(output, format="PNG")
    return output.getvalue()


class SiteBrandingAdminTests(TestCase):
    def setUp(self):
        self.branding, _ = SiteBranding.objects.get_or_create(
            pk=SiteBranding.SINGLETON_PK
        )
        call_command("bootstrap_roles", verbosity=0)
        self.branding.refresh_from_db()

    def test_superuser_can_change_but_not_delete_branding(self):
        superuser = Participant.objects.create_superuser(
            email="branding-superuser@example.com",
            nickname="Branding Superuser",
            password="test-password-only",
        )
        self.client.force_login(superuser)

        change_url = reverse(
            "admin:branding_sitebranding_change", args=(self.branding.pk,)
        )
        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Branding")
        self.assertContains(response, 'class="branding-image-panel"', count=4)
        self.assertContains(
            response,
            "Used for link previews on Discord and social media. It is not displayed within the website page itself.",
        )
        self.assertContains(response, "branding/media_library.js")
        self.assertContains(response, "branding/image_controls.js")
        self.assertContains(response, "Image opacity")
        self.assertContains(response, "Position")
        self.assertContains(response, 'class="branding-setting-tooltip"', count=8)
        self.assertContains(
            response,
            "Controls how strongly the background image is shown.",
        )
        self.assertNotContains(response, "Header logo preview:")
        self.assertNotContains(response, "Delete")

        list_url = reverse("admin:branding_sitebranding_changelist")
        self.assertRedirects(
            self.client.get(list_url),
            change_url,
            fetch_redirect_response=False,
        )

    def test_background_image_presentation_settings_render_as_css_variables(self):
        self.branding.background_image_opacity = 70
        self.branding.background_overlay_strength = 35
        self.branding.background_image_saturation = 80
        self.branding.background_image_brightness = 90
        self.branding.background_image_contrast = 110
        self.branding.background_image_position = "left top"
        self.branding.background_image_scale = "contain"
        self.branding.background_image_fixed = False
        with tempfile.TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root
        ):
            self.branding.background_image = SimpleUploadedFile(
                "test-background.png", png_bytes(), content_type="image/png"
            )
            self.branding.enable_background_image = True
            self.branding.save()

            response = self.client.get(reverse("registry:home"))

        self.assertContains(response, "--site-background-image-opacity: 0.7")
        self.assertContains(response, "--site-background-overlay: 35%")
        self.assertContains(response, "--site-background-saturation: 80%")
        self.assertContains(response, "--site-background-brightness: 90%")
        self.assertContains(response, "--site-background-contrast: 110%")
        self.assertContains(response, "--site-background-position: left top")
        self.assertContains(response, "--site-background-size: contain")
        self.assertContains(response, "--site-background-layer-position: absolute")

    def test_uploaded_header_logo_renders_only_when_enabled(self):
        one_pixel_png = png_bytes()
        with tempfile.TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root
        ):
            self.branding.header_logo = SimpleUploadedFile(
                "test-logo.png", one_pixel_png, content_type="image/png"
            )
            self.branding.header_logo_alt = "Test challenge logo"
            self.branding.save()

            disabled = self.client.get(reverse("registry:home"))
            self.assertNotContains(disabled, "test-logo.png")

            self.branding.enable_header_logo = True
            self.branding.save(update_fields=("enable_header_logo",))
            enabled = self.client.get(reverse("registry:home"))
            self.assertContains(enabled, "test-logo.png")
            self.assertContains(enabled, 'alt="Test challenge logo"')

    def test_media_library_upload_returns_immediate_image_metadata(self):
        superuser = Participant.objects.create_superuser(
            email="media-superuser@example.com",
            nickname="Media Superuser",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        image_list = self.client.get(reverse("admin:branding_managedimage_changelist"))
        self.assertContains(image_list, "Upload images")
        self.assertNotContains(image_list, "Add image")
        self.assertContains(image_list, "branding/media_library.js")
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("admin:branding_managedimage_library"),
                {
                    "names": ["Rat Race Header"],
                    "images": [SimpleUploadedFile("rat-race-header.png", png_bytes(), content_type="image/png")],
                },
            )

            self.assertEqual(response.status_code, 200)
            result = response.json()["results"][0]
            self.assertTrue(result["ok"])
            self.assertEqual(result["image"]["name"], "Rat Race Header")
            self.assertEqual(result["image"]["filename"], "rat-race-header.png")
            self.assertEqual(result["image"]["dimensions"], "2 x 2")
            uploaded_image = ManagedImage.objects.get(name="Rat Race Header")
            self.assertEqual(uploaded_image.uploaded_by, superuser)

            refreshed_list = self.client.get(reverse("admin:branding_managedimage_changelist"))
            self.assertContains(refreshed_list, "Uploaded by")
            self.assertContains(refreshed_list, superuser.nickname)

    def test_media_library_rejects_invalid_image_with_clear_feedback(self):
        superuser = Participant.objects.create_superuser(
            email="invalid-media@example.com",
            nickname="Invalid Media",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse("admin:branding_managedimage_library"),
                {
                    "names": ["Not Really An Image"],
                    "images": [SimpleUploadedFile("not-an-image.png", b"not an image", content_type="image/png")],
                },
            )

            self.assertEqual(response.status_code, 200)
            result = response.json()["results"][0]
            self.assertFalse(result["ok"])
            self.assertIn("not a valid image", result["error"])
            self.assertFalse(ManagedImage.objects.exists())

    def test_media_library_name_can_be_changed_inline(self):
        superuser = Participant.objects.create_superuser(
            email="rename-media@example.com",
            nickname="Rename Media",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            image = ManagedImage.objects.create(
                name="Original Name",
                image=SimpleUploadedFile("original.png", png_bytes(), content_type="image/png"),
                original_filename="original.png",
            )
            list_url = reverse("admin:branding_managedimage_changelist")
            rename_url = reverse("admin:branding_managedimage_rename", args=(image.pk,))

            image_list = self.client.get(list_url)
            self.assertContains(image_list, 'class="managed-image-name"')
            self.assertContains(image_list, f'data-rename-url="{rename_url}"')
            self.assertNotContains(
                image_list,
                reverse("admin:branding_managedimage_change", args=(image.pk,)),
            )

            response = self.client.post(rename_url, {"name": "Updated Name"})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], "Updated Name")
            image.refresh_from_db()
            self.assertEqual(image.name, "Updated Name")

    def test_media_library_inline_name_rejects_blank_and_duplicate_names(self):
        superuser = Participant.objects.create_superuser(
            email="invalid-rename-media@example.com",
            nickname="Invalid Rename Media",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            first = ManagedImage.objects.create(
                name="First Image",
                image=SimpleUploadedFile("first.png", png_bytes(), content_type="image/png"),
                original_filename="first.png",
            )
            second = ManagedImage.objects.create(
                name="Second Image",
                image=SimpleUploadedFile("second.png", png_bytes(), content_type="image/png"),
                original_filename="second.png",
            )
            rename_url = reverse("admin:branding_managedimage_rename", args=(second.pk,))

            blank_response = self.client.post(rename_url, {"name": "   "})
            duplicate_response = self.client.post(rename_url, {"name": first.name.lower()})

            self.assertEqual(blank_response.status_code, 400)
            self.assertIn("Enter a name", blank_response.json()["error"])
            self.assertEqual(duplicate_response.status_code, 400)
            self.assertIn("already exists", duplicate_response.json()["error"])
            second.refresh_from_db()
            self.assertEqual(second.name, "Second Image")

    def test_media_library_row_delete_removes_record_and_stored_file(self):
        superuser = Participant.objects.create_superuser(
            email="delete-media@example.com",
            nickname="Delete Media",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            image = ManagedImage.objects.create(
                name="Temporary Image",
                image=SimpleUploadedFile("temporary.png", png_bytes(), content_type="image/png"),
                original_filename="temporary.png",
            )
            stored_name = image.image.name
            storage = image.image.storage
            delete_url = reverse("admin:branding_managedimage_delete", args=(image.pk,))

            image_list = self.client.get(reverse("admin:branding_managedimage_changelist"))
            self.assertNotContains(image_list, 'class="managed-image-delete"')
            self.assertContains(image_list, 'value="delete_selected"')

            response = self.client.post(delete_url, {"post": "yes"})

            self.assertEqual(response.status_code, 302)
            self.assertFalse(ManagedImage.objects.filter(pk=image.pk).exists())
            self.assertFalse(storage.exists(stored_name))

    def test_selected_library_image_can_supply_header_logo(self):
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            image = ManagedImage.objects.create(
                name="Reusable Header",
                image=SimpleUploadedFile("reusable.png", png_bytes(), content_type="image/png"),
                original_filename="reusable.png",
            )
            self.branding.header_logo_asset = image
            self.branding.enable_header_logo = True
            self.branding.header_logo_alt = "Reusable challenge logo"
            self.branding.save()

            response = self.client.get(reverse("registry:home"))
            self.assertContains(response, "reusable.png")
            self.assertContains(response, 'alt="Reusable challenge logo"')

    def test_branding_administrator_has_only_scoped_admin_access(self):
        participant = Participant.objects.create_user(
            email="branding-admin@example.com",
            nickname="Branding Admin",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        participant.groups.add(Group.objects.get(name="Branding Administrator"))
        participant.refresh_from_db()
        self.client.force_login(participant)

        self.assertTrue(participant.is_staff)
        self.assertTrue(participant.has_perm("branding.view_sitebranding"))
        self.assertTrue(participant.has_perm("branding.change_sitebranding"))
        self.assertTrue(participant.has_perm("branding.add_websitetheme"))
        self.assertTrue(participant.has_perm("branding.change_websitetheme"))
        self.assertTrue(participant.has_perm("branding.delete_websitetheme"))
        self.assertTrue(participant.has_perm("branding.add_managedimage"))
        self.assertTrue(participant.has_perm("branding.change_managedimage"))
        self.assertTrue(participant.has_perm("branding.delete_managedimage"))
        self.assertTrue(participant.has_perm("pages.change_page"))
        self.assertTrue(participant.has_perm("pages.change_pagesection"))
        self.assertTrue(participant.has_perm("pages.change_sectionitem"))
        self.assertFalse(participant.has_perm("registry.view_participant"))

        admin_home = self.client.get("/admin/")
        self.assertRedirects(
            admin_home,
            reverse("admin:branding_sitebranding_change", args=(self.branding.pk,)),
            fetch_redirect_response=False,
        )
        participant_list = self.client.get(
            reverse("admin:registry_participant_changelist")
        )
        self.assertEqual(participant_list.status_code, 403)

        change_url = reverse(
            "admin:branding_sitebranding_change", args=(self.branding.pk,)
        )
        saved = self.client.post(
            change_url,
            {
                "full_title": "Edited Full Challenge",
                "short_title": "Edited Race",
                "tagline": "Edited tagline",
                "welcome_message": "Edited welcome!",
                "participant_label": "Edited Racer",
                "participant_plural_label": "Edited Racers",
                "former_participant_label": "Edited Former Racer",
                "run_update_label": "Edited update",
                "run_update_plural_label": "Edited updates",
                "sign_in_prompt": "Existing Racer?",
                "disclaimer": "Edited disclaimer.",
                "show_attribution": "on",
                "attribution_text": settings.SITE_ATTRIBUTION_TEXT,
                "attribution_url": settings.SITE_ATTRIBUTION_URL,
                "attribution_new_tab": "on",
                "active_theme": self.branding.active_theme_id,
                "homepage_feature_fit": "cover",
                "homepage_feature_height": "standard",
                "homepage_feature_custom_height": 24,
                "homepage_feature_position": "center center",
                "background_image_opacity": 100,
                "background_overlay_strength": 28,
                "background_image_saturation": 100,
                "background_image_brightness": 100,
                "background_image_contrast": 100,
                "background_image_position": "center top",
                "background_image_scale": "cover",
                "background_image_fixed": "on",
            },
        )
        self.assertEqual(saved.status_code, 302)
        public_page = self.client.get(reverse("registry:privacy"))
        self.assertContains(public_page, "Edited Full Challenge")
        self.assertContains(public_page, "Edited Former Racer")

        page_admin = self.client.get(reverse("admin:pages_page_changelist"))
        self.assertEqual(page_admin.status_code, 200)
        self.assertContains(page_admin, Page.objects.get(slug="home").title)

        self.client.logout()
        self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": "1984-04-25"},
        )
        registration = self.client.get(reverse("registry:register"))
        self.assertContains(registration, "Edited Racer nickname")

        account_user = Participant.objects.create_user(
            email="branding-account@example.com",
            nickname="Branding Account",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(account_user)
        account = self.client.get(reverse("registry:account"))
        self.assertContains(account, "Edited Racer dashboard")
        self.assertContains(account, "Edited welcome!")

    def test_branding_administrator_can_delete_only_inactive_custom_themes(self):
        participant = Participant.objects.create_user(
            email="theme-delete@example.com",
            nickname="Theme Deleter",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        participant.groups.add(Group.objects.get(name="Branding Administrator"))
        custom = WebsiteTheme.objects.create(name="Disposable Custom Theme")
        active_custom = WebsiteTheme.objects.create(name="Active Custom Theme")
        self.branding.active_theme = active_custom
        self.branding.save()
        built_in = WebsiteTheme.objects.get(preset_key="clean-competition")
        self.client.force_login(participant)
        changelist = reverse("admin:branding_websitetheme_changelist")

        custom_page = self.client.get(
            reverse("admin:branding_websitetheme_change", args=(custom.pk,))
        )
        active_page = self.client.get(
            reverse("admin:branding_websitetheme_change", args=(active_custom.pk,))
        )
        built_in_page = self.client.get(
            reverse("admin:branding_websitetheme_change", args=(built_in.pk,))
        )
        self.assertContains(custom_page, "Delete")
        self.assertNotContains(active_page, "Delete")
        self.assertNotContains(built_in_page, "Delete")

        response = self.client.post(
            changelist,
            {
                "action": "delete_custom_themes",
                "_selected_action": [str(custom.pk), str(active_custom.pk), str(built_in.pk)],
            },
            follow=True,
        )

        self.assertContains(response, "Deleted 1 custom theme(s).")
        self.assertContains(response, "Kept 2 active or built-in theme(s).")
        self.assertFalse(WebsiteTheme.objects.filter(pk=custom.pk).exists())
        self.assertTrue(WebsiteTheme.objects.filter(pk=active_custom.pk).exists())
        self.assertTrue(WebsiteTheme.objects.filter(pk=built_in.pk).exists())

    def test_participant_email_uses_database_branding(self):
        self.branding.full_title = "Email Full Challenge"
        self.branding.short_title = "Email Race"
        self.branding.tagline = "Email tagline"
        self.branding.save()
        participant = Participant.objects.create_user(
            email="email-branding@example.com",
            nickname="Email Branding",
            password="test-password-only",
        )

        send_verification_email(participant, "https://example.com/verify/")

        self.assertEqual(mail.outbox[0].subject, "Verify your Email Race nickname")
        self.assertIn("Email Full Challenge", mail.outbox[0].body)
        self.assertIn("Email tagline", mail.outbox[0].body)

    def test_three_editable_presets_exist_and_survival_event_is_active(self):
        self.assertSetEqual(
            set(WebsiteTheme.objects.values_list("preset_key", flat=True)),
            {"survival-event", "retro-road-race", "clean-competition"},
        )
        self.assertEqual(self.branding.active_theme.preset_key, "survival-event")

    def test_superuser_can_preview_then_activate_a_theme(self):
        superuser = Participant.objects.create_superuser(
            email="theme-superuser@example.com",
            nickname="Theme Superuser",
            password="test-password-only",
        )
        retro = WebsiteTheme.objects.get(preset_key="retro-road-race")
        self.client.force_login(superuser)
        changelist = reverse("admin:branding_websitetheme_changelist")
        preview_url = (
            f"{reverse('registry:register')}?theme-preview={retro.pk}"
        )

        changelist_page = self.client.get(changelist)

        self.assertContains(changelist_page, f'href="{preview_url}"')
        self.assertNotContains(
            changelist_page, "Preview selected theme on signup page"
        )
        preview_page = self.client.get(preview_url)
        self.assertContains(preview_page, "Previewing <strong>Retro Road Race</strong>")
        self.assertContains(preview_page, "theme-background-road")
        self.assertContains(preview_page, "--theme-accent: #B53624")
        self.branding.refresh_from_db()
        self.assertEqual(self.branding.active_theme.preset_key, "survival-event")

        activated = self.client.post(
            changelist,
            {"action": "activate_theme", "_selected_action": str(retro.pk)},
        )

        self.assertEqual(activated.status_code, 302)
        self.branding.refresh_from_db()
        self.assertEqual(self.branding.active_theme, retro)

    def test_theme_colours_reject_arbitrary_css(self):
        theme = WebsiteTheme(name="Unsafe", accent_colour="red; background:url(x)")

        with self.assertRaises(ValidationError):
            theme.full_clean()

    def test_supplied_fonts_are_selectable_and_rendered_as_theme_tokens(self):
        theme = WebsiteTheme.objects.get(preset_key="clean-competition")
        theme.display_font = WebsiteTheme.HeadingFont.DERELICT_ROUGH
        theme.display_font_weight = WebsiteTheme.FontWeight.REGULAR
        theme.display_font_spacing = WebsiteTheme.FontSpacing.NORMAL
        theme.heading_font = WebsiteTheme.HeadingFont.OSWALD
        theme.heading_font_weight = WebsiteTheme.FontWeight.SEMI_BOLD
        theme.heading_font_spacing = WebsiteTheme.FontSpacing.WIDE
        theme.body_font = WebsiteTheme.BodyFont.OSWALD
        theme.body_font_weight = WebsiteTheme.FontWeight.LIGHT
        theme.body_font_spacing = WebsiteTheme.FontSpacing.TIGHT
        theme.save()
        self.branding.active_theme = theme
        self.branding.save()

        public_page = self.client.get(reverse("registry:register"))

        self.assertContains(
            public_page,
            "--theme-display-font: RatRaceDerelictRough, RatRaceDerelict, Impact, sans-serif",
        )
        self.assertContains(
            public_page, "--theme-heading-font: RatRaceOswald, Impact, sans-serif"
        )
        self.assertContains(
            public_page,
            "--theme-body-font: RatRaceOswald, Arial, sans-serif",
        )
        self.assertContains(public_page, "--theme-heading-weight: 600")
        self.assertContains(public_page, "--theme-display-weight: 400")
        self.assertContains(public_page, "--theme-body-weight: 300")
        self.assertContains(public_page, "--theme-heading-spacing: 0.08em")
        self.assertContains(public_page, "--theme-body-spacing: -0.03em")

        superuser = Participant.objects.create_superuser(
            email="font-superuser@example.com",
            nickname="Font Superuser",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        change_page = self.client.get(
            reverse("admin:branding_websitetheme_change", args=(theme.pk,))
        )
        self.assertContains(change_page, "Derelict Rough")
        self.assertContains(change_page, "SemiBold (600)")
        self.assertContains(change_page, "Font family")
        self.assertContains(change_page, "Spacing")
        self.assertContains(change_page, "The Great Spiffo&#x27;s Rat Race")
        self.assertContains(change_page, "Welcome to the Rat Race!")
        self.assertContains(change_page, "Your participant account is ready.")
