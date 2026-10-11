import re
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from .run_review import EVENT_LABELS, _event_rows


class EventEvidenceTests(SimpleTestCase):
    def test_every_registered_event_has_readable_evidence(self):
        root = Path(__file__).resolve().parents[3]
        registry = root / "Contents/mods/Great Spiffo's Rat Race/42.21/media/lua/shared/TGSRR/Run/EventTypes.lua"
        registered = set(re.findall(r'\["([a-z._]+)"\] = true', registry.read_text()))
        self.assertEqual(registered, set(EVENT_LABELS))
        with patch("registry.run_review._catalogue_name", return_value="Readable name"):
            for name in registered:
                with self.subTest(event=name):
                    event = {"sequence": 1, "event_type": name, "payload": {
                        "skillId": "raw_skill", "details": {"enabled": True, "count": 1200},
                        "calendar": {"year": 1993, "month": 9, "day": 7},
                    }}
                    row = _event_rows([event])[0]
                    fields = {f["label"]: f["value"] for f in row["evidence_fields"]}
                    self.assertEqual(fields["Skill"], "Readable name")
                    self.assertEqual(fields["Details / Enabled"], "Yes")
                    self.assertEqual(fields["Details / Count"], "1,200")
                    self.assertEqual(fields["Calendar"], "07 September 1993")
                    self.assertIn("raw_skill", row["event_json"])

    def test_event_specific_units_and_unknown_extensions(self):
        rows = _event_rows([
            {"sequence": 1, "event_type": "kills.milestone.reached", "payload": {"threshold": 10000, "previous": 9999, "current": 10000}},
            {"sequence": 2, "event_type": "outpost.deliverable.completed", "payload": {"value": {"current": 10, "required": 10, "state": "completed"}}},
            {"sequence": 3, "event_type": "future.custom.event", "payload": {"newField": [{"someFlag": False}]}}
        ])
        self.assertEqual(rows[0]["evidence_fields"][0], {"label": "Kill milestone", "value": "10,000"})
        self.assertEqual(rows[1]["evidence_fields"][0], {"label": "Progress / Amount completed", "value": "10"})
        self.assertEqual(rows[2]["evidence_fields"][0], {"label": "New field (1) / Some flag", "value": "No"})
