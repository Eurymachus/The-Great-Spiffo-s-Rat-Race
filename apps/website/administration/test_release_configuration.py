from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.db.utils import OperationalError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from registry.models import Participant
from config.release_controls import current_state, enabled
from .models import ReleaseConfiguration


@override_settings(SITE_MAINTENANCE_MODE=True, REGISTRATION_ENABLED=False,
                   WORKSHOP_SUBMISSIONS_ENABLED=False, RR1_SUBMISSIONS_ENABLED=False,
                   RR2_ENABLED=False, ALLOWED_HOSTS=["testserver", "dev.example.test"])
class ReleaseConfigurationTests(TestCase):
    def setUp(self):
        self.owner = Participant.objects.create_superuser("owner@example.invalid", "Owner", "test-password")
        self.url = reverse("admin:administration_releaseconfiguration_add")
        self.change = reverse("admin:administration_releaseconfiguration_change", args=[1])

    def test_bootstrap_and_immediate_database_authority(self):
        self.assertTrue(enabled("construction"))
        self.assertFalse(enabled("registration"))
        self.assertFalse(ReleaseConfiguration.objects.exists())
        record = ReleaseConfiguration.objects.create(construction=False, registration=True)
        self.assertFalse(enabled("construction"))
        self.assertTrue(enabled("registration"))
        record.registration = False
        record.save()
        self.assertFalse(enabled("registration"))

    def test_superuser_save_is_audited_and_construction_does_not_lock_admin(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"construction": "on"}).status_code, 302)
        self.assertTrue(ReleaseConfiguration.objects.get().construction)
        self.assertEqual(self.client.get(self.change, HTTP_HOST="dev.example.test").status_code, 200)
        self.assertEqual(self.client.get("/", HTTP_HOST="dev.example.test").status_code, 503)
        self.assertEqual(self.client.post(self.change, {"registration": "on"}).status_code, 302)
        self.assertTrue(enabled("registration"))
        self.assertFalse(enabled("rr2"))
        self.assertEqual(self.client.get("/", HTTP_HOST="dev.example.test").status_code, 200)
        self.assertEqual(LogEntry.objects.filter(content_type__model="releaseconfiguration").count(), 2)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)
        self.assertEqual(self.client.post(reverse("admin:administration_releaseconfiguration_delete", args=[1]), {"post":"yes"}).status_code, 403)

    def test_staff_with_all_model_permissions_cannot_read_or_write(self):
        ReleaseConfiguration.objects.create()
        staff = Participant.objects.create_user("staff@example.invalid", "Staff", "test-password", is_staff=True)
        staff.user_permissions.set(Permission.objects.filter(content_type__model="releaseconfiguration"))
        self.client.force_login(staff)
        for url in [self.url, self.change, reverse("admin:administration_releaseconfiguration_changelist"), reverse("admin:administration_releaseconfiguration_history", args=[1])]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {"rr2":"on"}).status_code, 403)
        self.assertFalse(enabled("rr2"))

    def test_anonymous_and_csrf_are_rejected(self):
        self.assertEqual(self.client.post(self.url, {"rr2":"on"}).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url, {"rr2":"on"}).status_code, 403)
        self.assertFalse(ReleaseConfiguration.objects.exists())

    def test_database_failure_closes_access(self):
        with patch("administration.models.ReleaseConfiguration.objects.filter", side_effect=OperationalError("offline")):
            self.assertEqual(current_state(), dict(construction=True, registration=False, workshop_submissions=False, rr1_submissions=False, rr2=False))

    def test_independent_controls_gate_routes_without_restart(self):
        record = ReleaseConfiguration.objects.create(construction=False)
        signup = reverse("registry:register")
        self.assertEqual(self.client.get(signup).status_code, 403)
        record.registration = True
        record.save()
        self.assertEqual(self.client.get(signup).status_code, 200)
        self.assertFalse(enabled("workshop_submissions"))
        self.assertFalse(enabled("rr1_submissions"))
        self.assertFalse(enabled("rr2"))
