from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from registry.models import Participant

from .models import CatalogueAlias, CatalogueEntry
from .resolver import resolve_identifier


class CatalogueResolverTests(TestCase):
    def test_resolves_direct_identifier_for_applicable_version(self):
        entry = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="Woodwork",
            display_name="Carpentry",
            introduced_in="42.0",
        )
        self.assertEqual(
            resolve_identifier(CatalogueEntry.Kind.SKILL, "Woodwork", "42.19"),
            entry,
        )

    def test_resolves_versioned_alias(self):
        entry = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.NewItem",
            display_name="New item",
            introduced_in="42.0",
        )
        CatalogueAlias.objects.create(
            entry=entry,
            stable_id="Base.OldItem",
            removed_in="43.0",
        )
        self.assertEqual(
            resolve_identifier(CatalogueEntry.Kind.ITEM, "Base.OldItem", "42.19"),
            entry,
        )
        self.assertIsNone(
            resolve_identifier(CatalogueEntry.Kind.ITEM, "Base.OldItem", "43.0")
        )

    def test_bundled_catalogue_import_is_idempotent(self):
        call_command("import_zomboid_catalogue", stdout=StringIO())
        first_count = CatalogueEntry.objects.count()
        self.assertGreaterEqual(first_count, 60)
        self.assertEqual(
            resolve_identifier(
                CatalogueEntry.Kind.SKILL, "Woodwork", "42.19"
            ).display_name,
            "Carpentry",
        )
        self.assertEqual(
            resolve_identifier(
                CatalogueEntry.Kind.OUTPOST,
                "hog_wallow_military_base",
                "42.19",
            ).display_name,
            "Hog Wallow Military Base",
        )

        output = StringIO()
        call_command("import_zomboid_catalogue", stdout=output)
        self.assertEqual(CatalogueEntry.objects.count(), first_count)
        self.assertIn(f"{first_count} unchanged", output.getvalue())


class CatalogueAdminTests(TestCase):
    def test_catalogue_role_can_open_catalogue_admin(self):
        call_command("bootstrap_roles")
        user = Participant.objects.create_user(
            email="integration@example.com",
            nickname="Integration",
            password="Local-test-password-482!",
            is_active=True,
        )
        user.groups.add(Group.objects.get(name="Zomboid Integration"))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.client.force_login(user)

        response = self.client.get(
            reverse("admin:zomboid_catalogue_catalogueentry_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project Zomboid Catalogue")
