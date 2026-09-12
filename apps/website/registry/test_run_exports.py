import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import LogEntry
from django.test import TestCase
from django.urls import reverse

from . import run_exports
from .models import (
    ChallengeMode,
    ChallengeRun,
    Notification,
    Participant,
    ParticipantChallengeModeLimit,
    RunCharacterTrait,
    RunDailyMetric,
    RunDailyRecord,
    RunKillSummary,
    RunOutpost,
    RunOutpostDeliverable,
    RunSkill,
    RunStartingLocation,
    RunStatisticMetric,
    RunStatisticSummary,
    RunSubmission,
    RunWeaponKill,
    StreamingAccount,
    StreamingMedia,
    VerifiedRunEventBlock,
)
from .run_block_cache import decode_run_export_cached
from .run_authority import refresh_initial_run_authority
from .run_exports import InvalidRunExport, decode_run_export
from .run_review import build_run_review, capture_preapproval_assessment


def frame(value):
    value = value if isinstance(value, bytes) else str(value).encode()
    return str(len(value)).encode() + b":" + value


def tagged(tag, value):
    return tag.encode() + frame(value)


def canonical_value(value):
    if value is None:
        return b"z0:"
    if isinstance(value, bool):
        return tagged("b", "1" if value else "0")
    if isinstance(value, (int, float)):
        return tagged("n", value)
    if isinstance(value, str):
        return tagged("s", value)
    if isinstance(value, list):
        return tagged("a", b"".join(canonical_value(item) for item in value))
    content = b"".join(
        tagged("k", key) + canonical_value(value[key]) for key in sorted(value)
    )
    return tagged("m", content)


def event_body(
    run_id,
    sequence,
    event_type,
    payload,
    event_schema=2,
    *,
    epoch=1,
    utc=None,
    world_age_hours=None,
):
    return b"".join(
        (
            tagged("v", event_schema),
            tagged("r", run_id),
            tagged("e", epoch),
            tagged("q", sequence),
            tagged("t", 1784800000 + sequence if utc is None else utc),
            tagged("w", sequence if world_age_hours is None else world_age_hours),
            tagged("y", event_type),
            tagged("p", canonical_value(payload)),
        )
    )


def literal_lzss(value):
    output = bytearray()
    for cursor in range(0, len(value), 8):
        chunk = value[cursor : cursor + 8]
        output.append((1 << len(chunk)) - 1)
        output.extend(chunk)
    return bytes(output)


def make_export_from_bodies(
    bodies,
    *,
    run_id="rr-web-test",
    generated_at=1784800100,
    projection_bytes=None,
):
    previous_hash = "0" * 64
    for body in bodies:
        previous_hash = hashlib.sha256(previous_hash.encode() + body).hexdigest()
    body_frames = b"".join(frame(body) for body in bodies)
    canonical = b"".join(
        frame(value)
        for value in (
            3,
            run_id,
            generated_at,
            len(bodies),
            previous_hash,
            projection_bytes,
            body_frames,
        )
    )
    checksum = hashlib.sha256(canonical).hexdigest()
    payload = base64.urlsafe_b64encode(literal_lzss(canonical)).decode().rstrip("=")
    return f"TGSRR1.LZ1.{payload}.{checksum}"


def make_block_export_from_bodies(
    bodies,
    *,
    run_id="rr-web-test",
    generated_at=1784800100,
    projection=None,
    block_size=2,
):
    previous_hash = "0" * 64
    hashes = []
    for body in bodies:
        previous_hash = hashlib.sha256(previous_hash.encode() + body).hexdigest()
        hashes.append(previous_hash)
    descriptors = []
    encoded_blocks = []
    for first in range(0, len(bodies), block_size):
        block_bodies = bodies[first:first + block_size]
        canonical = b"".join(frame(body) for body in block_bodies)
        checksum = hashlib.sha256(canonical).hexdigest()
        payload = base64.urlsafe_b64encode(literal_lzss(canonical)).decode().rstrip("=")
        encoded_blocks.extend((payload, checksum))
        descriptors.append({
            "count": len(block_bodies),
            "firstSequence": first + 1,
            "lastSequence": first + len(block_bodies),
            "lastHash": hashes[first + len(block_bodies) - 1],
            "checksum": checksum,
        })
    manifest = canonical_value({
        "format": 4,
        "runId": run_id,
        "generatedUtc": generated_at,
        "eventSequence": len(bodies),
        "eventHash": previous_hash,
        "projection": projection,
        "eventBlocks": descriptors,
    })
    manifest_checksum = hashlib.sha256(manifest).hexdigest()
    manifest_payload = base64.urlsafe_b64encode(
        literal_lzss(manifest)
    ).decode().rstrip("=")
    return ".".join((
        "TGSRR1", "BLK1", manifest_payload, manifest_checksum,
        *encoded_blocks,
    ))


def make_export(
    run_id="rr-web-test",
    kills=42,
    event_specs=None,
    projection=None,
    challenge=None,
    generated_at=1784800100,
    event_schema=2,
    event_options=None,
):
    event_specs = event_specs or [
        ("session.started", {"character": {"displayName": "Test Survivor"}}),
        ("day.started", {"partial": False}),
    ]
    event_options = event_options or {}
    bodies = [
        event_body(
            run_id,
            sequence,
            event_type,
            payload,
            event_schema,
            **event_options,
        )
        for sequence, (event_type, payload) in enumerate(event_specs, start=1)
    ]
    projection = projection or {
        "schema": 1,
        "currentKills": kills,
        "character": {
            "starting": {"displayName": "Starting Survivor"},
            "chosenStartingRegion": {
                "schema": 1,
                "selectionMode": "explicit",
                "resolvedRegionId": "Muldraugh, KY",
                "capturedUtc": 1784800000,
            },
            "startingLocation": {
                "x": 10835,
                "y": 10144,
                "z": 0,
                "buildingId": "10835,10144,0",
                "registeredLocation": None,
                "capturedUtc": 1784800000,
                "worldAgeHours": 0,
                "partial": False,
            },
            "current": {"displayName": "Test Survivor"},
            "selectedStartingTraits": ["base:Strong"],
            "selectedStartingTraitsPartial": False,
            "selectedStartingTraitsCapturedUtc": 1784800000,
            "startingEffectiveTraits": ["base:Strong"],
            "currentEffectiveTraits": ["base:Strong"],
        },
    }
    if challenge is not None:
        projection["challenge"] = challenge
    return make_export_from_bodies(
        bodies,
        run_id=run_id,
        generated_at=generated_at,
        projection_bytes=canonical_value(projection),
    )


def lifecycle_summary(*, complete=False, sequence=None, regression_sequence=None):
    def point(value):
        return {
            "sequence": value,
            "utc": 1784800000 + value,
            "worldAgeHours": value,
            "elapsedDays": value / 24,
        }

    completion = point(sequence) if sequence is not None else None
    regression = point(regression_sequence) if regression_sequence is not None else None
    return {
        "firstCompletion": completion,
        "latestCompletion": completion,
        "latestRegression": regression,
        "completionCount": 1 if completion else 0,
        "regressionCount": 1 if regression else 0,
        "currentState": "complete" if complete else "incomplete",
    }


def outpost_lifecycle_projection():
    outpost_ids = sorted(
        {
            "brandenburg", "echo_creek", "ekron", "fallas_lake",
            "hog_wallow_military_base", "irvington", "louisville",
            "march_ridge", "muldraugh", "riverside", "rosewood",
            "valley_station", "west_point",
        }
    )
    deliverable_ids = sorted(
        {
            "room_activation", "floor_activation", "zombie_clearance",
            "window_barricades", "enclosed", "doors_fitted", "doors_closed",
            "good_bed", "generator", "food", "plumbed_sink", "spare_car",
            "engine_start",
        }
    )
    return [
        {
            "id": outpost_id,
            "complete": False,
            "lifecycle": lifecycle_summary(),
            "deliverables": [
                {
                    "id": deliverable_id,
                    "passed": False,
                    "lifecycle": lifecycle_summary(),
                }
                for deliverable_id in deliverable_ids
            ],
        }
        for outpost_id in outpost_ids
    ]


