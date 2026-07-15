from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from registry.models import Participant
from registry.verification_email import send_verification_email

from .models import SiteBranding


class SiteBrandingAdminTests(TestCase):
    def setUp(self):
        self.branding, _ = SiteBranding.objects.get_or_create(
            pk=SiteBranding.SINGLETON_PK
        )
        call_command("bootstrap_roles", verbosity=0)

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
