from datetime import datetime, timezone

from django.test import TestCase
from django.template.loader import render_to_string

from .models import ChallengeRun, RunTemperatureSummary
from .run_authority import refresh_initial_run_authority
from .run_exports import decode_run_export, InvalidRunExport
from .run_public import build_temperature_context
from .test_run_exports import make_export


def weather(low=-13.7, high=4.5, partial=False):
    def observation(value, hour):
        return dict(celsius=value, utc=100, worldAgeHours=hour, timeOfDay=hour,
                    calendar=dict(year=1993, month=1, day=1))
    return dict(schema=1, unit="celsius", source="outdoor_weather",
                sampleIntervalGameMinutes=1, partial=partial,
                minimum=observation(low, 6), maximum=observation(high, 15))


class TemperatureTests(TestCase):
    def setUp(self):
        self.run = ChallengeRun.objects.create(run_id="temperature-test", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        self.projection = dict(schema=2, character={}, outposts=[], skills=[],
            outdoorTemperature=weather(-20, 35, True),
            activeDay=dict(dayIndex=2, outdoorTemperature=weather(0, 2)))
        self.events = [dict(event_type="day.started", payload=dict(dayIndex=2,
            completedDay=dict(dayIndex=1, outdoorTemperature=weather())))]

    def test_authority_keeps_independent_records_and_daily_timestamps(self):
        refresh_initial_run_authority(self.run, self.projection, self.events)
        summary = RunTemperatureSummary.objects.get(run=self.run)
        self.assertEqual(summary.temperature_minimum, -20)
        self.assertEqual(summary.temperature_maximum, 35)
        self.assertTrue(summary.temperature_partial)
        sealed = self.run.daily_records.get(state="sealed")
        self.assertEqual(sealed.temperature_minimum, -13.7)
        self.assertEqual(sealed.temperature_minimum_observation["timeOfDay"], 6)
        context = build_temperature_context(self.run)
        self.assertEqual([p["minimum"] for p in context["temperature_chart_data"]], [-13.7, 0])
        self.assertEqual(context["temperature_chart_data"][0]["month"], 1)
        html = render_to_string("registry/public_run_detail.html", {"run": self.run, **context})
        self.assertIn('data-outpost-dialog-open="run-temperature-dialog"', html)
        self.assertIn('data-temperature-series="maximum" checked', html)
        self.assertIn('data-temperature-series="minimum" checked', html)
        self.assertIn("35.0", html)

    def test_incremental_update_preserves_sealed_days_and_replaces_summary(self):
        refresh_initial_run_authority(self.run, self.projection, self.events)
        sealed = self.run.daily_records.get(state="sealed")
        self.projection["outdoorTemperature"] = weather(-30, 35)
        self.projection["activeDay"]["outdoorTemperature"] = weather(-30, 2)
        refresh_initial_run_authority(self.run, self.projection, self.events, previous_event_sequence=1)
        self.assertEqual(self.run.daily_records.get(state="sealed").pk, sealed.pk)
        self.assertEqual(RunTemperatureSummary.objects.get(run=self.run).temperature_minimum, -30)
        self.assertEqual(self.run.daily_records.get(state="active").temperature_minimum, -30)

    def test_older_exports_remain_unknown(self):
        refresh_initial_run_authority(self.run, dict(schema=2, character={}, outposts=[],
            activeDay=dict(dayIndex=1)), [])
        self.assertFalse(RunTemperatureSummary.objects.filter(run=self.run).exists())
        self.assertIsNone(self.run.daily_records.get().temperature_minimum)
        context = build_temperature_context(self.run)
        self.assertEqual(context["temperature_chart_data"], [])
        html = render_to_string("registry/public_run_detail.html", {"run": self.run, **context})
        self.assertIn("No approved daily temperature history", html)

    def test_decoder_validates_daily_and_run_temperature_evidence(self):
        for location in ("summary", "active", "sealed"):
            for bad in (float("inf"), True, "cold"):
                with self.subTest(location=location, bad=bad):
                    value = weather()
                    value["minimum"]["celsius"] = bad
                    projection = dict(schema=1, character={}, currentKills=42)
                    events = [("day.started", {})]
                    if location == "summary": projection["outdoorTemperature"] = value
                    elif location == "active": projection["activeDay"] = {"outdoorTemperature": value}
                    else: events = [("day.started", {"completedDay": {"outdoorTemperature": value}})]
                    with self.assertRaises(InvalidRunExport):
                        decode_run_export(make_export(projection=projection, event_specs=events))
        projection = dict(schema=1, character={}, currentKills=42, outdoorTemperature=weather())
        self.assertEqual(decode_run_export(make_export(projection=projection)).projection["outdoorTemperature"]["minimum"]["celsius"], -13.7)
