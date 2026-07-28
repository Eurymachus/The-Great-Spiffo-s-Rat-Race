import base64
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from .models import (
    ChallengeMode,
    ChallengeRun,
    Notification,
    Participant,
    RunSubmission,
    StreamingAccount,
    StreamingMedia,
)
from .run_exports import InvalidRunExport, decode_run_export
from .run_review import build_run_review


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


class RunExportCodecTests(TestCase):
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
            decoded.generated_at,
            datetime.fromtimestamp(1784800100, tz=timezone.utc),
        )

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
                        "schema": 2,
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
            reverse("registry:submit_run"), {"run_export": make_export()}
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
        self.assertContains(dashboard, "42 kills")

    def test_submission_maps_known_challenge_mode_and_preserves_raw_evidence(self):
        response = self.client.post(
            reverse("registry:submit_run"),
            {
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
            {
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
            {
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
        self.assertEqual(submission.challenge_mode_display, "TGSRR - Standard")

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
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(run_id="active-run")},
        )
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(run_id="past-run")},
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
        self.assertNotContains(dashboard, "active-run")
        self.assertNotContains(dashboard, "past-run")
        self.assertContains(dashboard, 'class="dashboard-run-entry"', count=4)
        self.assertContains(dashboard, "Run details", count=2)
        self.assertContains(dashboard, "Approved submissions", count=2)
        self.assertContains(dashboard, "Submission history", count=2)
        self.assertContains(dashboard, "Awaiting Review")
        self.assertContains(dashboard, "Awaiting review")

    def test_duplicate_export_is_rejected(self):
        value = make_export()
        self.client.post(reverse("registry:submit_run"), {"run_export": value})
        response = self.client.post(
            reverse("registry:submit_run"), {"run_export": value}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already been submitted")
        self.assertEqual(RunSubmission.objects.count(), 1)

    def test_admin_approval_updates_submission_and_dashboard(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export()}
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
        self.assertNotContains(dashboard, "Day 1")
        self.assertNotContains(dashboard, "Events verified")

    def test_newer_snapshot_can_be_approved_without_new_ledger_events(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42)},
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
            },
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
            reverse("registry:submit_run"), {"run_export": make_export()}
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
            reverse("admin:registry_runsubmission_change", args=(submission.pk,)),
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

    def test_admin_submission_page_uses_review_controls_instead_of_save_controls(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export()}
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
            reverse("registry:submit_run"), {"run_export": make_export()}
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
            {"run_export": make_export(challenge=cdda)},
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
            },
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
            {"run_export": make_export(kills=42, event_specs=initial_specs)},
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
            {"run_export": make_export(kills=55, event_specs=extended_specs)},
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
            {"run_export": make_export(kills=42, event_specs=initial_specs)},
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
            {"run_export": make_export(kills=55, event_specs=changed_specs)},
        )
        pending_submission = RunSubmission.objects.get(status=RunSubmission.Status.RECEIVED)
        review = build_run_review(pending_submission)

        self.assertEqual(review["comparison"]["changed_sequences"], [2])
        self.assertTrue(
            any(
                finding["title"] == "Previously approved history changed"
                and finding["level"] == "danger"
                for finding in review["findings"]
            )
        )

    def test_pending_and_declined_update_do_not_change_approved_run(self):
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=42)},
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
            ])},
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
