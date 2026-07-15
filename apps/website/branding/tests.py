from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from registry.models import Participant
from registry.verification_email import send_verification_email

from .models import SiteBranding, WebsiteTheme


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
        self.assertContains(response, "Site branding")
        self.assertNotContains(response, "Delete")

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
                "former_participant_label": "Edited Former Racer",
                "disclaimer": "Edited disclaimer.",
                "active_theme": self.branding.active_theme_id,
            },
        )
        self.assertEqual(saved.status_code, 302)
        public_page = self.client.get(reverse("registry:privacy"))
        self.assertContains(public_page, "Edited Full Challenge")
        self.assertContains(public_page, "Edited Former Racer")

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
        selection = {"action": "preview_theme", "_selected_action": str(retro.pk)}

        preview_redirect = self.client.post(changelist, selection)

        self.assertEqual(preview_redirect.status_code, 302)
        preview_page = self.client.get(preview_redirect.url)
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
