from copy import deepcopy
from datetime import datetime, timezone

from django.test import TestCase

from .models import ChallengeRun, RunDailyMetric, RunStatisticSummary
from .run_authority import refresh_initial_run_authority
from .run_exports import InvalidRunExport, decode_run_export
from .test_run_exports import make_export


def projection(counts=None):
    return {
        "schema": 1, "currentKills": 42, "character": {},
        "farming": {"schema": 1, "planted": {}, "harvested": {}, "produce": counts if counts is not None else {
            "Base.Steak": 3, "Base.Chicken": 2, "Base.Toast": 1,
        }},
        "activeDay": {"dayIndex": 2, "farmingPlantedDeltas": {}, "farmingHarvestedDeltas": {}, "farmingProduceDeltas": {"Base.Steak": 1}},
    }


class FarmingTests(TestCase):
    def test_decode_preserves_raw_item_ids_without_titles(self):
        value = projection()
        decoded = decode_run_export(make_export(projection=value))
        self.assertEqual(decoded.projection["farming"], value["farming"])

    def test_empty_lua_tables_and_known_zero_are_accepted(self):
        for counts in ({}, []):
            value = projection(counts)
            value["activeDay"]["farmingProduceDeltas"] = counts
            decode_run_export(make_export(projection=value))

    def test_rejects_invalid_counts_ids_and_metadata(self):
        for counts in ({"Base.Book": -1}, {"Base.Book": True}, {"Base.Book": 0.5},
                       {"Base.Book": 2**53}, {"Translated book title": 1}, [1], None):
            value = projection()
            value["farming"]["produce"] = counts
            with self.subTest(counts=counts), self.assertRaises(InvalidRunExport):
                decode_run_export(make_export(projection=value))
        for key, bad in (("schema", True), ("schema", 2), ("partial", "false"), ("titles", [])):
            value = projection()
            value["farming"][key] = bad
            with self.subTest(key=key), self.assertRaises(InvalidRunExport):
                decode_run_export(make_export(projection=value))

    def test_daily_history_cannot_exceed_independent_cumulative_counts(self):
        value = projection()
        specs = [("day.started", {"dayIndex": 2, "completedDay": {
            "dayIndex": 1, "farmingPlantedDeltas": {}, "farmingHarvestedDeltas": {}, "farmingProduceDeltas": {"Base.Steak": 3},
        }})]
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value, event_specs=specs))
        value["farming"]["produce"]["Base.Steak"] = 5
        decode_run_export(make_export(projection=value, event_specs=specs))
        del value["farming"]
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value, event_specs=specs))

    def test_approval_normalizes_item_dimensions_and_replaces_without_duplicates(self):
        run = ChallengeRun.objects.create(run_id="farming-authority", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = projection()
        specs = [("day.started", {"dayIndex": 2, "completedDay": {
            "dayIndex": 1, "farmingPlantedDeltas": {}, "farmingHarvestedDeltas": {}, "farmingProduceDeltas": {"Base.Steak": 2},
        }})]
        decoded = decode_run_export(make_export(projection=value, event_specs=specs))
        # Decoding alone cannot change approved authority.
        self.assertFalse(run.statistic_summaries.exists())
        for _ in range(2):
            refresh_initial_run_authority(run, decoded.projection, decoded.events)
        summary = run.statistic_summaries.get(kind=RunStatisticSummary.Kind.FARMING_PRODUCE)
        self.assertEqual(summary.value, 6)
        self.assertFalse(summary.partial)
        self.assertEqual(dict(summary.metrics.values_list("raw_primary_id", "value")), value["farming"]["produce"])
        rows = RunDailyMetric.objects.filter(daily_record__run=run, kind=RunDailyMetric.Kind.FARMING_PRODUCE)
        self.assertEqual(sorted(rows.values_list("value", flat=True)), [1, 2])
        for day in run.daily_records.all():
            self.assertNotIn("farming", day.partial_metrics)
        # An older export has unknown coverage, not five fabricated zero counters.
        legacy = deepcopy(value)
        del legacy["farming"]
        del legacy["activeDay"]["farmingProduceDeltas"]
        del legacy["activeDay"]["farmingPlantedDeltas"]
        del legacy["activeDay"]["farmingHarvestedDeltas"]
        refresh_initial_run_authority(run, legacy, [])
        self.assertFalse(run.statistic_summaries.filter(kind=RunStatisticSummary.Kind.FARMING_PRODUCE).exists())
        self.assertIn("farming", run.daily_records.get().partial_metrics)

    def test_partial_coverage_and_zero_summary(self):
        run = ChallengeRun.objects.create(run_id="farming-partial", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = projection([])
        value["farming"]["partial"] = True
        value["activeDay"].update(farmingProduceDeltas=[], farmingPartial=True)
        refresh_initial_run_authority(run, value, [])
        summary = run.statistic_summaries.get(kind=RunStatisticSummary.Kind.FARMING_PRODUCE)
        self.assertEqual(summary.value, 0)
        self.assertTrue(summary.partial)
        self.assertFalse(summary.metrics.exists())
        self.assertIn("farming", run.daily_records.get().partial_metrics)

    def test_crop_ids_remain_distinct_from_item_catalogue_ids(self):
        run = ChallengeRun.objects.create(run_id="crop-ids", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        value = projection()
        value["farming"].update(planted={"Broccoli": 2}, harvested={"Broccoli": 1})
        value["activeDay"].update(farmingPlantedDeltas={"Broccoli": 1}, farmingHarvestedDeltas={"Broccoli": 1})
        decoded = decode_run_export(make_export(projection=value))
        refresh_initial_run_authority(run, decoded.projection, decoded.events)
        summary = run.statistic_summaries.get(kind=RunStatisticSummary.Kind.FARMING_PLANTED)
        self.assertEqual(summary.value, 2)
        metric = summary.metrics.get()
        self.assertEqual(metric.dimension, "crop")
        self.assertEqual(metric.raw_primary_id, "Broccoli")
        self.assertIsNone(metric.primary_catalogue_entry)
        value["farming"]["planted"] = {"Broccoli": True}
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value))
