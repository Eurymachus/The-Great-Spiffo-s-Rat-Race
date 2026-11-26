from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from registry.models import Participant


@override_settings(DEBUG=False)
class AdminPermissionPageTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", verbosity=0)
        self.user = Participant.objects.create_user(
            email="reviewer@example.test", nickname="Reviewer", password="test-only", status="verified"
        )
        self.user.groups.add(Group.objects.get(name="Workshop Mod Approver"))
        self.client.force_login(self.user)

    def test_denial_keeps_admin_layout_and_restricted_navigation(self):
        response = self.client.get(reverse("admin:registry_participant_changelist"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "admin/permission_denied.html")
        self.assertContains(response, "permission to view participants", status_code=403)
        self.assertContains(response, "Return to dashboard", status_code=403)
        self.assertContains(response, reverse("admin:registry_workshopmod_changelist"), status_code=403)
        self.assertNotContains(response, 'href="' + reverse("admin:registry_participant_changelist") + '"', status_code=403)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_nonstaff_and_anonymous_still_require_admin_login(self):
        self.user.groups.clear()
        response = self.client.get(reverse("admin:registry_participant_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)
        self.client.logout()
        response = self.client.get(reverse("admin:registry_participant_changelist"))
        self.assertEqual(response.status_code, 302)
