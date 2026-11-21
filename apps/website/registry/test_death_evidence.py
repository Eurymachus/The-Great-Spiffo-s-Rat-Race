from copy import deepcopy
from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse

from .death_evidence import death_fields
from .models import ChallengeRun, RunDeathSummary, RunSubmission, Participant
from .run_authority import refresh_initial_run_authority
from .run_exports import InvalidRunExport, decode_run_export
from .test_run_exports import make_export, make_block_export_from_bodies, event_body


def evidence():
    return {
        "schema": 1, "captureContext": "death_callback",
        "recentWindowMilliseconds": 10000,
        "killedByFall": False, "deathDragDown": False,
        "lastDamageSource": "BLEEDING", "cause": "BLEEDING", "certainty": "suspected",
        "recentDamage": [
            {"source": "FIRE", "amount": 2, "ageMilliseconds": 40},
            {"source": "BLEEDING", "amount": 0.2, "ageMilliseconds": 0},
        ],
        "location": {"x": 100, "y": 200, "z": -1, "buildingId": "12345678901234567",
                     "capturedUtc": 1784800001, "worldAgeHours": 1, "partial": False,
                     "registeredLocation": {"kind": "outpost", "id": "echo_creek", "registryVersion": 1}},
    }


def terminal_export(value, *, event_evidence=None):
    projection = {
        "schema": 1, "currentKills": 42, "character": {}, "lifecycle": "deceased",
        "endedReason": "deceased", "endedUtc": 1784800001,
        "endedWorldAgeHours": 1, "endedEventSequence": 1,
        "deathEvidence": value,
    }
    return make_export(projection=projection, event_specs=[
        ("run.ended", {"reason": "deceased", "deathEvidence": value if event_evidence is None else event_evidence})
    ])


