from copy import deepcopy
from datetime import datetime, timezone
from django.test import TestCase
from .models import ChallengeRun, RunStatisticSummary
from .run_authority import refresh_initial_run_authority
from .run_exports import InvalidRunExport, decode_run_export
from .test_run_exports import make_export


def projection():
    return {"schema": 1, "currentKills": 0, "character": {},
            "distance": {"travelledMeters": 30, "byModeMeters": {"onFoot": 10, "driver": 20}},
            "activeDay": {"dayIndex": 1, "distanceDeltaMeters": 5,
                          "distanceByModeDeltas": {"onFoot": 5, "driver": 0}}}


class DistanceTests(TestCase):
    def test_roundtrip_and_authority(self):
        value = projection()
        decoded = decode_run_export(make_export(projection=value))
        run = ChallengeRun.objects.create(run_id="distance-test", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0"*64)
        for _ in range(2):
            refresh_initial_run_authority(run, decoded.projection, decoded.events)
        summaries = run.statistic_summaries.filter(kind__in=["distance_on_foot", "distance_driver"])
        self.assertEqual(dict(summaries.values_list("kind", "value")),
                         {"distance_on_foot": 10, "distance_driver": 20})
        day = run.daily_records.get()
        self.assertEqual((day.distance_on_foot_meters, day.distance_driver_meters), (5, 0))
        del value["distance"]["byModeMeters"]
        del value["activeDay"]["distanceByModeDeltas"]
        refresh_initial_run_authority(run, value, [])
        self.assertFalse(summaries.exists())
        self.assertIsNone(run.daily_records.get().distance_on_foot_meters)

    def test_invalid_values_and_totals(self):
        for bad in (-1, True, float("inf"), float("nan"), "10", 31):
            value = projection(); value["distance"]["byModeMeters"]["onFoot"] = bad
            with self.subTest(bad=bad), self.assertRaises(InvalidRunExport):
                decode_run_export(make_export(projection=value))
        value = projection(); value["distance"]["byModeMeters"]["boat"] = 0
        with self.assertRaises(InvalidRunExport): decode_run_export(make_export(projection=value))

    def test_partial_and_daily_bound(self):
        value = projection(); value["distance"]["travelledMeters"] = 100
        with self.assertRaises(InvalidRunExport): decode_run_export(make_export(projection=value))
        value["distance"]["modesPartial"] = True
        decode_run_export(make_export(projection=value))
        specs = [("day.started", {"dayIndex": 2, "completedDay": {"dayIndex": 1, "distanceDeltaMeters": 6,
                  "distanceByModeDeltas": {"onFoot": 6, "driver": 0}}})]
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_export(projection=value, event_specs=specs))
