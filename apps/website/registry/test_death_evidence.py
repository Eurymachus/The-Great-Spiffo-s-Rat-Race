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
    def test_zombie_wounds_classification_and_authority(self):
        value = evidence()
        value.update(schema=4, cause="zombie_attack", infectedAtDeath=True,
                     terminalWounds=[dict(injuryType="bite", bodyPart="ForeArm_L", remainingTime=10,
                                          bandaged=False, bleedingTime=5, zombieAssociation="bite")])
        decoded = decode_run_export(terminal_export(value))
        self.assertTrue(death_fields(value)["infected_at_death"])
        run = ChallengeRun.objects.create(run_id="wound-authority", export_format=4,
                                         generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        for _ in range(2):
            refresh_initial_run_authority(run, decoded.projection, [])
        summary = RunDeathSummary.objects.get(run=run)
        self.assertTrue(summary.terminal_wounds_captured)
        self.assertEqual(summary.terminal_wounds.count(), 1)
        self.assertEqual(summary.terminal_wounds.get().zombie_association, "bite")
        for kind, origin in (("scratch", "observed_zombie_attack"), ("laceration", "observed_zombie_attack")):
            value["terminalWounds"][0].update(injuryType=kind, zombieAssociation=origin)
            self.assertEqual(death_fields(value)["cause"], "zombie_attack")
        for changes in ({"bandaged": True}, {"bleedingTime": 0}, {"zombieAssociation": "unknown"}):
            other = deepcopy(value)
            other["terminalWounds"][0].update(changes)
            other["cause"] = "BLEEDING"
            self.assertEqual(death_fields(other)["cause"], "BLEEDING")
        value.update(deathDragDown=True, cause="zombie_drag_down", certainty="explicit_flag")
        death_fields(value)
        value.update(medication={"sleepingPillsTaken": 10, "intoxication": 0},
                     cause="mixed", certainty="competing_evidence")
        death_fields(value)
        decoded.projection["deathEvidence"].pop("terminalWounds")
        decoded.projection["deathEvidence"]["cause"] = "BLEEDING"
        refresh_initial_run_authority(run, decoded.projection, [])
        summary.refresh_from_db()
        self.assertFalse(summary.terminal_wounds_captured)
        self.assertFalse(summary.terminal_wounds.exists())

    def test_wound_evidence_rejects_malformed_recovery_and_tampering(self):
        value = evidence()
        value["terminalWounds"] = [dict(injuryType="scratch", bodyPart="Head", remainingTime=1,
                                      bandaged=False, bleedingTime=1, zombieAssociation="unknown")]
        for key, replacement in (("bandaged", 0), ("remainingTime", 0), ("bleedingTime", -1),
                                 ("zombieAssociation", "bite"), ("injuryType", "invented")):
            other = deepcopy(value)
            other["terminalWounds"][0][key] = replacement
            with self.assertRaises(ValueError): death_fields(other)
        other = deepcopy(value)
        other["terminalWounds"] *= 2
        with self.assertRaises(ValueError): death_fields(other)
        other = deepcopy(value)
        other["terminalWounds"][0]["remainingTime"] = 2
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(value, event_evidence=other))
        value.update(captureContext="recovery", recentDamage=[], lastDamageSource="", cause="unknown", certainty="unknown")
        value.pop("location")
        with self.assertRaises(ValueError): death_fields(value)

    def test_poison_sickness_grouping_retains_sources_and_uncertainty(self):
        value = evidence()
        value.update(schema=4, cause="POISON", certainty="suspected", lastDamageSource="SICK",
                     recentDamage=[{"source": "POISON", "amount": 3, "ageMilliseconds": 10000},
                                   {"source": "SICK", "amount": 5, "ageMilliseconds": 0}])
        decoded = decode_run_export(terminal_export(value))
        fields = death_fields(decoded.projection["deathEvidence"])
        self.assertEqual(fields["cause"], "POISON")
        self.assertEqual(fields["last_damage_source"], "SICK")
        self.assertEqual(len(decoded.projection["deathEvidence"]["recentDamage"]), 2)
        other = deepcopy(value); other["cause"] = "SICK"
        with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(other))
        other = deepcopy(value); other["certainty"] = "fatal_threshold"
        with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(other))
        other = deepcopy(value); other.update(killedByFall=True, cause="fall", certainty="explicit_flag")
        decode_run_export(terminal_export(other))
        other = deepcopy(value)
        other.update(medication={"sleepingPillsTaken": 12, "intoxication": 0},
                     cause="mixed", certainty="competing_evidence")
        decode_run_export(terminal_export(other))
        other = deepcopy(value)
        other["recentDamage"].append({"source": "BLEEDING", "amount": 1, "ageMilliseconds": 0})
        other.update(lastDamageSource="BLEEDING", cause="BLEEDING")
        decode_run_export(terminal_export(other))
        value["recentDamage"] = value["recentDamage"][1:]
        value["cause"] = "SICK"
        decode_run_export(terminal_export(value))

    def test_schema_four_subfatal_pills_with_recent_bleeding(self):
        for count in (10, 11, 12):
            for age in (0, 10000):
                value = evidence()
                value.update(schema=4, cause="mixed", certainty="competing_evidence",
                             medication={"sleepingPillsTaken": count, "intoxication": 0},
                             recentDamage=[{"source": "BLEEDING", "amount": 0.02, "ageMilliseconds": age},
                                           {"source": "THIRST", "amount": 0.01, "ageMilliseconds": 0}],
                             lastDamageSource="THIRST")
                with self.subTest(count=count, age=age):
                    decode_run_export(terminal_export(value))
                    value.update(cause="THIRST", certainty="suspected")
                    with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(value))
                    if count < 12:
                        value["schema"] = 3
                        decode_run_export(terminal_export(value))
        for count, source in ((9, "BLEEDING"), (10, "FIRE"), (11, "THIRST")):
            value = evidence()
            value.update(schema=4, cause=source, certainty="suspected", lastDamageSource=source,
                         recentDamage=[{"source": source, "amount": 1, "ageMilliseconds": 0}],
                         medication={"sleepingPillsTaken": count, "intoxication": 15})
            decode_run_export(terminal_export(value))
        value.update(recentDamage=[], lastDamageSource="", cause="unknown", certainty="unknown")
        decode_run_export(terminal_export(value))
        value.pop("medication")
        decode_run_export(terminal_export(value))

    def test_schema_three_sleeping_pills_threshold_and_legacy(self):
        value = evidence()
        value.update(schema=3, recentDamage=[], lastDamageSource="",
                     cause="sleeping_pills", certainty="fatal_threshold",
                     thermalDamageStageAtDeath=0,
                     medication={"sleepingPillsTaken": 12, "intoxication": 0})
        for count in (12, 13):
            for intoxication in (0, 10, 15, 100):
                value["medication"].update(sleepingPillsTaken=count, intoxication=intoxication)
                value["infectedAtDeath"] = True
                decoded = decode_run_export(terminal_export(value))
                self.assertEqual(death_fields(decoded.projection["deathEvidence"])["cause"], "sleeping_pills")
        for count in (0, 9, 10, 11):
            value["medication"]["sleepingPillsTaken"] = count
            with self.subTest(count=count), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))
            other = deepcopy(value); other.update(cause="unknown", certainty="unknown")
            decode_run_export(terminal_export(other))
        value["medication"]["sleepingPillsTaken"] = 12
        for schema in (1, 2):
            other = deepcopy(value); other.update(schema=schema, cause="unknown", certainty="unknown")
            decode_run_export(terminal_export(other))
            other.update(cause="sleeping_pills", certainty="fatal_threshold")
            with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(other))
        for missing in (("medication",), ("thermalDamageStageAtDeath",), ("killedByFall", "deathDragDown")):
            other = deepcopy(value)
            for key in missing: del other[key]
            with self.subTest(missing=missing), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(other))
            other.update(cause="unknown", certainty="unknown")
            decode_run_export(terminal_export(other))

    def test_sleeping_pills_competing_evidence_and_authority(self):
        base = evidence()
        base.update(schema=3, recentDamage=[], lastDamageSource="",
                    cause="mixed", certainty="competing_evidence", thermalDamageStageAtDeath=0,
                    medication={"sleepingPillsTaken": 12, "intoxication": 15})
        competitors = [
            {"killedByFall": True}, {"deathDragDown": True},
            {"thermalDamageStageAtDeath": 1},
            {"recentDamage": [{"source": "BLEEDING", "amount": 0.1, "ageMilliseconds": 10000}],
             "lastDamageSource": "BLEEDING"},
        ]
        run = ChallengeRun.objects.create(run_id="pill-classification", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        for competitor in competitors:
            value = deepcopy(base); value.update(competitor)
            decoded = decode_run_export(terminal_export(value))
            refresh_initial_run_authority(run, decoded.projection, decoded.events)
            run.death_summary.refresh_from_db()
            self.assertEqual(run.death_summary.cause, "mixed")
            self.assertEqual(run.death_summary.sleeping_pills_taken, 12)
            value.update(cause="sleeping_pills", certainty="fatal_threshold")
            with self.subTest(competitor=competitor), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))
        value = deepcopy(base)
        value.update(killedByFall=True, deathDragDown=True, certainty="conflicting_flags")
        decode_run_export(terminal_export(value))
        value = deepcopy(base); value.update(cause="sleeping_pills", certainty="fatal_threshold")
        decoded = decode_run_export(terminal_export(value))
        refresh_initial_run_authority(run, decoded.projection, decoded.events)
        run.death_summary.refresh_from_db()
        self.assertEqual(run.death_summary.cause, "sleeping_pills")
        self.assertEqual(run.death_summary.certainty, "fatal_threshold")

    def test_medication_context_integrity_and_nullable_authority(self):
        value = evidence()
        value["medication"] = {"sleepingPillsTaken": 12, "intoxication": 15}
        decoded = decode_run_export(terminal_export(value))
        self.assertEqual(decoded.projection["deathEvidence"]["cause"], "BLEEDING")
        run = ChallengeRun.objects.create(run_id="medication-authority", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        refresh_initial_run_authority(run, decoded.projection, decoded.events)
        self.assertEqual(run.death_summary.sleeping_pills_taken, 12)
        self.assertEqual(run.death_summary.intoxication_at_death, 15)
        for key in ("sleepingPillsTaken", "intoxication"):
            altered = deepcopy(value)
            altered["medication"][key] = 0
            with self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value, event_evidence=altered))
        value["medication"] = {"sleepingPillsTaken": 0, "intoxication": 0}
        self.assertEqual(death_fields(value)["sleeping_pills_taken"], 0)
        old = decode_run_export(terminal_export(evidence()))
        refresh_initial_run_authority(run, old.projection, old.events)
        run.death_summary.refresh_from_db()
        self.assertIsNone(run.death_summary.sleeping_pills_taken)
        self.assertIsNone(run.death_summary.intoxication_at_death)

    def test_rejects_invalid_medication_and_recovery(self):
        for bad in (None, [], {}, {"sleepingPillsTaken": 1}):
            value = evidence(); value["medication"] = bad
            with self.subTest(bad=bad), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))
        for key, bad in (("sleepingPillsTaken", -1), ("sleepingPillsTaken", True),
                         ("sleepingPillsTaken", 1.5), ("sleepingPillsTaken", 2**31),
                         ("intoxication", -1), ("intoxication", 101),
                         ("intoxication", True), ("intoxication", float("nan"))):
            value = evidence()
            value["medication"] = {"sleepingPillsTaken": 12, "intoxication": 15}
            value["medication"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                death_fields(value)
        value = evidence()
        value.update(captureContext="recovery", recentDamage=[], lastDamageSource="",
                     cause="unknown", certainty="unknown")
        value.pop("location")
        value["medication"] = {"sleepingPillsTaken": 0, "intoxication": 0}
        with self.assertRaises(ValueError):
            death_fields(value)

    def test_fatal_hypothermia_threshold_and_legacy_classification(self):
        value = evidence()
        value.update(schema=2, recentDamage=[], lastDamageSource="",
                     cause="hypothermia", certainty="fatal_threshold",
                     thermalDamageStageAtDeath=1,
                     lastLivingThermal={"hypothermiaLevel": 4, "damageStage": 0.999943,
                         "observedUtc": 1784800000, "observedWorldAgeHours": 1, "ageMilliseconds": 2})
        decoded = decode_run_export(terminal_export(value))
        self.assertEqual(death_fields(decoded.projection["deathEvidence"])["cause"], "hypothermia")
        for key, bad in (("hypothermiaLevel", 3), ("ageMilliseconds", 1001),
                         ("damageStage", 0), ("damageStage", 1)):
            other = deepcopy(value); other["lastLivingThermal"][key] = bad
            with self.subTest(key=key), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(other))
        other = deepcopy(value); other["thermalDamageStageAtDeath"] = 0.999
        with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(other))
        other = deepcopy(value); other.update(killedByFall=True, cause="fall", certainty="explicit_flag")
        decode_run_export(terminal_export(other))
        other = deepcopy(value); other.update(recentDamage=[{"source":"BLEEDING", "amount":1, "ageMilliseconds":0}],
                                              lastDamageSource="BLEEDING", cause="BLEEDING", certainty="suspected")
        decode_run_export(terminal_export(other))
        value.update(schema=1, cause="unknown", certainty="unknown")
        decode_run_export(terminal_export(value))
        value["schema"] = 2
        with self.assertRaises(InvalidRunExport): decode_run_export(terminal_export(value))

    def test_last_living_thermal_snapshot_and_terminal_stage_are_independent(self):
        value = evidence()
        value["lastLivingThermal"] = {"hypothermiaLevel": 4, "damageStage": 0.9,
            "observedUtc": 1784800000, "observedWorldAgeHours": 0.99, "ageMilliseconds": 25}
        value["thermalDamageStageAtDeath"] = 1
        decoded = decode_run_export(terminal_export(value))
        self.assertEqual(decoded.projection["deathEvidence"]["cause"], "BLEEDING")
        run = ChallengeRun.objects.create(run_id="thermal-authority", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        refresh_initial_run_authority(run, decoded.projection, decoded.events)
        death = run.death_summary
        self.assertEqual(death.last_living_hypothermia_level, 4)
        self.assertEqual(death.last_living_thermal_damage_stage, 0.9)
        self.assertEqual(death.last_living_thermal_age_milliseconds, 25)
        self.assertEqual(death.thermal_damage_stage_at_death, 1)
        altered = deepcopy(value)
        altered["lastLivingThermal"]["hypothermiaLevel"] = 0
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(value, event_evidence=altered))
        for key, bad in (("hypothermiaLevel", 5), ("hypothermiaLevel", True),
                         ("hypothermiaLevel", 1.5), ("damageStage", 1.1),
                         ("ageMilliseconds", -1), ("observedUtc", "1"),
                         ("observedWorldAgeHours", float("nan"))):
            bad_value = deepcopy(value); bad_value["lastLivingThermal"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                death_fields(bad_value)
        old = decode_run_export(terminal_export(evidence()))
        refresh_initial_run_authority(run, old.projection, old.events)
        death.refresh_from_db()
        self.assertIsNone(death.last_living_hypothermia_level)
        self.assertIsNone(death.thermal_damage_stage_at_death)
        value.update(captureContext="recovery", recentDamage=[], lastDamageSource="", cause="unknown", certainty="unknown")
        with self.assertRaises(ValueError): death_fields(value)


    def test_sickness_context_is_independent_and_normalized(self):
        value = evidence()
        value["sickness"] = {"foodSickness": 80, "poison": 0,
                             "corpseSicknessRate": 0.01, "woundInfectionLevel": 4}
        value["recentDamage"][0].update(source="SICK", sickness={
            "foodSickness": 75, "poison": 12, "corpseSicknessRate": 0, "woundInfectionLevel": 0})
        decoded = decode_run_export(terminal_export(value))
        self.assertEqual(decoded.projection["deathEvidence"]["cause"], "BLEEDING")
        run = ChallengeRun.objects.create(run_id="sickness-authority", export_format=4,
            generated_at=datetime.now(timezone.utc), event_hash="0" * 64)
        for _ in range(2):
            refresh_initial_run_authority(run, decoded.projection, decoded.events)
        death = run.death_summary
        self.assertEqual(death.food_sickness, 80)
        self.assertEqual(death.poison, 0)
        self.assertEqual(death.recent_damage.get(source="SICK").poison, 12)
        self.assertIsNone(death.recent_damage.get(source="BLEEDING").poison)
        other = deepcopy(value)
        other["sickness"]["poison"] = 1
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(value, event_evidence=other))
        other = deepcopy(value)
        other["recentDamage"][0]["sickness"]["poison"] = 1
        with self.assertRaises(InvalidRunExport):
            decode_run_export(terminal_export(value, event_evidence=other))
        old = decode_run_export(terminal_export(evidence()))
        refresh_initial_run_authority(run, old.projection, old.events)
        death.refresh_from_db()
        self.assertIsNone(death.food_sickness)

    def test_rejects_invalid_sickness_and_recovery_context(self):
        for bad in (None, [], {}, {"foodSickness": 1}):
            value = evidence(); value["sickness"] = bad
            with self.subTest(bad=bad), self.assertRaises(InvalidRunExport):
                decode_run_export(terminal_export(value))
        for key in ("foodSickness", "poison", "corpseSicknessRate", "woundInfectionLevel"):
            for bad in (-1, True, "1", float("inf"), float("nan")):
                value = evidence()
                value["sickness"] = dict.fromkeys(("foodSickness", "poison", "corpseSicknessRate", "woundInfectionLevel"), 0)
                value["sickness"][key] = bad
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    death_fields(value)
        value = evidence()
        value.update(captureContext="recovery", recentDamage=[], lastDamageSource="", cause="unknown", certainty="unknown")
        value.pop("location")
        value["sickness"] = dict.fromkeys(("foodSickness", "poison", "corpseSicknessRate", "woundInfectionLevel"), 0)
        with self.assertRaises(ValueError): death_fields(value)


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
