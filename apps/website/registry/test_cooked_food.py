from copy import deepcopy
from datetime import datetime, timezone
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from .models import ChallengeRun, RunDailyMetric, RunStatisticSummary
from .run_authority import refresh_initial_run_authority
from .run_exports import InvalidRunExport, decode_run_export
from .test_run_exports import make_export


def projection(counts=None):
    return {
        "schema": 1, "currentKills": 42, "character": {},
        "cookedFood": {"schema": 1, "items": counts if counts is not None else {
            "Base.Steak": 3, "Base.Chicken": 2, "Base.Toast": 1,
        }},
        "activeDay": {"dayIndex": 2, "cookedFoodItemsDeltas": {"Base.Steak": 1}},
    }


class CookedFoodTests(TestCase):
    def test_migration_marks_existing_days_unknown_without_duplicate_flags(self):
        run = ChallengeRun.objects.create(run_id="cookedFood-legacy", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = {"schema": 1, "currentKills": 0, "character": {},
                 "activeDay": {"dayIndex": 1, "killDelta": 7}}
        refresh_initial_run_authority(run, value, [])
        day = run.daily_records.get()
        day.partial_metrics = ["distance"]
        day.save(update_fields=["partial_metrics"])
        migration = import_module("registry.migrations.0073_cooked_food_history_coverage")
        for _ in range(2):
            migration.mark_existing_days_unknown(apps, SimpleNamespace(connection=connection))
        day.refresh_from_db()
        self.assertEqual(day.partial_metrics, ["distance", "cookedFood"])
        self.assertEqual(day.kill_delta, 7)

    def test_decode_preserves_raw_item_ids_without_titles(self):
        value = projection()
        decoded = decode_run_export(make_export(projection=value))
        self.assertEqual(decoded.projection["cookedFood"], value["cookedFood"])

    def test_empty_lua_tables_and_known_zero_are_accepted(self):
        for counts in ({}, []):
            value = projection(counts)
            value["activeDay"]["cookedFoodItemsDeltas"] = counts
            decode_run_export(make_export(projection=value))

    def test_rejects_invalid_counts_ids_and_metadata(self):
        for counts in ({"Base.Book": -1}, {"Base.Book": True}, {"Base.Book": 0.5},
                       {"Base.Book": 2**53}, {"Translated book title": 1}, [1], None):
            value = projection()
            value["cookedFood"]["items"] = counts
            with self.subTest(counts=counts), self.assertRaises(InvalidRunExport):
                decode_run_export(make_export(projection=value))
        for key, bad in (("schema", True), ("schema", 2), ("partial", "false"), ("titles", [])):
            value = projection()
            value["cookedFood"][key] = bad
            with self.subTest(key=key), self.assertRaises(InvalidRunExport):
                decode_run_export(make_export(projection=value))

    def test_daily_history_cannot_exceed_independent_cumulative_counts(self):
        value = projection()
        specs = [("day.started", {"dayIndex": 2, "completedDay": {
            "dayIndex": 1, "cookedFoodItemsDeltas": {"Base.Steak": 3},
        }})]
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value, event_specs=specs))
        value["cookedFood"]["items"]["Base.Steak"] = 5
        decode_run_export(make_export(projection=value, event_specs=specs))
        del value["cookedFood"]
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value, event_specs=specs))

    def test_approval_normalizes_item_dimensions_and_replaces_without_duplicates(self):
        run = ChallengeRun.objects.create(run_id="cookedFood-authority", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = projection()
        specs = [("day.started", {"dayIndex": 2, "completedDay": {
            "dayIndex": 1, "cookedFoodItemsDeltas": {"Base.Steak": 2},
        }})]
        decoded = decode_run_export(make_export(projection=value, event_specs=specs))
        # Decoding alone cannot change approved authority.
        self.assertFalse(run.statistic_summaries.exists())
        for _ in range(2):
            refresh_initial_run_authority(run, decoded.projection, decoded.events)
        summary = run.statistic_summaries.get(kind=RunStatisticSummary.Kind.COOKED_FOOD)
        self.assertEqual(summary.value, 6)
        self.assertFalse(summary.partial)
        self.assertEqual(dict(summary.metrics.values_list("raw_primary_id", "value")), value["cookedFood"]["items"])
        rows = RunDailyMetric.objects.filter(daily_record__run=run, kind=RunDailyMetric.Kind.COOKED_FOOD)
        self.assertEqual(sorted(rows.values_list("value", flat=True)), [1, 2])
        for day in run.daily_records.all():
            self.assertNotIn("cookedFood", day.partial_metrics)
        # An older export has unknown coverage, not five fabricated zero counters.
        legacy = deepcopy(value)
        del legacy["cookedFood"]
        del legacy["activeDay"]["cookedFoodItemsDeltas"]
        refresh_initial_run_authority(run, legacy, [])
        self.assertFalse(run.statistic_summaries.filter(kind=RunStatisticSummary.Kind.COOKED_FOOD).exists())
        self.assertIn("cookedFood", run.daily_records.get().partial_metrics)

    def test_partial_coverage_and_zero_summary(self):
        run = ChallengeRun.objects.create(run_id="cookedFood-partial", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = projection([])
        value["cookedFood"]["partial"] = True
        value["activeDay"].update(cookedFoodItemsDeltas=[], cookedFoodPartial=True)
        refresh_initial_run_authority(run, value, [])
        summary = run.statistic_summaries.get(kind=RunStatisticSummary.Kind.COOKED_FOOD)
        self.assertEqual(summary.value, 0)
        self.assertTrue(summary.partial)
        self.assertFalse(summary.metrics.exists())
        self.assertIn("cookedFood", run.daily_records.get().partial_metrics)
