from django.test import TestCase

from zomboid_catalogue.models import CatalogueAsset, CatalogueEntry
from .run_public import _catalogue_icon_map


class CatalogueIconFallbackTests(TestCase):
    def entry(self, version, kind="skill", identifier="Aiming"):
        return CatalogueEntry.objects.create(
            kind=kind, stable_id=identifier, introduced_in=version,
            display_name=identifier, icon_key="aiming",
        )

    def asset(self, entry, filename, source="pzwiki"):
        return CatalogueAsset.objects.create(
            entry=entry, role="icon", source_key="aiming", file=filename,
            availability="imported", source_type=source,
        )

    def test_older_matching_art_survives_until_current_art_is_ready(self):
        old = self.entry("42.20")
        current = self.entry("42.21")
        old_art = self.asset(old, "old.png")
        self.assertEqual(_catalogue_icon_map([current])[current.pk], old_art.file.url)
        current_art = self.asset(current, "current.png")
        self.assertEqual(_catalogue_icon_map([current])[current.pk], current_art.file.url)

    def test_identity_and_version_boundaries(self):
        target = self.entry("42.21")
        self.asset(self.entry("42.22"), "future.png")
        self.asset(self.entry("42.20", kind="item"), "other-kind.png")
        self.asset(self.entry("42.20", identifier="Reloading"), "other-id.png")
        self.assertEqual(_catalogue_icon_map([target]), {})

    def test_latest_older_version_and_manual_priority(self):
        self.asset(self.entry("42.19"), "oldest.png", source="manual")
        old = self.entry("42.20")
        self.asset(old, "wiki.png")
        manual = CatalogueAsset.objects.create(
            entry=old, role="icon", source_key="override", file="manual.png",
            availability="imported", source_type="manual",
        )
        target = self.entry("42.21")
        self.assertEqual(_catalogue_icon_map([target])[target.pk], manual.file.url)

    def test_unavailable_assets_do_not_hide_older_art(self):
        old_art = self.asset(self.entry("42.20"), "old.png")
        target = self.entry("42.21")
        self.asset(target, "", source="pzwiki")
        self.assertEqual(_catalogue_icon_map([target])[target.pk], old_art.file.url)
        self.assertEqual(_catalogue_icon_map([]), {})
