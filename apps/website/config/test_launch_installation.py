import tempfile
from copy import deepcopy
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.admin.sites import site
from django.contrib.auth.models import Group
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.management import call_command
from django.test import TestCase, override_settings

from pages.models import Page
from pages.site_presentation import import_presentation
from registry.models import ChallengeRun, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Participant, RunSubmission


@override_settings(DEBUG=False, RR2_ENABLED=False, REGISTRATION_ENABLED=False, WORKSHOP_SUBMISSIONS_ENABLED=False, RR1_SUBMISSIONS_ENABLED=False)
class FirstReleaseInstallationTests(TestCase):
    def test_packaged_seed_and_roles_repeat_on_a_fresh_database_with_no_participant_data(self):
        package = Path(__file__).resolve().parents[3] / "deployment" / "site-presentation"
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                call_command("bootstrap_roles", stdout=StringIO())
                presentation = import_presentation(package)
                pages = list(Page.objects.order_by("slug").values("slug", "public_path", "is_published"))
                permissions = {group.name: set(group.permissions.values_list("codename", flat=True)) for group in Group.objects.all()}
                import_presentation(package)
                call_command("bootstrap_roles", stdout=StringIO())
                self.assertEqual(list(Page.objects.order_by("slug").values("slug", "public_path", "is_published")), pages)
                self.assertEqual({group.name: set(group.permissions.values_list("codename", flat=True)) for group in Group.objects.all()}, permissions)
                for model in (Participant, LegacyRun, LegacyRunClaim, LegacyRunSubmission, ChallengeRun, RunSubmission):
                    self.assertEqual(model.objects.count(), 0, model._meta.label)
                legacy_package = deepcopy(presentation)
                for item in legacy_package["pages"]:
                    item["fields"].pop("required_release", None)
                with patch("pages.site_presentation.load_and_validate_package", return_value=(legacy_package, package)):
                    import_presentation(package)
                self.assertEqual(Page.objects.get(slug="challenge-rules").required_release, "rr2")
                self.assertEqual(self.client.get("/").status_code, 200)
                homepage = self.client.get("/")
                self.assertContains(homepage, 'href="/mods/"')
                for path in ("/rules/", "/halloffame/"):
                    self.assertEqual(self.client.get(path).status_code, 404)
                    self.assertNotContains(homepage, f'href="{path}"')
                self.assertEqual(self.client.get("/exploits/").status_code, 403)
                self.assertEqual(self.client.get("/legacyleaderboard/").status_code, 200)
                self.assertContains(self.client.get("/mods/"), "which is in development")
                administrator = Participant.objects.create_superuser(email="editor@example.test", nickname="Editor", password="test-only")
                self.client.force_login(administrator)
                self.assertEqual(self.client.get("/rules/").status_code, 404)
                with override_settings(RR2_ENABLED=True):
                    self.assertEqual(self.client.get("/rules/").status_code, 200)

    def test_empty_static_root_can_collect_and_resolve_admin_assets(self):
        with tempfile.TemporaryDirectory() as static_root:
            with override_settings(STATIC_ROOT=static_root, STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
            }):
                call_command("collectstatic", interactive=False, verbosity=0, stdout=StringIO())
                self.assertTrue((Path(static_root) / "staticfiles.json").exists())
                url = staticfiles_storage.url("registry/admin_legacy_claim_review.css")
                self.assertNotEqual(url, "/static/registry/admin_legacy_claim_review.css")
                self.assertIn(url, str(site._registry[LegacyRunClaim].media))