class RunExportCodecTests(TestCase):
    def test_reuses_verified_format_four_event_blocks(self):
        run_id = "rr-block-cache-test"
        bodies = [
            event_body(run_id, 1, "session.started", {"character": {}}),
            event_body(run_id, 2, "day.started", {"partial": False}),
            event_body(run_id, 3, "day.started", {"partial": False}),
        ]
        value = make_block_export_from_bodies(
            bodies,
            run_id=run_id,
            projection={"schema": 1, "currentKills": 0, "character": {}},
        )
        decoded = decode_run_export_cached(value)
        for item in decoded.event_blocks:
            descriptor = item["descriptor"]
            VerifiedRunEventBlock.objects.create(
                checksum=descriptor["checksum"],
                first_sequence=descriptor["firstSequence"],
                last_sequence=descriptor["lastSequence"],
                event_count=descriptor["count"],
                starting_hash=item["starting_hash"],
                last_hash=descriptor["lastHash"],
                canonical=item["canonical"],
                events=item["events"],
            )

        with patch(
            "registry.run_exports._decompress", wraps=run_exports._decompress
        ) as decompress:
            cached = decode_run_export_cached(value)

        self.assertEqual(cached.events, decoded.events)
        self.assertEqual(decompress.call_count, 1)

    def test_accepts_format_four_independent_event_blocks(self):
        run_id = "rr-block-test"
        bodies = [
            event_body(run_id, 1, "session.started", {
                "character": {"displayName": "Block Survivor"},
            }),
            event_body(run_id, 2, "day.started", {"partial": False}),
            event_body(run_id, 3, "day.started", {"partial": False}),
        ]
        projection = {
            "schema": 1,
            "currentKills": 42,
            "character": {"current": {"displayName": "Block Survivor"}},
        }

        decoded = decode_run_export(make_block_export_from_bodies(
            bodies, run_id=run_id, projection=projection,
        ))

        self.assertEqual(decoded.format, 4)
        self.assertEqual(decoded.event_sequence, 3)
        self.assertEqual(decoded.character_name, "Block Survivor")

    def test_accepts_and_preserves_sparse_schema_two_outpost_lifecycle_contract(self):
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": [],
        }

        decoded = decode_run_export(make_export(projection=projection))

        self.assertEqual(decoded.projection["schema"], 2)
        self.assertEqual(decoded.projection["outposts"], [])

    def test_rejects_schema_two_outpost_lifecycle_state_mismatch(self):
        outposts = outpost_lifecycle_projection()
        outposts[0]["deliverables"][0]["lifecycle"]["currentState"] = "complete"
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": outposts,
        }

        with self.assertRaisesMessage(
            InvalidRunExport, "invalid outpost lifecycle summaries"
        ):
            decode_run_export(make_export(projection=projection))

    def test_rejects_started_spare_car_when_no_spare_car_is_present(self):
        outposts = outpost_lifecycle_projection()
        deliverables = {
            item["id"]: item for item in outposts[0]["deliverables"]
        }
        deliverables["engine_start"]["passed"] = True
        deliverables["engine_start"]["lifecycle"] = lifecycle_summary(
            complete=True, sequence=1
        )
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": outposts,
        }

        with self.assertRaisesMessage(
            InvalidRunExport, "invalid outpost lifecycle summaries"
        ):
            decode_run_export(
                make_export(
                    projection=projection,
                    event_specs=[{
                        "type": "outpost.deliverable.completed",
                        "payload": {
                            "outpostId": outposts[0]["id"],
                            "deliverableId": "engine_start",
                        },
                    }],
                )
            )

    def test_rejects_schema_two_first_completion_missing_from_ledger(self):
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": outpost_lifecycle_projection(),
        }
        projection["outposts"][0]["deliverables"][0]["passed"] = True
        projection["outposts"][0]["deliverables"][0]["lifecycle"] = (
            lifecycle_summary(complete=True, sequence=1)
        )

        with self.assertRaisesMessage(
            InvalidRunExport, "do not match the verified ledger"
        ):
            decode_run_export(
                make_export(
                    projection=projection,
                    event_specs=[],
                )
            )

    def test_rejects_regression_events_in_bounded_lifecycle_contract(self):
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": [],
        }
        with self.assertRaisesMessage(
            InvalidRunExport, "do not match the verified ledger"
        ):
            decode_run_export(make_export(
                projection=projection,
                event_specs=[("outpost.regressed", {"outpostId": "echo_creek"})],
            ))

    def test_decodes_matching_deceased_terminal_state(self):
        projection = {
            "schema": 1,
            "currentKills": 42,
            "character": {"current": {"displayName": "Late Survivor"}},
            "lifecycle": "deceased",
            "endedReason": "deceased",
            "endedUtc": 1784800003,
            "endedWorldAgeHours": 3,
            "endedEventSequence": 3,
        }
        decoded = decode_run_export(
            make_export(
                projection=projection,
                event_specs=[
                    ("session.started", {"character": {"displayName": "Late Survivor"}}),
                    ("day.started", {"partial": False}),
                    ("run.ended", {"reason": "deceased"}),
                ],
            )
        )

        self.assertEqual(decoded.lifecycle, "deceased")

    def test_rejects_terminal_event_without_matching_projection(self):
        with self.assertRaisesMessage(
            InvalidRunExport,
            "terminal run event has no matching lifecycle projection",
        ):
            decode_run_export(
                make_export(
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Test Survivor"}}),
                        ("run.ended", {"reason": "deceased"}),
                    ]
                )
            )

    def test_decodes_real_current_contract_export(self):
        fixture = (
            Path(__file__).with_name("testdata")
            / "format3_event2_projection1.txt"
        )

        decoded = decode_run_export(fixture.read_text(encoding="utf-8"))

        self.assertEqual(decoded.format, 3)
        self.assertEqual(
            decoded.run_id,
            "rr-1785152260-1785152260039-225317-444485",
        )
        self.assertEqual(decoded.event_sequence, 21)
        self.assertEqual(
            decoded.event_hash,
            "08a2fc2c61ac86b72d6e8234acc12bc080e156ffb5e01a7d96e36c627d8eca43",
        )
        self.assertEqual(
            decoded.checksum,
            "ab96abe36f137b2376549f2731f8140044217a97fb1868495cd836df40188d0a",
        )
        self.assertEqual({event["schema"] for event in decoded.events}, {2})
        self.assertEqual(decoded.projection["schema"], 1)
        self.assertEqual(
            decoded.projection["challenge"],
            {
                "id": "TGSRR",
                "gameMode": "The Great Spiffo's Rat Race",
            },
        )
        self.assertEqual(decoded.current_kills, 6124)
        self.assertEqual(len(decoded.projection["skills"]), 35)
        self.assertEqual(len(decoded.projection["outposts"]), 13)
        self.assertEqual(len(decoded.projection["townVisits"]["towns"]), 12)
        self.assertEqual(
            decoded.events[-1]["payload"]["challenge"]["id"],
            "TGSRR",
        )
        expected_contract_sections = {
            "activeDay",
            "activeGameplay",
            "activeMods",
            "animalBirths",
            "animalsSlaughtered",
            "animalsTrapped",
            "brokenWeapons",
            "butterProduced",
            "challenge",
            "challengeProgress",
            "character",
            "currentKills",
            "distance",
            "fireDeaths",
            "fishCaught",
            "generatorKnowledge",
            "injuries",
            "literature",
            "locations",
            "milestones",
            "milkCollected",
            "nimbleStance",
            "outposts",
            "recovery",
            "schema",
            "skills",
            "townVisits",
            "weaponKills",
            "weight",
            "zombieKillTypes",
        }
        self.assertEqual(set(decoded.projection), expected_contract_sections)

    def test_decodes_and_verifies_format_three_export(self):
        decoded = decode_run_export(make_export())
        self.assertEqual(decoded.run_id, "rr-web-test")
        self.assertEqual(decoded.current_kills, 42)
        self.assertEqual(decoded.event_sequence, 2)
        self.assertEqual(decoded.character_name, "Test Survivor")
        self.assertEqual(decoded.projection["schema"], 1)
        self.assertEqual(
            decoded.projection["character"]["selectedStartingTraits"],
            ["base:Strong"],
        )
        self.assertEqual(
            decoded.projection["character"]["startingLocation"]["x"],
            10835,
        )
        self.assertEqual(
            decoded.projection["character"]["chosenStartingRegion"],
            {
                "schema": 1,
                "selectionMode": "explicit",
                "resolvedRegionId": "Muldraugh, KY",
                "capturedUtc": 1784800000,
            },
        )
        self.assertEqual(
            decoded.generated_at,
            datetime.fromtimestamp(1784800100, tz=timezone.utc),
        )

    def test_rejects_malformed_starting_location(self):
        projection = {
            "schema": 1,
            "currentKills": 42,
            "character": {
                "current": {"displayName": "Test Survivor"},
                "startingLocation": {
                    "x": "10835",
                    "y": 10144,
                    "z": 0,
                    "buildingId": "",
                    "capturedUtc": 1784800000,
                    "worldAgeHours": 0,
                    "partial": False,
                },
            },
        }
        with self.assertRaisesRegex(InvalidRunExport, "starting-location"):
            decode_run_export(make_export(projection=projection))

    def test_accepts_registered_starting_location(self):
        export = make_export()
        decoded = decode_run_export(export)
        location = decoded.projection["character"]["startingLocation"]
        location["registeredLocation"] = {
            "kind": "landmark",
            "id": "star_eplex_cinema",
            "registryVersion": 1,
        }
        decoded = decode_run_export(make_export(projection=decoded.projection))
        self.assertEqual(
            decoded.projection["character"]["startingLocation"][
                "registeredLocation"
            ]["id"],
            "star_eplex_cinema",
        )

    def test_accepts_omitted_false_partial_flags(self):
        decoded = decode_run_export(make_export())
        character = decoded.projection["character"]
        character["startingLocation"].pop("partial")
        character.pop("selectedStartingTraitsPartial")

        decoded = decode_run_export(make_export(projection=decoded.projection))

        self.assertFalse(
            decoded.projection["character"]["startingLocation"].get(
                "partial", False
            )
        )

    def test_accepts_random_chosen_starting_region(self):
        decoded = decode_run_export(make_export())
        decoded.projection["character"]["chosenStartingRegion"] = {
            "schema": 1,
            "selectionMode": "random",
            "resolvedRegionId": "Rosewood, KY",
            "capturedUtc": 1784800000,
        }

        decoded = decode_run_export(make_export(projection=decoded.projection))

        self.assertEqual(
            decoded.projection["character"]["chosenStartingRegion"][
                "selectionMode"
            ],
            "random",
        )

    def test_rejects_malformed_chosen_starting_region(self):
        decoded = decode_run_export(make_export())
        decoded.projection["character"]["chosenStartingRegion"] = {
            "schema": 1,
            "selectionMode": "random",
            "resolvedRegionId": "",
            "capturedUtc": 1784800000,
        }

        with self.assertRaisesRegex(InvalidRunExport, "chosen-region"):
            decode_run_export(make_export(projection=decoded.projection))

    def test_accepts_current_event_schema_two(self):
        decoded = decode_run_export(make_export(event_schema=2))

        self.assertEqual([event["schema"] for event in decoded.events], [2, 2])

    def test_rejects_legacy_event_schema_one(self):
        with self.assertRaisesRegex(InvalidRunExport, "unsupported event record"):
            decode_run_export(make_export(event_schema=1))

    def test_rejects_unknown_event_schema(self):
        with self.assertRaisesRegex(InvalidRunExport, "unsupported event record"):
            decode_run_export(make_export(event_schema=3))

    def test_rejects_invalid_event_epoch(self):
        with self.assertRaisesRegex(InvalidRunExport, "invalid event metadata"):
            decode_run_export(make_export(event_options={"epoch": 0}))

    def test_rejects_negative_event_timestamp(self):
        with self.assertRaisesRegex(InvalidRunExport, "invalid event metadata"):
            decode_run_export(make_export(event_options={"utc": -1}))

    def test_rejects_non_finite_event_world_age(self):
        with self.assertRaisesRegex(InvalidRunExport, "invalid event metadata"):
            decode_run_export(make_export(event_options={"world_age_hours": "1e999"}))

    def test_rejects_noncanonical_number(self):
        projection = tagged(
            "m",
            tagged("k", "schema")
            + tagged("n", "01")
            + tagged("k", "currentKills")
            + tagged("n", 42)
            + tagged("k", "character")
            + canonical_value({}),
        )
        bodies = [event_body("rr-web-test", 1, "session.started", {})]

        with self.assertRaisesRegex(InvalidRunExport, "invalid number"):
            decode_run_export(
                make_export_from_bodies(bodies, projection_bytes=projection)
            )

    def test_rejects_duplicate_map_key(self):
        projection = tagged(
            "m",
            tagged("k", "schema")
            + tagged("n", 1)
            + tagged("k", "schema")
            + tagged("n", 1),
        )
        bodies = [event_body("rr-web-test", 1, "session.started", {})]

        with self.assertRaisesRegex(InvalidRunExport, "duplicate map key"):
            decode_run_export(
                make_export_from_bodies(bodies, projection_bytes=projection)
            )

    def test_rejects_run_id_that_cannot_be_stored(self):
        with self.assertRaisesRegex(InvalidRunExport, "header contains invalid"):
            decode_run_export(make_export(run_id="r" * 161))

    def test_decodes_optional_raw_challenge_evidence(self):
        decoded = decode_run_export(
            make_export(
                challenge={
                    "id": "TGSRR_CDDA",
                    "gameMode": "The Great Spiffo's Rat Race - CDDA",
                }
            )
        )

        self.assertEqual(decoded.challenge_id, "TGSRR_CDDA")
        self.assertEqual(
            decoded.challenge_game_mode,
            "The Great Spiffo's Rat Race - CDDA",
        )

    def test_rejects_malformed_challenge_evidence(self):
        with self.assertRaisesRegex(InvalidRunExport, "invalid challenge evidence"):
            decode_run_export(make_export(challenge={"id": "TGSRR_CDDA"}))

    def test_rejects_changed_export(self):
        value = make_export()
        changed = value[:-1] + ("0" if value[-1] != "0" else "1")
        with self.assertRaises(InvalidRunExport):
            decode_run_export(changed)

    def test_rejects_unsupported_projection(self):
        with self.assertRaisesRegex(InvalidRunExport, "unsupported run projection"):
            decode_run_export(
                make_export(
                    projection={
                        "schema": 3,
                        "currentKills": 42,
                        "character": {},
                    }
                )
            )


class RunSubmissionTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create_user(
            email="runner@example.com",
            nickname="Runner",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(self.participant)

    def test_verified_export_creates_run_submission_and_notification(self):
        response = self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        self.assertRedirects(response, reverse("registry:account"))
        run = ChallengeRun.objects.get()
        submission = RunSubmission.objects.get()
        self.assertEqual(run.participant, self.participant)
        self.assertEqual(run.character_name, "Test Survivor")
        self.assertEqual(run.current_kills, 42)
        self.assertEqual(run.latest_projection["schema"], 1)
        self.assertEqual(submission.run, run)
        self.assertEqual(submission.projection, run.latest_projection)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.participant, title="Submission received"
            ).exists()
        )
        dashboard = self.client.get(reverse("registry:account"))
        self.assertContains(dashboard, "Test Survivor")
        self.assertContains(dashboard, "1 update")

    def test_format_four_submission_retains_verified_block_references(self):
        run_id = "rr-submission-block-cache-test"
        bodies = [
            event_body(run_id, 1, "session.started", {"character": {}}),
            event_body(run_id, 2, "day.started", {"partial": False}),
            event_body(run_id, 3, "day.started", {"partial": False}),
        ]
        value = make_block_export_from_bodies(
            bodies,
            run_id=run_id,
            projection={"schema": 1, "currentKills": 0, "character": {}},
        )

        response = self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": value}
        )

        self.assertRedirects(response, reverse("registry:account"))
        submission = RunSubmission.objects.get()
        self.assertEqual(submission.event_blocks.count(), 2)
        self.assertEqual(VerifiedRunEventBlock.objects.count(), 2)

    def test_submission_offers_file_upload_and_text_fallback(self):
        response = self.client.get(reverse("registry:submit_run"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose export file")
        self.assertContains(response, 'data-export-dropzone')
        self.assertContains(response, 'accept=".txt,text/plain"')
        self.assertContains(response, "Paste export text instead")
        self.assertContains(response, 'id="id_run_export"')
        self.assertContains(response, "Open file chooser")
        self.assertContains(response, 'data-export-path-choose')

    def test_submission_presents_visual_video_and_clip_pickers(self):
        account = StreamingAccount.objects.create(
            participant=self.participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="visual-runner",
            channel_identity="visual-runner",
            display_name="Visual Runner",
            channel_url="https://www.twitch.tv/visual-runner",
        )
        StreamingMedia.objects.create(
            account=account,
            kind=StreamingMedia.Kind.VIDEO,
            provider_media_id="video-visual",
            title="Full Rat Race broadcast",
            canonical_url="https://www.twitch.tv/videos/visual",
            thumbnail_url="https://example.test/video.jpg",
            published_at=datetime.now(tz=timezone.utc),
            duration_seconds=3723,
        )
        StreamingMedia.objects.create(
            account=account,
            kind=StreamingMedia.Kind.CLIP,
            provider_media_id="clip-visual",
            title="Close escape",
            canonical_url="https://clips.twitch.tv/visual",
            thumbnail_url="https://example.test/clip.jpg",
            published_at=datetime.now(tz=timezone.utc),
            duration_seconds=28,
        )

        response = self.client.get(reverse("registry:submit_run"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-video-picker')
        self.assertContains(response, "Full Rat Race broadcast")
        self.assertContains(response, "https://example.test/video.jpg")
        self.assertContains(response, 'data-clips-open')
        self.assertContains(response, 'data-clips-dialog')
        self.assertContains(response, "Close escape")
        self.assertContains(response, "https://example.test/clip.jpg")

    def test_submission_maps_known_challenge_mode_and_preserves_raw_evidence(self):
        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    challenge={
                        "id": "TGSRR_CDDA",
                        "gameMode": "The Great Spiffo's Rat Race - CDDA",
                    }
                )
            },
        )

        self.assertRedirects(response, reverse("registry:account"))
        mode = ChallengeMode.objects.get(key="TGSRR_CDDA")
        submission = RunSubmission.objects.get()
        run = ChallengeRun.objects.get()
        self.assertEqual(submission.challenge_mode, mode)
        self.assertEqual(submission.challenge_id, "TGSRR_CDDA")
        self.assertEqual(
            submission.challenge_game_mode,
            "The Great Spiffo's Rat Race - CDDA",
        )
        self.assertEqual(run.challenge_mode, mode)
        self.assertEqual(run.challenge_id, "TGSRR_CDDA")
        self.assertEqual(run.starting_challenge_mode, mode)
        self.assertEqual(run.starting_challenge_id, "TGSRR_CDDA")
        self.assertContains(
            self.client.get(reverse("registry:account")),
            "TGSRR - CDDA",
        )

    def test_unknown_challenge_mode_is_preserved_without_rejecting_submission(self):
        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    challenge={
                        "id": "TGSRR_FutureMode",
                        "gameMode": "The Great Spiffo's Rat Race - Future Mode",
                    }
                )
            },
        )

        self.assertRedirects(response, reverse("registry:account"))
        submission = RunSubmission.objects.get()
        self.assertIsNone(submission.challenge_mode)
        self.assertEqual(submission.challenge_id, "TGSRR_FutureMode")
        self.assertEqual(
            submission.challenge_mode_display,
            "TGSRR_FutureMode (Unmapped)",
        )

    def test_empty_challenge_id_maps_by_exact_game_mode_name(self):
        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    challenge={
                        "id": "",
                        "gameMode": "The Great Spiffo's Rat Race",
                    }
                )
            },
        )

        self.assertRedirects(response, reverse("registry:account"))
        submission = RunSubmission.objects.get()
        self.assertEqual(submission.challenge_id, "")
        self.assertEqual(submission.challenge_mode.key, "TGSRR")
        self.assertEqual(submission.challenge_mode_display, "TGSRR")

    def test_submission_snapshots_selected_stream_evidence(self):
        account = StreamingAccount.objects.create(
            participant=self.participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-runner",
            channel_identity="twitch-runner",
            display_name="runner",
            channel_url="https://www.twitch.tv/runner",
        )
        broadcast = StreamingMedia.objects.create(
            account=account,
            kind=StreamingMedia.Kind.VIDEO,
            provider_media_id="video-42",
            title="The whole run",
            canonical_url="https://www.twitch.tv/videos/42",
            published_at=datetime.now(tz=timezone.utc),
        )
        clip = StreamingMedia.objects.create(
            account=account,
            kind=StreamingMedia.Kind.CLIP,
            provider_media_id="clip-42",
            parent_media_id="video-42",
            title="Final escape",
            canonical_url="https://clips.twitch.tv/final-escape",
            published_at=datetime.now(tz=timezone.utc),
            vod_offset_seconds=123,
        )

        response = self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(),
                "evidence_provider": StreamingAccount.Provider.TWITCH,
                "evidence_video": str(broadcast.pk),
                "evidence_start_seconds": 60,
                "evidence_end_seconds": 3600,
                "evidence_clips": [str(clip.pk)],
            },
        )

        self.assertRedirects(response, reverse("registry:account"))
        submission = RunSubmission.objects.get()
        self.assertEqual(submission.evidence_provider, "twitch")
        self.assertEqual(submission.evidence_media_id, "video-42")
        self.assertEqual(submission.evidence_url, broadcast.canonical_url)
        self.assertEqual(submission.evidence_start_seconds, 60)
        self.assertEqual(submission.evidence_end_seconds, 3600)
        self.assertEqual(submission.evidence_clips[0]["media_id"], "clip-42")

    def test_run_lifecycle_separates_active_and_past_runs(self):
        mode = ChallengeMode.objects.get(key="TGSRR")
        mode.max_active_runs_per_participant = 2
        mode.save(update_fields=("max_active_runs_per_participant",))
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="active-run")},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="past-run")},
        )
        active_run = ChallengeRun.objects.get(run_id="active-run")
        active_run.character_name = "Active Survivor"
        active_run.save(update_fields=("character_name",))
        past_run = ChallengeRun.objects.get(run_id="past-run")
        past_run.character_name = "Past Survivor"
        past_run.lifecycle_status = ChallengeRun.Lifecycle.DECEASED
        past_run.save(update_fields=("character_name", "lifecycle_status"))

        dashboard = self.client.get(reverse("registry:account"))

        self.assertContains(dashboard, "Past Runs")
        self.assertContains(dashboard, "Deceased")
        self.assertContains(dashboard, "Active Survivor")
        self.assertContains(dashboard, "Past Survivor")
        self.assertContains(dashboard, 'class="profile-run-card"', count=2)
        self.assertContains(dashboard, 'class="dashboard-run-entry"', count=2)
        self.assertContains(dashboard, "Run details", count=2)
        self.assertContains(dashboard, "Approved submissions", count=2)
        self.assertContains(dashboard, "Submission history", count=2)
        self.assertContains(dashboard, "Awaiting Review")
        self.assertContains(dashboard, "Awaiting review")

    def test_mode_active_run_limit_blocks_a_second_character(self):
        first = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="first-active-run",
                    challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                )
            },
        )
        self.assertRedirects(first, reverse("registry:account"))

        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="second-active-run",
                    challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "maximum of 1 active run")
        self.assertContains(response, "data-submission-blocked-dialog")
        active_run = ChallengeRun.objects.get(run_id="first-active-run")
        self.assertContains(response, "View active run")
        self.assertContains(
            response,
            f'data-run-detail-open="run-detail-{active_run.pk}"',
        )
        self.assertContains(response, f'id="run-detail-{active_run.pk}"')
        self.assertContains(response, 'name="return_to_submission" value="1"')
        self.assertFalse(ChallengeRun.objects.filter(run_id="second-active-run").exists())

    def test_configured_mode_limit_allows_more_than_one_active_run(self):
        mode = ChallengeMode.objects.get(key="TGSRR")
        mode.max_active_runs_per_participant = 2
        mode.save(update_fields=("max_active_runs_per_participant",))

        for run_id in ("first-active-run", "second-active-run"):
            response = self.client.post(
                reverse("registry:submit_run"),
                {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                    "run_export": make_export(
                        run_id=run_id,
                        challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                    )
                },
            )
            self.assertRedirects(response, reverse("registry:account"))

        self.assertEqual(ChallengeRun.objects.count(), 2)

    def test_pending_deceased_run_releases_active_slot_before_approval(self):
        deceased_projection = {
            "schema": 1,
            "currentKills": 42,
            "character": {"current": {"displayName": "Late Survivor"}},
            "lifecycle": "deceased",
            "endedReason": "deceased",
            "endedUtc": 1784800003,
            "endedWorldAgeHours": 3,
            "endedEventSequence": 3,
        }
        deceased = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(
                run_id="pending-deceased",
                challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                projection=deceased_projection,
                event_specs=[
                    ("session.started", {"character": {"displayName": "Late Survivor"}}),
                    ("day.started", {"partial": False}),
                    ("run.ended", {"reason": "deceased"}),
                ],
            )},
        )
        self.assertRedirects(deceased, reverse("registry:account"))

        active = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(
                run_id="new-active",
                challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
            )},
        )

        self.assertRedirects(active, reverse("registry:account"))
        self.assertEqual(ChallengeRun.objects.count(), 2)
        pending = ChallengeRun.objects.get(run_id="pending-deceased")
        self.assertEqual(pending.lifecycle_status, ChallengeRun.Lifecycle.ACTIVE)
        self.assertEqual(pending.reported_lifecycle_status, ChallengeRun.Lifecycle.DECEASED)

    def test_participant_pending_deceased_override_limits_new_terminal_runs(self):
        mode = ChallengeMode.objects.get(key="TGSRR")
        ParticipantChallengeModeLimit.objects.create(
            participant=self.participant,
            challenge_mode=mode,
            max_pending_deceased_runs=0,
            reason="Temporary moderation restriction.",
        )
        projection = {
            "schema": 1, "currentKills": 1,
            "character": {"current": {"displayName": "Ended"}},
            "lifecycle": "deceased", "endedReason": "deceased",
            "endedUtc": 1784800003, "endedWorldAgeHours": 3,
            "endedEventSequence": 3,
        }

        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(
                run_id="restricted-deceased", projection=projection,
                challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                event_specs=[
                    ("session.started", {"character": {"displayName": "Ended"}}),
                    ("day.started", {"partial": False}),
                    ("run.ended", {"reason": "deceased"}),
                ],
            )},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "maximum of 0 pending deceased runs")
        self.assertFalse(ChallengeRun.objects.filter(run_id="restricted-deceased").exists())

    def test_active_approval_waits_for_earlier_pending_terminal_submission(self):
        projection = {
            "schema": 1, "currentKills": 1,
            "character": {"current": {"displayName": "Ended"}},
            "lifecycle": "deceased", "endedReason": "deceased",
            "endedUtc": 1784800003, "endedWorldAgeHours": 3,
            "endedEventSequence": 3,
        }
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(
                run_id="earlier-terminal", projection=projection,
                challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
                event_specs=[
                    ("session.started", {"character": {"displayName": "Ended"}}),
                    ("day.started", {"partial": False}),
                    ("run.ended", {"reason": "deceased"}),
                ],
            ), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(
                run_id="later-active",
                challenge={"id": "TGSRR", "gameMode": "The Great Spiffo's Rat Race"},
            ), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        active_submission = RunSubmission.objects.get(run__run_id="later-active")
        administrator = Participant.objects.create_superuser(
            email="ordering-reviewer@example.com",
            nickname="Ordering Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(active_submission.pk,))
        )

        self.assertRedirects(
            response,
            reverse("admin:registry_runsubmission_change", args=(active_submission.pk,)),
        )
        active_submission.refresh_from_db()
        self.assertEqual(active_submission.status, RunSubmission.Status.RECEIVED)

    def test_participant_can_irreversibly_deactivate_active_run(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="run-to-deactivate")},
        )
        run = ChallengeRun.objects.get(run_id="run-to-deactivate")

        response = self.client.post(
            reverse("registry:deactivate_run", args=(run.pk,)),
            {"confirm_deactivation": "deactivate"},
        )

        self.assertRedirects(response, reverse("registry:account"))
        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.ABANDONED)
        self.assertIsNotNone(run.participant_deactivated_at)
        submission = run.submissions.get()
        self.assertEqual(submission.status, RunSubmission.Status.DECLINED)
        self.assertEqual(submission.review_note, "Run deactivated by participant.")

        dashboard = self.client.get(reverse("registry:account"))
        self.assertContains(dashboard, "Abandoned")
        self.assertNotContains(dashboard, "Deactivate permanently")

    def test_deactivation_from_submission_block_returns_to_submission_form(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="blocked-active-run")},
        )
        run = ChallengeRun.objects.get(run_id="blocked-active-run")

        response = self.client.post(
            reverse("registry:deactivate_run", args=(run.pk,)),
            {
                "confirm_deactivation": "deactivate",
                "return_to_submission": "1",
            },
        )

        self.assertRedirects(response, reverse("registry:submit_run"))
        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.ABANDONED)

    def test_deactivation_from_submission_block_supports_in_page_response(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="ajax-active-run")},
        )
        run = ChallengeRun.objects.get(run_id="ajax-active-run")

        response = self.client.post(
            reverse("registry:deactivate_run", args=(run.pk,)),
            {
                "confirm_deactivation": "deactivate",
                "return_to_submission": "1",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "message": "The active run was deactivated. You can now submit this character.",
            },
        )
        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.ABANDONED)

    def test_deactivated_run_rejects_later_updates_and_frees_mode_slot(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="retired-run",
                    challenge={
                        "id": "TGSRR",
                        "gameMode": "The Great Spiffo's Rat Race",
                    },
                )
            },
        )
        run = ChallengeRun.objects.get(run_id="retired-run")
        self.client.post(
            reverse("registry:deactivate_run", args=(run.pk,)),
            {"confirm_deactivation": "deactivate"},
        )

        blocked = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="retired-run",
                    kills=50,
                    generated_at=1784800200,
                    challenge={
                        "id": "TGSRR",
                        "gameMode": "The Great Spiffo's Rat Race",
                    },
                )
            },
        )
        self.assertEqual(blocked.status_code, 200)
        self.assertContains(blocked, "was deactivated")

        replacement = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="replacement-run",
                    challenge={
                        "id": "TGSRR",
                        "gameMode": "The Great Spiffo's Rat Race",
                    },
                )
            },
        )
        self.assertRedirects(replacement, reverse("registry:account"))
        self.assertTrue(ChallengeRun.objects.filter(run_id="replacement-run").exists())

    def test_duplicate_export_is_rejected(self):
        value = make_export()
        self.client.post(reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": value})
        response = self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": value}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already been submitted")
        self.assertEqual(RunSubmission.objects.count(), 1)

    def test_participant_can_add_evidence_without_replacing_locked_export(self):
        value = make_export(run_id="evidence-correction-run")
        self.client.post(reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": value})
        submission = RunSubmission.objects.get()
        original_checksum = submission.checksum
        original_export = submission.raw_export
        self.assertEqual(submission.evidence_revisions.count(), 1)

        update_url = reverse(
            "registry:update_run_submission_evidence", args=(submission.pk,)
        )
        page = self.client.get(update_url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Locked tracker export")
        self.assertNotContains(page, submission.checksum)
        response = self.client.post(
            update_url,
            {"manual_evidence_url": "https://www.twitch.tv/videos/234567"},
        )

        self.assertRedirects(response, reverse("registry:account"))
        submission.refresh_from_db()
        self.assertEqual(submission.checksum, original_checksum)
        self.assertEqual(submission.raw_export, original_export)
        self.assertEqual(
            submission.evidence_url, "https://www.twitch.tv/videos/234567"
        )
        self.assertEqual(submission.status, RunSubmission.Status.RECEIVED)
        self.assertEqual(submission.evidence_revisions.count(), 2)
        self.assertEqual(
            submission.preapproval_state, RunSubmission.PreapprovalState.GREEN
        )
        submission.status = RunSubmission.Status.APPROVED
        submission.save(update_fields=("status",))
        self.assertEqual(self.client.get(update_url).status_code, 404)

    def test_request_evidence_notifies_participant_and_blocks_later_review(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="awaiting-evidence-run")},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="awaiting-evidence-run",
                    generated_at=1784800200,
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Test Survivor"}}),
                        ("day.started", {"partial": False}),
                        ("day.started", {"partial": False}),
                    ],
                )
            },
        )
        first, second = RunSubmission.objects.order_by("submitted_at", "pk")
        administrator = Participant.objects.create_superuser(
            email="evidence-reviewer@example.com",
            nickname="Evidence Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        reason = "Please add the complete broadcast URL."
        response = self.client.post(
            reverse(
                "admin:registry_runsubmission_request_evidence", args=(first.pk,)
            ),
            {"reason": reason},
        )
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        self.assertEqual(first.status, RunSubmission.Status.AWAITING_EVIDENCE)
        self.assertEqual(first.evidence_request_note, reason)
        notification = Notification.objects.get(title="More evidence needed")
        self.assertEqual(
            notification.destination,
            reverse("registry:update_run_submission_evidence", args=(first.pk,)),
        )

        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(second.pk,))
        )
        second.refresh_from_db()
        self.assertEqual(second.status, RunSubmission.Status.RECEIVED)

        self.client.force_login(self.participant)
        response = self.client.post(
            notification.destination,
            {"manual_evidence_url": "https://www.twitch.tv/videos/345678"},
        )
        self.assertRedirects(response, reverse("registry:account"))
        first.refresh_from_db()
        self.assertEqual(first.status, RunSubmission.Status.RECEIVED)

    def test_export_older_than_newest_pending_snapshot_is_rejected(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="pending-order-run",
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Test Survivor"}}),
                        ("day.started", {"partial": False}),
                        ("day.started", {"partial": False}),
                    ],
                )
            },
        )
        response = self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="pending-order-run",
                    generated_at=1784800200,
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "older than the latest version")
        self.assertEqual(RunSubmission.objects.count(), 1)

    def test_admin_overview_marks_missing_vod_or_url_orange_and_skips_bulk_approval(self):
        self.client.post(reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()})
        submission = RunSubmission.objects.get()
        # A historical submission can predate the evidence requirement.
        submission.evidence_url = ""
        submission.save(update_fields=["evidence_url"])
        submission.preapproval_assessed_at = None
        capture_preapproval_assessment(submission)
        administrator = Participant.objects.create_superuser(
            email="orange-reviewer@example.com",
            nickname="Orange Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        overview = self.client.get(reverse("admin:registry_runsubmission_changelist"), follow=True)
        self.assertContains(overview, "Pending first approval")
        self.assertContains(overview, "No URL or VOD provided")
        self.assertEqual(
            submission.preapproval_state, RunSubmission.PreapprovalState.ORANGE
        )
        self.assertIsNotNone(submission.preapproval_assessed_at)
        review = build_run_review(submission)
        self.assertEqual(review["severity"], "warning")
        self.assertTrue(
            any(finding["title"] == "No URL or VOD provided" for finding in review["findings"])
        )
        assessed_at = submission.preapproval_assessed_at
        submission.evidence_url = "https://example.com/vod/added-too-late"
        submission.save(update_fields=("evidence_url",))
        capture_preapproval_assessment(submission)
        submission.refresh_from_db()
        self.assertEqual(
            submission.preapproval_state, RunSubmission.PreapprovalState.ORANGE
        )
        self.assertEqual(submission.preapproval_assessed_at, assessed_at)

        run_queue = reverse(
            "admin:registry_runsubmission_run_queue", args=(submission.run_id,)
        )
        self.client.post(run_queue, {ACTION_CHECKBOX_NAME: [str(submission.pk)]})
        submission.refresh_from_db()
        self.assertEqual(submission.status, RunSubmission.Status.RECEIVED)

    def test_admin_overview_marks_legacy_invalid_export_red_and_skips_it(self):
        self.client.post(reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()})
        submission = RunSubmission.objects.get()
        submission.preapproval_state = RunSubmission.PreapprovalState.RED
        submission.preapproval_findings = [
            {
                "level": "danger",
                "title": "Invalid export",
                "message": "The export contains invalid outpost lifecycle summaries.",
            }
        ]
        submission.save(update_fields=("preapproval_state", "preapproval_findings"))
        administrator = Participant.objects.create_superuser(
            email="invalid-export-reviewer@example.com",
            nickname="Invalid Export Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        with patch(
            "registry.admin.build_run_review",
            side_effect=AssertionError("The overview must use the stored assessment."),
        ):
            overview = self.client.get(reverse("admin:registry_runsubmission_changelist"), follow=True)
            self.assertEqual(overview.status_code, 200)
            self.assertContains(overview, "Invalid export")
            run_queue = reverse(
                "admin:registry_runsubmission_run_queue", args=(submission.run_id,)
            )
            self.client.post(run_queue, {ACTION_CHECKBOX_NAME: [str(submission.pk)]})

        submission.refresh_from_db()
        self.assertEqual(submission.status, RunSubmission.Status.RECEIVED)

    def test_admin_run_queue_approves_green_submission_and_returns_to_grouped_queue(self):
        self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(),
                "manual_evidence_url": "https://www.twitch.tv/videos/123456",
            },
        )
        submission = RunSubmission.objects.get()
        self.assertEqual(
            submission.preapproval_state, RunSubmission.PreapprovalState.GREEN
        )
        administrator = Participant.objects.create_superuser(
            email="green-reviewer@example.com",
            nickname="Green Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        overview = self.client.get(reverse("admin:registry_runsubmission_changelist"), follow=True)
        self.assertContains(overview, "Verification")
        self.assertContains(overview, 'data-submission-count="1"')
        self.assertContains(overview, "Review required")
        self.assertContains(overview, "Pending first approval")
        run_queue_url = reverse(
            "admin:registry_runsubmission_run_queue", args=(submission.run_id,)
        )
        run_queue = self.client.get(run_queue_url)
        self.assertContains(run_queue, "Next to review")
        self.assertNotContains(run_queue, "Approve selected clean sequence")
        review_page = self.client.get(
            reverse("admin:registry_runsubmission_change", args=(submission.pk,))
            + "?return_to_run=1"
        )
        self.assertContains(review_page, f'data-admin-return-url="{run_queue_url}"')

        response = self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(submission.pk,)) + "?return_to_run=1"
        )
        self.assertRedirects(response, run_queue_url)
        submission.refresh_from_db()
        self.assertEqual(submission.status, RunSubmission.Status.APPROVED)
        overview = self.client.get(reverse("admin:registry_runsubmission_changelist"), follow=True)
        self.assertNotContains(overview, submission.run.character_name)

    def test_run_queue_groups_updates_and_enforces_chronological_review(self):
        evidence = "https://www.twitch.tv/videos/123456"
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(run_id="ordered-run"), "manual_evidence_url": evidence},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(
                    run_id="ordered-run",
                    generated_at=1784800200,
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Test Survivor"}}),
                        ("day.started", {"partial": False}),
                        ("day.started", {"partial": False}),
                    ],
                ),
                "manual_evidence_url": evidence,
            },
        )
        submissions = list(RunSubmission.objects.order_by("submitted_at", "pk"))
        self.assertEqual(len(submissions), 2)
        administrator = Participant.objects.create_superuser(
            email="ordered-reviewer@example.com",
            nickname="Ordered Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        overview = self.client.get(reverse("admin:registry_runsubmission_changelist"), follow=True)
        self.assertContains(overview, 'data-submission-count="2"')
        self.assertContains(overview, "run_tab=submissions")

        run_queue_url = reverse(
            "admin:registry_runsubmission_run_queue", args=(submissions[0].run_id,)
        )
        run_queue = self.client.get(run_queue_url)
        self.assertContains(run_queue, "Next to review", count=1)
        self.assertContains(run_queue, "Waiting for earlier review", count=1)

        later_approve_url = reverse(
            "admin:registry_runsubmission_approve", args=(submissions[1].pk,)
        ) + "?return_to_run=1"
        response = self.client.post(later_approve_url)
        self.assertRedirects(response, reverse("admin:registry_runsubmission_change", args=(submissions[1].pk,)) + "?return_to_run=1", fetch_redirect_response=False)
        submissions[1].refresh_from_db()
        self.assertEqual(submissions[1].status, RunSubmission.Status.RECEIVED)

        response = self.client.post(
            run_queue_url,
            {ACTION_CHECKBOX_NAME: [str(item.pk) for item in submissions]},
        )
        self.assertEqual(response.status_code, 405)
        for submission in submissions:
            submission.refresh_from_db()
            self.assertEqual(submission.status, RunSubmission.Status.RECEIVED)

    def test_dashboard_groups_pending_updates_by_run(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export(run_id="grouped-dashboard-run")},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {"manual_evidence_url": "https://www.twitch.tv/videos/123456",
                "run_export": make_export(
                    run_id="grouped-dashboard-run",
                    generated_at=1784800200,
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Test Survivor"}}),
                        ("day.started", {"partial": False}),
                        ("day.started", {"partial": False}),
                    ],
                )
            },
        )

        dashboard = self.client.get(reverse("registry:account"))

        self.assertContains(dashboard, "2 updates")
        self.assertContains(dashboard, 'class="dashboard-run-entry"', count=1)

    def test_admin_approval_updates_submission_and_dashboard(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export(), "manual_evidence_url": "https://www.twitch.tv/videos/123456"}
        )
        run = ChallengeRun.objects.get()
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        response = self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(submission.pk,))
        )
        self.assertRedirects(
            response,
            reverse("admin:registry_runsubmission_change", args=(submission.pk,)),
        )
        run.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(run.status, ChallengeRun.Status.OFFICIAL)
        self.assertEqual(run.approved_submission, submission)
        self.assertEqual(submission.status, RunSubmission.Status.APPROVED)
        self.assertIsNotNone(submission.reviewed_at)
        self.assertEqual(run.contract_state.projection_schema, 1)
        self.assertEqual(
            run.character_record.starting_display_name, "Starting Survivor"
        )
        self.assertEqual(run.character_record.current_display_name, "Test Survivor")
        self.assertEqual(run.character_record.traits.count(), 3)
        self.assertEqual(
            set(run.character_record.traits.values_list("phase", flat=True)),
            {
                RunCharacterTrait.Phase.SELECTED_STARTING,
                RunCharacterTrait.Phase.SPAWNED_STARTING,
                RunCharacterTrait.Phase.CURRENT,
            },
        )
        self.assertEqual(
            run.starting_location.selection_mode,
            RunStartingLocation.SelectionMode.EXPLICIT,
        )
        self.assertEqual(
            run.starting_location.resolved_region_raw_id, "Muldraugh, KY"
        )
        self.assertEqual(
            (run.starting_location.x, run.starting_location.y, run.starting_location.z),
            (10835, 10144, 0),
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.participant, title="Submission approved"
            ).exists()
        )
        self.client.force_login(self.participant)
        dashboard = self.client.get(reverse("registry:account"))
        self.assertContains(dashboard, "Verified")
        self.assertContains(dashboard, "Test Survivor")
        self.assertContains(dashboard, "In-game Day")
        self.assertContains(dashboard, "Day 1", count=2)
        self.assertNotContains(dashboard, "Events verified")

    def test_approval_lock_targets_only_submission_with_no_approved_baseline(self):
        from .admin import locked_run_submission_queryset

        self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        self.assertIsNone(run.approved_submission)

        query = locked_run_submission_queryset().filter(
            pk=RunSubmission.objects.get().pk
        ).query

        self.assertTrue(query.select_for_update)
        self.assertEqual(query.select_for_update_of, ("self",))

    def test_approval_uses_approved_cursor_for_exact_format_four_successor(self):
        run_id = "rr-incremental-approval-test"
        projection = {"schema": 1, "currentKills": 0, "character": {}}
        first_bodies = [
            event_body(run_id, 1, "session.started", {"character": {}}),
            event_body(run_id, 2, "day.started", {"partial": False}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_block_export_from_bodies(
                first_bodies, run_id=run_id, projection=projection
            ), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        administrator = Participant.objects.create_superuser(
            email="incremental-reviewer@example.com",
            nickname="Incremental Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        first = RunSubmission.objects.get()
        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(first.pk,))
        )

        self.client.force_login(self.participant)
        extended_bodies = first_bodies + [
            event_body(run_id, 3, "day.started", {"partial": False})
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_block_export_from_bodies(
                extended_bodies,
                run_id=run_id,
                generated_at=1784800200,
                projection=projection,
            ), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        successor = RunSubmission.objects.get(status=RunSubmission.Status.RECEIVED)
        self.client.force_login(administrator)
        with patch(
            "registry.submission_approval.refresh_initial_run_authority",
            wraps=refresh_initial_run_authority,
        ) as refresh:
            self.client.post(
                reverse(
                    "admin:registry_runsubmission_approve", args=(successor.pk,)
                )
            )

        self.assertEqual(refresh.call_args.kwargs["previous_event_sequence"], 2)

    def test_admin_approval_rolls_back_if_authority_refresh_fails(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export(), "manual_evidence_url": "https://www.twitch.tv/videos/123456"}
        )
        run = ChallengeRun.objects.get()
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="rollback-reviewer@example.com",
            nickname="Rollback Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        with patch(
            "registry.submission_approval.refresh_initial_run_authority",
            side_effect=RuntimeError("authority refresh failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "authority refresh failed"):
                self.client.post(
                    reverse(
                        "admin:registry_runsubmission_approve",
                        args=(submission.pk,),
                    )
                )

        run.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(run.status, ChallengeRun.Status.PENDING)
        self.assertIsNone(run.approved_submission)
        self.assertEqual(submission.status, RunSubmission.Status.RECEIVED)
        self.assertIsNone(submission.reviewed_at)
        self.assertFalse(hasattr(run, "contract_state"))
        self.assertFalse(hasattr(run, "character_record"))
        self.assertFalse(hasattr(run, "starting_location"))
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.participant,
                title="Submission approved",
            ).exists()
        )

    def test_schema_two_approval_rebuilds_authoritative_outpost_records(self):
        observed_outpost = next(
            outpost
            for outpost in outpost_lifecycle_projection()
            if outpost["id"] == "rosewood"
        )
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": [observed_outpost],
        }
        response = self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(projection=projection), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        self.assertEqual(response.status_code, 302, response.content.decode())
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="outpost-reviewer@example.com",
            nickname="Outpost Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(submission.pk,))
        )

        self.assertEqual(RunOutpost.objects.count(), 1)
        self.assertEqual(RunOutpostDeliverable.objects.count(), 13)
        rosewood = RunOutpost.objects.get(raw_outpost_id="rosewood")
        self.assertIsNotNone(rosewood.catalogue_entry)
        self.assertEqual(rosewood.current_state, "incomplete")
        self.assertEqual(rosewood.deliverables.count(), 13)

    def test_approval_rebuilds_sparse_skill_and_kill_authority(self):
        projection = {
            "schema": 2,
            "currentKills": 42,
            "character": {"current": {"displayName": "Test Survivor"}},
            "outposts": [],
            "skills": [
                {"id": "Aiming", "categoryId": "Firearm", "level": 2, "xp": 88.5},
                {"id": "Cooking", "categoryId": "Crafting", "level": 0, "xp": 0},
            ],
            "weaponKills": {
                "partial": True,
                "baselineTotal": 4,
                "sources": [
                    {"id": "Base.Axe", "kills": 11},
                    {"id": "Base.BareHands", "kills": 0},
                ],
            },
            "fireDeaths": {"count": 3},
            "zombieKillTypes": {"standing": 9, "onfront": 2},
        }
        response = self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(projection=projection), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        self.assertEqual(response.status_code, 302, response.content.decode())
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="advanced-authority-reviewer@example.com",
            nickname="Advanced Authority Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(submission.pk,))
        )

        skill = RunSkill.objects.get()
        self.assertEqual(skill.raw_skill_id, "Aiming")
        self.assertEqual(skill.level, 2)
        self.assertEqual(skill.xp, 88.5)
        summary = RunKillSummary.objects.get()
        self.assertEqual(summary.current_kills, 42)
        self.assertTrue(summary.weapon_partial)
        self.assertEqual(summary.weapon_baseline_total, 4)
        self.assertEqual(summary.fire_deaths, 3)
        self.assertEqual(summary.standing, 9)
        self.assertEqual(summary.on_front, 2)
        weapon = RunWeaponKill.objects.get()
        self.assertEqual(weapon.raw_source_id, "Base.Axe")
        self.assertEqual(weapon.kills, 11)

    def test_authority_rebuilds_sealed_and_active_daily_records(self):
        run = ChallengeRun.objects.create(
            run_id="rr-daily-authority-test",
            export_format=3,
            generated_at=datetime.now(timezone.utc),
            event_hash="0" * 64,
        )
        events = [
            {
                "event_type": "day.started",
                "utc": 100,
                "world_age_hours": 0,
                "payload": {
                    "dayIndex": 1,
                    "calendar": {"year": 1993, "month": 7, "day": 9},
                },
            },
            {
                "event_type": "day.started",
                "utc": 200,
                "world_age_hours": 24,
                "payload": {
                    "dayIndex": 2,
                    "calendar": {"year": 1993, "month": 7, "day": 10},
                    "completedDay": {
                        "dayIndex": 1,
                        "startedUtc": 100,
                        "startedWorldAgeHours": 0,
                        "killDelta": 4,
                        "weightDeltaKilograms": -0.25,
                        "animalPetDeltas": {"cow": 2},
                        "fluidConsumedDeltas": {"Water": 1.25},
                        "caloriesConsumedDelta": 450.5,
                        "generatorRepairDelta": 2,
                        "generatorConditionRestoredDelta": 9.5,
                        "nimbleMovementMillisecondsDelta": 12000,
                        "activeGameplayMillisecondsDelta": 60000,
                        "xpDeltas": {"Aiming": 12.5},
                        "animalTrapDeltas": [
                            {
                                "animalType": "rabbit",
                                "trapId": "Base.TrapBox",
                                "trapped": 1,
                            }
                        ],
                    },
                },
            },
        ]
        projection = {
            "schema": 2,
            "character": {},
            "outposts": [],
            "skills": [],
            "activeDay": {
                "dayIndex": 2,
                "startedUtc": 200,
                "startedWorldAgeHours": 24,
                "observedUtc": 220,
                "observedWorldAgeHours": 26,
                "elapsedWorldHours": 2,
                "distanceDeltaMeters": 125.5,
                "caloriesConsumedDelta": 25.0,
                "generatorRepairDelta": 1,
                "generatorConditionRestoredDelta": 4.0,
                "nimbleMovementMillisecondsDelta": 3000,
                "activeGameplayMillisecondsDelta": 15000,
                "brokenWeaponDeltas": {"Base.Axe": 1},
                "animalPetDeltas": {"cow": 1},
                "fluidConsumedDeltas": {"Water": 0.5},
                "distancePartial": True,
            },
        }

        refresh_initial_run_authority(run, projection, events)

        sealed = RunDailyRecord.objects.get(state=RunDailyRecord.State.SEALED)
        self.assertEqual(sealed.day_index, 1)
        self.assertEqual(sealed.calendar_day, 9)
        self.assertEqual(sealed.observed_utc, 200)
        self.assertEqual(sealed.kill_delta, 4)
        self.assertEqual(sealed.weight_delta_kilograms, -0.25)
        self.assertEqual(sealed.calories_consumed_delta, 450.5)
        self.assertEqual(sealed.generator_repair_delta, 2)
        self.assertEqual(sealed.generator_condition_restored_delta, 9.5)
        self.assertEqual(sealed.nimble_movement_milliseconds_delta, 12000)
        self.assertEqual(sealed.active_gameplay_milliseconds_delta, 60000)
        self.assertEqual(sealed.metrics.count(), 4)
        self.assertTrue(
            sealed.metrics.filter(
                kind=RunDailyMetric.Kind.SKILL_XP,
                raw_primary_id="Aiming",
                value=12.5,
            ).exists()
        )

        active = RunDailyRecord.objects.get(state=RunDailyRecord.State.ACTIVE)
        self.assertEqual(active.day_index, 2)
        self.assertEqual(active.calendar_day, 10)
        self.assertEqual(active.distance_delta_meters, 125.5)
        self.assertEqual(active.calories_consumed_delta, 25.0)
        self.assertEqual(active.generator_repair_delta, 1)
        self.assertEqual(active.generator_condition_restored_delta, 4.0)
        self.assertEqual(active.nimble_movement_milliseconds_delta, 3000)
        self.assertEqual(active.active_gameplay_milliseconds_delta, 15000)
        self.assertTrue(active.partial)
        self.assertEqual(active.partial_metrics, ["distance"])
        broken = active.metrics.get(kind=RunDailyMetric.Kind.BROKEN_WEAPON)
        self.assertEqual(broken.raw_primary_id, "Base.Axe")
        self.assertEqual(broken.value, 1)
        self.assertTrue(
            active.metrics.filter(
                kind=RunDailyMetric.Kind.ANIMAL_PET,
                raw_primary_id="cow",
                value=1,
            ).exists()
        )
        self.assertTrue(
            active.metrics.filter(
                kind=RunDailyMetric.Kind.FLUID_CONSUMED,
                raw_primary_id="Water",
                value=0.5,
            ).exists()
        )

    def test_authority_normalizes_cumulative_statistics_for_queries(self):
        run = ChallengeRun.objects.create(
            run_id="rr-statistic-authority-test",
            export_format=4,
            generated_at=datetime.now(timezone.utc),
            event_hash="0" * 64,
        )
        projection = {
            "schema": 2,
            "character": {},
            "outposts": [],
            "skills": [],
            "weight": {"currentKilograms": 78.5},
            "distance": {"travelledMeters": 1250.25, "rejectedSamples": 3},
            "nimbleStance": {"movementMilliseconds": 12000},
            "activeGameplay": {"milliseconds": 60000},
            "animalsPetted": {
                "total": 2,
                "animalTypes": [{"animalType": "cow", "pets": 2}],
            },
            "fluidConsumed": {
                "totalLiters": 1.25,
                "fluidTypes": [{"fluidTypeId": "Water", "liters": 1.25}],
            },
            "caloriesConsumed": {"totalKilocalories": 450.5},
            "generatorRepairs": {"count": 2, "conditionRestored": 9.5},
        }

        refresh_initial_run_authority(run, projection, [])

        self.assertTrue(
            RunStatisticSummary.objects.filter(
                run=run,
                kind=RunStatisticSummary.Kind.DISTANCE,
                value__gte=1000,
                secondary_value=3,
                unit="meter",
            ).exists()
        )
        pet_summary = RunStatisticSummary.objects.get(
            run=run, kind=RunStatisticSummary.Kind.ANIMAL_PET
        )
        self.assertEqual(pet_summary.value, 2)
        self.assertTrue(
            RunStatisticMetric.objects.filter(
                summary=pet_summary,
                dimension=RunStatisticMetric.Dimension.ANIMAL,
                raw_primary_id="cow",
                value=2,
            ).exists()
        )
        fluid_summary = RunStatisticSummary.objects.get(
            run=run, kind=RunStatisticSummary.Kind.FLUID_CONSUMED
        )
        self.assertEqual(fluid_summary.value, 1.25)
        self.assertTrue(
            fluid_summary.metrics.filter(
                dimension=RunStatisticMetric.Dimension.FLUID,
                raw_primary_id="Water",
                value=1.25,
            ).exists()
        )
        repairs = RunStatisticSummary.objects.get(
            run=run, kind=RunStatisticSummary.Kind.GENERATOR_REPAIRS
        )
        self.assertEqual(repairs.value, 2)
        self.assertEqual(repairs.secondary_value, 9.5)

    def test_authority_appends_new_daily_records_without_rebuilding_sealed_history(self):
        run = ChallengeRun.objects.create(
            run_id="rr-incremental-daily-authority-test",
            export_format=4,
            generated_at=datetime.now(timezone.utc),
            event_hash="0" * 64,
        )
        first_events = [
            {
                "event_type": "day.started",
                "utc": 100,
                "world_age_hours": 0,
                "payload": {
                    "dayIndex": 1,
                    "calendar": {"year": 1993, "month": 7, "day": 9},
                },
            },
            {
                "event_type": "day.started",
                "utc": 200,
                "world_age_hours": 24,
                "payload": {
                    "dayIndex": 2,
                    "calendar": {"year": 1993, "month": 7, "day": 10},
                    "completedDay": {"dayIndex": 1, "killDelta": 4},
                },
            },
        ]
        projection = {
            "schema": 2,
            "character": {},
            "outposts": [],
            "skills": [],
            "activeDay": {"dayIndex": 2, "killDelta": 1},
        }
        refresh_initial_run_authority(run, projection, first_events)
        original = RunDailyRecord.objects.get(
            run=run, state=RunDailyRecord.State.SEALED, day_index=1
        )

        extended_events = first_events + [{
            "event_type": "day.started",
            "utc": 300,
            "world_age_hours": 48,
            "payload": {
                "dayIndex": 3,
                "calendar": {"year": 1993, "month": 7, "day": 11},
                "completedDay": {"dayIndex": 2, "killDelta": 7},
            },
        }]
        projection["activeDay"] = {"dayIndex": 3, "killDelta": 2}
        refresh_initial_run_authority(
            run,
            projection,
            extended_events,
            previous_event_sequence=len(first_events),
        )

        original.refresh_from_db()
        self.assertEqual(original.kill_delta, 4)
        self.assertEqual(
            RunDailyRecord.objects.get(
                run=run, state=RunDailyRecord.State.SEALED, day_index=2
            ).kill_delta,
            7,
        )
        self.assertEqual(
            RunDailyRecord.objects.get(
                run=run, state=RunDailyRecord.State.ACTIVE
            ).day_index,
            3,
        )

    def test_approval_marks_a_terminal_death_export_as_deceased(self):
        projection = {
            "schema": 1,
            "currentKills": 42,
            "character": {"current": {"displayName": "Late Survivor"}},
            "lifecycle": "deceased",
            "endedReason": "deceased",
            "endedUtc": 1784800003,
            "endedWorldAgeHours": 3,
            "endedEventSequence": 3,
        }
        self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(
                    projection=projection,
                    event_specs=[
                        ("session.started", {"character": {"displayName": "Late Survivor"}}),
                        ("day.started", {"partial": False}),
                        ("run.ended", {"reason": "deceased"}),
                    ],
                )
            , "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        run = ChallengeRun.objects.get()
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="terminal-reviewer@example.com",
            nickname="Terminal Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(submission.pk,))
        )

        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.DECEASED)

    def test_newer_snapshot_can_be_approved_without_new_ledger_events(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        initial_submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="snapshot-reviewer@example.com",
            nickname="Snapshot Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(initial_submission.pk,),
            )
        )

        self.client.force_login(self.participant)
        self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(
                    kills=55,
                    generated_at=1784800200,
                )
            , "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        newer_snapshot = RunSubmission.objects.get(
            status=RunSubmission.Status.RECEIVED
        )
        self.assertEqual(
            newer_snapshot.event_sequence,
            initial_submission.event_sequence,
        )
        self.assertEqual(newer_snapshot.event_hash, initial_submission.event_hash)

        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(newer_snapshot.pk,),
            )
        )

        newer_snapshot.refresh_from_db()
        run = newer_snapshot.run
        run.refresh_from_db()
        self.assertEqual(newer_snapshot.status, RunSubmission.Status.APPROVED)
        self.assertEqual(run.approved_submission, newer_snapshot)
        self.assertEqual(run.current_kills, 55)

    def test_admin_decline_requires_and_records_reason(self):
        self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        decline_url = reverse(
            "admin:registry_runsubmission_decline", args=(submission.pk,)
        )

        response = self.client.post(decline_url, {"reason": "  "})
        self.assertRedirects(
            response,
            reverse("admin:registry_runsubmission_change", args=(submission.pk,))
            + "?decline_error=reason_required",
        )
        response = self.client.get(response.url)
        self.assertContains(response, "data-run-decline-error")
        self.assertContains(
            response, "A reason is required when declining a submission."
        )
        run.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(run.status, ChallengeRun.Status.PENDING)
        self.assertIsNone(submission.reviewed_at)

        reason = "The submitted event sequence is incomplete."
        response = self.client.post(decline_url, {"reason": reason})
        self.assertRedirects(
            response,
            reverse("admin:registry_runsubmission_change", args=(submission.pk,)),
        )
        run.refresh_from_db()
        submission.refresh_from_db()
        self.assertEqual(run.status, ChallengeRun.Status.PENDING)
        self.assertEqual(submission.status, RunSubmission.Status.DECLINED)
        self.assertIsNotNone(submission.reviewed_at)
        self.assertEqual(submission.review_note, reason)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.participant,
                title="Submission declined",
                message__contains=reason,
            ).exists()
        )

    def test_admin_sets_run_lifecycle_with_required_audited_reason(self):
        self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        administrator = Participant.objects.create_superuser(
            email="lifecycle-reviewer@example.com",
            nickname="Lifecycle Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        change_url = reverse("admin:registry_challengerun_change", args=(run.pk,))
        set_status_url = reverse(
            "admin:registry_challengerun_set_status", args=(run.pk,)
        )

        page = self.client.get(change_url)
        self.assertContains(page, "Set status")
        self.assertContains(page, "Lifecycle status:")
        self.assertContains(page, "This change will appear in the run's history.")

        response = self.client.post(
            set_status_url,
            {"lifecycle_status": ChallengeRun.Lifecycle.INVALIDATED, "reason": "  "},
        )
        self.assertRedirects(response, f"{change_url}?status_error=reason_required")
        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.ACTIVE)

        reason = "The submitted evidence was found to be ineligible."
        response = self.client.post(
            set_status_url,
            {"lifecycle_status": ChallengeRun.Lifecycle.INVALIDATED, "reason": reason},
        )
        self.assertRedirects(response, change_url)
        run.refresh_from_db()
        self.assertEqual(run.lifecycle_status, ChallengeRun.Lifecycle.INVALIDATED)
        log_entry = LogEntry.objects.get(object_id=str(run.pk))
        self.assertIn('from "Active" to "Invalidated"', log_entry.change_message)
        self.assertIn(reason, log_entry.change_message)

    def test_admin_submission_page_uses_review_controls_instead_of_save_controls(self):
        self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        response = self.client.get(
            reverse("admin:registry_runsubmission_change", args=(submission.pk,))
        )
        self.assertContains(response, ">Approve</button>", html=False)
        self.assertContains(response, ">Decline</button>", html=False)
        self.assertNotContains(response, "Save and add another")
        self.assertNotContains(response, "Save and continue editing")

    def test_admin_submission_page_presents_structured_review(self):
        self.client.post(
            reverse("registry:submit_run"), {"manual_evidence_url": "https://www.twitch.tv/videos/123456", "run_export": make_export()}
        )
        submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="structured-reviewer@example.com",
            nickname="Structured Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        response = self.client.get(
            reverse("admin:registry_runsubmission_change", args=(submission.pk,))
        )

        self.assertContains(response, "Integrity findings")
        self.assertContains(response, "Export integrity verified")
        self.assertContains(response, "Recorded event types")
        self.assertContains(response, "Session started")
        self.assertContains(response, "Raw evidence and identifiers")
        self.assertContains(response, "Decoded run snapshot JSON")
        self.assertContains(response, "Decoded event history JSON")
        self.assertContains(response, '<details class="run-review-json">', count=2)
        self.assertNotContains(response, '<details class="run-review-json" open>')
        self.assertContains(response, "&quot;currentKills&quot;: 42")
        event_ledger = response.content.decode().split("Event ledger", 1)[1]
        self.assertLess(event_ledger.index("<td>2</td>"), event_ledger.index("<td>1</td>"))

    def test_review_and_approval_reject_mid_run_challenge_mode_change(self):
        cdda = {
            "id": "TGSRR_CDDA",
            "gameMode": "The Great Spiffo's Rat Race - CDDA",
        }
        sprinters = {
            "id": "TGSRR_Sprinters",
            "gameMode": "The Great Spiffo's Rat Race - Sprinters",
        }
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(challenge=cdda), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        extended_events = [
            ("session.started", {"character": {"displayName": "Test Survivor"}}),
            ("day.started", {"partial": False}),
            ("day.started", {"partial": False}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {
                "run_export": make_export(
                    kills=50,
                    event_specs=extended_events,
                    challenge=sprinters,
                )
            , "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        changed = RunSubmission.objects.order_by("-submitted_at").first()
        review = build_run_review(changed)
        self.assertTrue(
            any(
                finding["title"] == "Starting challenge mode changed"
                and finding["level"] == "danger"
                for finding in review["findings"]
            )
        )
        administrator = Participant.objects.create_superuser(
            email="challenge-reviewer@example.com",
            nickname="Challenge Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse("admin:registry_runsubmission_approve", args=(changed.pk,))
        )
        changed.refresh_from_db()
        self.assertEqual(changed.status, RunSubmission.Status.RECEIVED)

    def test_review_compares_pending_snapshot_with_approved_baseline(self):
        initial_specs = [
            ("session.started", {"character": {"displayName": "Test Survivor"}}),
            ("day.started", {"partial": False}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42, event_specs=initial_specs), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        run = ChallengeRun.objects.get()
        initial_submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="baseline-reviewer@example.com",
            nickname="Baseline Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(initial_submission.pk,),
            )
        )
        self.client.force_login(self.participant)
        extended_specs = initial_specs + [
            ("skill.level.reached", {"skill": "Woodwork", "level": 3}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=55, event_specs=extended_specs), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        pending_submission = RunSubmission.objects.get(status=RunSubmission.Status.RECEIVED)
        review = build_run_review(pending_submission)

        self.assertIsNotNone(review["baseline"])
        self.assertEqual(review["comparison"]["event_delta"], 1)
        self.assertEqual(review["comparison"]["kill_delta"], 13)
        self.assertEqual(review["comparison"]["changed_sequences"], [])
        self.assertTrue(
            any(
                finding["title"] == "Approved history is unchanged"
                for finding in review["findings"]
            )
        )

        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(pending_submission.pk,),
            )
        )
        pending_submission.refresh_from_db()
        review_after_approval = build_run_review(pending_submission)
        self.assertEqual(
            pending_submission.baseline_submission,
            initial_submission,
        )
        self.assertEqual(
            review_after_approval["baseline"],
            initial_submission,
        )
        self.assertEqual(review_after_approval["comparison"]["event_delta"], 1)

    def test_review_flags_changed_events_from_approved_history(self):
        initial_specs = [
            ("session.started", {"character": {"displayName": "Test Survivor"}}),
            ("day.started", {"partial": False}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42, event_specs=initial_specs), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        run = ChallengeRun.objects.get()
        initial_submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="history-reviewer@example.com",
            nickname="History Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(initial_submission.pk,),
            )
        )
        self.client.force_login(self.participant)
        changed_specs = [
            initial_specs[0],
            ("day.started", {"partial": True}),
            ("skill.level.reached", {"skill": "Woodwork", "level": 3}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=55, event_specs=changed_specs), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        pending_submission = RunSubmission.objects.get(status=RunSubmission.Status.RECEIVED)
        review = build_run_review(pending_submission)

        self.assertEqual(review["comparison"]["changed_sequences"], [2])
        self.assertTrue(
            any(
                "previously approved event(s) changed" in finding["title"]
                and finding["level"] == "danger"
                for finding in review["findings"]
            )
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(pending_submission.pk,),
            )
        )
        pending_submission.refresh_from_db()
        run.refresh_from_db()
        self.assertEqual(pending_submission.status, RunSubmission.Status.RECEIVED)
        self.assertEqual(run.approved_submission, initial_submission)

    def test_pending_and_declined_update_do_not_change_approved_run(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        initial_submission = RunSubmission.objects.get()
        administrator = Participant.objects.create_superuser(
            email="canonical-reviewer@example.com",
            nickname="Canonical Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse(
                "admin:registry_runsubmission_approve",
                args=(initial_submission.pk,),
            )
        )
        run = ChallengeRun.objects.get()
        self.assertEqual(run.current_kills, 42)

        self.client.force_login(self.participant)
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=99, event_specs=[
                ("session.started", {"character": {"displayName": "Test Survivor"}}),
                ("day.started", {"partial": False}),
                ("skill.level.reached", {"skill": "Woodwork", "level": 3}),
            ]), "manual_evidence_url": "https://www.twitch.tv/videos/123456"},
        )
        update = RunSubmission.objects.get(status=RunSubmission.Status.RECEIVED)
        run.refresh_from_db()
        self.assertEqual(run.current_kills, 42)
        self.assertEqual(run.approved_submission, initial_submission)

        self.client.force_login(administrator)
        self.client.post(
            reverse("admin:registry_runsubmission_decline", args=(update.pk,)),
            {"reason": "Evidence did not cover this update."},
        )
        run.refresh_from_db()
        update.refresh_from_db()
        self.assertEqual(run.current_kills, 42)
        self.assertEqual(run.status, ChallengeRun.Status.OFFICIAL)
        self.assertEqual(run.approved_submission, initial_submission)
        self.assertEqual(update.status, RunSubmission.Status.DECLINED)
