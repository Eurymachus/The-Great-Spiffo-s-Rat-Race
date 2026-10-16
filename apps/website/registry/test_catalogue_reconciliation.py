from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from zomboid_catalogue.models import CatalogueEntry, CatalogueAlias
from zomboid_catalogue.resolver import resolve_identifier
from .models import ChallengeRun, RunStatisticMetric, RunStatisticSummary
from .run_authority import _refresh_statistic_authority


class CatalogueReconciliationTests(TestCase):
    def setUp(self):
        self.old = CatalogueEntry.objects.create(kind="item", stable_id="Base.AxeStone",
            display_name="Crude Stone Axe", introduced_in="42.20")
        self.new = CatalogueEntry.objects.create(kind="item", stable_id=self.old.stable_id,
            display_name=self.old.display_name, introduced_in="42.21")
        self.run = ChallengeRun.objects.create(run_id="reconcile-test", export_format=4,
            generated_at=timezone.now(), event_hash="0" * 64)

    def test_versions_are_resolved_but_different_alias_targets_are_ambiguous(self):
        self.assertEqual(resolve_identifier("item", self.old.stable_id), self.new)
        self.assertEqual(resolve_identifier("item", self.old.stable_id, "42.20"), self.old)
        self.assertIsNone(resolve_identifier("item", self.old.stable_id, "42.19"))
        other = CatalogueEntry.objects.create(kind="item", stable_id="Base.Other",
            display_name="Other", introduced_in="42.20")
        for version, entry in (("42.20", self.old), ("42.21", other)):
            CatalogueAlias.objects.create(entry=entry, stable_id="ambiguous", introduced_in=version)
        self.assertIsNone(resolve_identifier("item", "ambiguous"))

    def test_approval_import_links_item_with_multiple_catalogue_versions(self):
        _refresh_statistic_authority(self.run, {"brokenWeapons": {
            "total": 36, "weapons": [{"id": self.old.stable_id, "breaks": 36}]}})
        metric = RunStatisticMetric.objects.get(summary__run=self.run, summary__kind="broken_weapons")
        self.assertEqual(metric.primary_catalogue_entry, self.new)
        self.assertEqual((metric.raw_primary_id, metric.value), (self.old.stable_id, 36))

    def test_repair_is_dry_run_first_missing_only_and_idempotent(self):
        summary = RunStatisticSummary.objects.create(run=self.run, kind="broken_weapons", value=36)
        metric = RunStatisticMetric.objects.create(summary=summary, dimension="item",
            raw_primary_id=self.old.stable_id, value=36)
        linked = RunStatisticMetric.objects.create(summary=summary, dimension="item",
            raw_primary_id="historical-id", value=2, primary_catalogue_entry=self.old)
        call_command("reconcile_broken_weapon_catalogue", stdout=StringIO())
        metric.refresh_from_db()
        self.assertIsNone(metric.primary_catalogue_entry_id)
        call_command("reconcile_broken_weapon_catalogue", apply=True, stdout=StringIO())
        metric.refresh_from_db(); linked.refresh_from_db()
        self.assertEqual(metric.primary_catalogue_entry_id, self.new.pk)
        self.assertEqual((metric.raw_primary_id, metric.value), (self.old.stable_id, 36))
        self.assertEqual(linked.primary_catalogue_entry_id, self.old.pk)
        output = StringIO()
        call_command("reconcile_broken_weapon_catalogue", apply=True, stdout=output)
        self.assertIn("Applied: 0 links", output.getvalue())