class DeathEvidenceTests(TestCase):
    def test_infection_is_nullable_independent_context_and_integrity_checked(self):
        value = evidence()
        self.assertIsNone(death_fields(value)["infected_at_death"])
        for infected in (True, False):
            value.update(infectedAtDeath=infected, killedByFall=True,
                         cause="fall", certainty="explicit_flag")
            decoded = decode_run_export(terminal_export(value))
            self.assertIs(death_fields(decoded.projection["deathEvidence"])["infected_at_death"], infected)
            self.assertEqual(decoded.projection["deathEvidence"]["cause"], "fall")
        other = deepcopy(value)
        other["infectedAtDeath"] = True
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(value, event_evidence=other))
        for invalid in (0, 1, "true", None):
            value["infectedAtDeath"] = invalid
            with self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))

    def test_compacted_location_flag_matches_full_terminal_event(self):
        full = evidence()
        compact = deepcopy(full)
        del compact["location"]["partial"]
        decoded = decode_run_export(terminal_export(compact, event_evidence=full))
        self.assertNotIn("partial", decoded.projection["deathEvidence"]["location"])
        self.assertIs(decoded.events[0]["payload"]["deathEvidence"]["location"]["partial"], False)
        self.assertEqual(death_fields(compact), death_fields(full))
        body = event_body("rr-web-test", 1, "run.ended", {"reason": "deceased", "deathEvidence": full})
        self.assertEqual(decode_run_export(make_block_export_from_bodies(
            [body], projection=decoded.projection)).projection, decoded.projection)
        compact["location"]["partial"] = True
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(compact, event_evidence=full))

    def test_format_four_terminal_block_validates_evidence(self):
        value = evidence()
        projection = decode_run_export(terminal_export(value)).projection
        body = event_body("rr-web-test", 1, "run.ended", {"reason": "deceased", "deathEvidence": value})
        encoded = make_block_export_from_bodies([body], projection=projection)
        self.assertEqual(decode_run_export(encoded).projection["deathEvidence"], value)
        projection["deathEvidence"]["location"]["x"] += 1
        with self.assertRaises(InvalidRunExport):
            decode_run_export(make_block_export_from_bodies([body], projection=projection))

    def test_death_authority_is_published_only_on_approval(self):
        participant = Participant.objects.create_user(email="death@example.com", nickname="Death Test",
            password="test-password", is_active=True, status=Participant.Status.VERIFIED)
        self.client.force_login(participant)
        self.client.post(reverse("registry:submit_run"), {
            "manual_evidence_url": "https://www.twitch.tv/videos/123456",
            "run_export": terminal_export(evidence()),
        })
        submission = RunSubmission.objects.get()
        self.assertFalse(RunDeathSummary.objects.exists())
        administrator = Participant.objects.create_superuser(email="death-admin@example.com",
            nickname="Death Reviewer", password="test-password")
        self.client.force_login(administrator)
        self.client.post(reverse("admin:registry_runsubmission_approve", args=(submission.pk,)))
        submission.refresh_from_db()
        self.assertEqual(submission.status, RunSubmission.Status.APPROVED)
        self.assertEqual(RunDeathSummary.objects.get().last_damage_source, "BLEEDING")

    def test_terminal_export_preserves_evidence_and_rejects_projection_tampering(self):
        value = evidence()
        decoded = decode_run_export(terminal_export(value))
        self.assertEqual(decoded.projection["deathEvidence"], value)
        other = deepcopy(value)
        other["location"]["x"] += 1
        with self.assertRaisesMessage(InvalidRunExport, "does not match"):
            decode_run_export(terminal_export(value, event_evidence=other))
        other = deepcopy(value)
        other["killedByFall"] = 0  # Python equality alone considers 0 == False.
        with self.assertRaisesMessage(InvalidRunExport, "invalid death evidence"):
            decode_run_export(terminal_export(value, event_evidence=other))

    def test_rejects_malformed_or_overconfident_evidence(self):
        variants = []
        for key, replacement in (("certainty", "explicit_flag"), ("schema", True),
                                 ("lastDamageSource", "FIRE"), ("killedByFall", 1),
                                 ("recentWindowMilliseconds", 99999)):
            value = evidence()
            value[key] = replacement
            variants.append(value)
        for key, replacement in (("ageMilliseconds", 10001), ("amount", -1), ("amount", True)):
            value = evidence()
            value["recentDamage"][0][key] = replacement
            variants.append(value)
        value = evidence()
        value["recentDamage"].append(value["recentDamage"][-1])
        variants.append(value)
        value = evidence()
        value["location"]["x"] = 1.5
        variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))

    def test_flags_override_suspicion_but_preserve_last_source(self):
        value = evidence()
        value.update(killedByFall=True, cause="fall", certainty="explicit_flag")
        self.assertEqual(death_fields(value)["last_damage_source"], "BLEEDING")
        value.update(deathDragDown=True, cause="mixed", certainty="conflicting_flags")
        self.assertEqual(death_fields(value)["cause"], "mixed")

    def test_recovery_does_not_invent_recent_damage_or_location(self):
        value = {"schema": 1, "captureContext": "recovery", "recentWindowMilliseconds": 10000,
                 "recentDamage": [], "lastDamageSource": "", "cause": "unknown", "certainty": "unknown"}
        fields = death_fields(value)
        self.assertIsNone(fields["x"])
        self.assertIsNone(fields["killed_by_fall"])
        value["recentDamage"] = evidence()["recentDamage"]
        value.update(lastDamageSource="BLEEDING", cause="BLEEDING", certainty="suspected")
        with self.assertRaises(ValueError):
            death_fields(value)

    def test_authority_replaces_evidence_without_duplicate_damage_rows(self):
        run = ChallengeRun.objects.create(run_id="death-authority", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        projection = decode_run_export(terminal_export(evidence())).projection
        projection["deathEvidence"]["infectedAtDeath"] = True
        for _ in range(2):
            refresh_initial_run_authority(run, projection, [])
        summary = RunDeathSummary.objects.get(run=run)
        self.assertEqual(summary.x, 100)
        self.assertEqual(summary.building_def_id, "12345678901234567")
        self.assertEqual(summary.registered_raw_id, "echo_creek")
        self.assertEqual(list(summary.recent_damage.values_list("source", flat=True)), ["FIRE", "BLEEDING"])
        self.assertEqual(summary.certainty, "suspected")
        self.assertIs(summary.infected_at_death, True)
        projection["deathEvidence"]["infectedAtDeath"] = False
        refresh_initial_run_authority(run, projection, [])
        summary.refresh_from_db()
        self.assertIs(summary.infected_at_death, False)
        del projection["deathEvidence"]["infectedAtDeath"]
        refresh_initial_run_authority(run, projection, [])
        summary.refresh_from_db()
        self.assertIsNone(summary.infected_at_death)
        # An older accepted contract has unknown coverage, not false flags/zero coordinates.
        del projection["deathEvidence"]
        refresh_initial_run_authority(run, projection, [])
        self.assertFalse(RunDeathSummary.objects.filter(run=run).exists())
