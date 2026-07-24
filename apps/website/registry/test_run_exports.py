import base64
import hashlib
from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse

from .models import (
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


def event_body(run_id, sequence, event_type, payload):
    return b"".join(
        (
            tagged("v", 1),
            tagged("r", run_id),
            tagged("e", 1),
            tagged("q", sequence),
            tagged("t", 1784800000 + sequence),
            tagged("w", sequence),
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


def make_export(run_id="rr-web-test", kills=42, event_specs=None, projection=None):
    event_specs = event_specs or [
        ("session.started", {"character": {"displayName": "Test Survivor"}}),
        ("day.started", {"partial": False}),
    ]
    bodies = [
        event_body(run_id, sequence, event_type, payload)
        for sequence, (event_type, payload) in enumerate(event_specs, start=1)
    ]
    previous_hash = "0" * 64
    for body in bodies:
        previous_hash = hashlib.sha256(previous_hash.encode() + body).hexdigest()
    body_frames = b"".join(frame(body) for body in bodies)
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
    canonical = b"".join(
        frame(value)
        for value in (
            3,
            run_id,
            1784800100,
            len(bodies),
            previous_hash,
            canonical_value(projection),
            body_frames,
        )
    )
    checksum = hashlib.sha256(canonical).hexdigest()
    payload = base64.urlsafe_b64encode(literal_lzss(canonical)).decode().rstrip("=")
    return f"TGSRR1.LZ1.{payload}.{checksum}"


class RunExportCodecTests(TestCase):
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
        past_run = ChallengeRun.objects.get(run_id="past-run")
        past_run.lifecycle_status = ChallengeRun.Lifecycle.DECEASED
        past_run.save(update_fields=("lifecycle_status",))

        dashboard = self.client.get(reverse("registry:account"))

        self.assertContains(dashboard, "Past Runs")
        self.assertContains(dashboard, "Deceased")
        self.assertContains(dashboard, "active-run")
        self.assertContains(dashboard, "past-run")

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
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        response = self.client.post(
            reverse("admin:registry_challengerun_approve", args=(run.pk,))
        )
        self.assertRedirects(
            response,
            reverse("admin:registry_challengerun_change", args=(run.pk,)),
        )
        run.refresh_from_db()
        submission = RunSubmission.objects.get()
        self.assertEqual(run.status, ChallengeRun.Status.APPROVED)
        self.assertIsNotNone(run.reviewed_at)
        self.assertEqual(run.review_reason, "")
        self.assertEqual(submission.status, RunSubmission.Status.APPROVED)
        self.assertEqual(submission.reviewed_at, run.reviewed_at)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.participant, title="Submission approved"
            ).exists()
        )
        self.client.force_login(self.participant)
        dashboard = self.client.get(reverse("registry:account"))
        self.assertContains(dashboard, "Approved")
        self.assertContains(dashboard, "Test Survivor")

    def test_admin_decline_requires_and_records_reason(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        decline_url = reverse(
            "admin:registry_challengerun_decline", args=(run.pk,)
        )

        response = self.client.post(decline_url, {"reason": "  "})
        self.assertRedirects(
            response,
            reverse("admin:registry_challengerun_change", args=(run.pk,)),
        )
        run.refresh_from_db()
        self.assertEqual(run.status, ChallengeRun.Status.UNDER_REVIEW)
        self.assertIsNone(run.reviewed_at)

        reason = "The submitted event sequence is incomplete."
        response = self.client.post(decline_url, {"reason": reason})
        self.assertRedirects(
            response,
            reverse("admin:registry_challengerun_change", args=(run.pk,)),
        )
        run.refresh_from_db()
        submission = RunSubmission.objects.get()
        self.assertEqual(run.status, ChallengeRun.Status.DECLINED)
        self.assertIsNotNone(run.reviewed_at)
        self.assertEqual(run.review_reason, reason)
        self.assertEqual(submission.status, RunSubmission.Status.DECLINED)
        self.assertEqual(submission.reviewed_at, run.reviewed_at)
        self.assertEqual(submission.review_note, reason)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.participant,
                title="Submission declined",
                message__contains=reason,
            ).exists()
        )

    def test_admin_run_page_uses_review_controls_instead_of_save_controls(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        administrator = Participant.objects.create_superuser(
            email="reviewer@example.com",
            nickname="Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        response = self.client.get(
            reverse("admin:registry_challengerun_change", args=(run.pk,))
        )
        self.assertContains(response, ">Approve</button>", html=False)
        self.assertContains(response, ">Decline</button>", html=False)
        self.assertNotContains(response, "Save and add another")
        self.assertNotContains(response, "Save and continue editing")

    def test_admin_run_page_presents_structured_review(self):
        self.client.post(
            reverse("registry:submit_run"), {"run_export": make_export()}
        )
        run = ChallengeRun.objects.get()
        administrator = Participant.objects.create_superuser(
            email="structured-reviewer@example.com",
            nickname="Structured Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)

        response = self.client.get(
            reverse("admin:registry_challengerun_change", args=(run.pk,))
        )

        self.assertContains(response, "Integrity findings")
        self.assertContains(response, "Export integrity verified")
        self.assertContains(response, "Recorded event types")
        self.assertContains(response, "Session started")
        self.assertContains(response, "Raw evidence and identifiers")

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
        administrator = Participant.objects.create_superuser(
            email="baseline-reviewer@example.com",
            nickname="Baseline Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse("admin:registry_challengerun_approve", args=(run.pk,))
        )
        self.client.force_login(self.participant)
        extended_specs = initial_specs + [
            ("skill.level.reached", {"skill": "Woodwork", "level": 3}),
        ]
        self.client.post(
            reverse("registry:submit_run"),
            {"run_export": make_export(kills=55, event_specs=extended_specs)},
        )
        run.refresh_from_db()

        review = build_run_review(run)

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
        administrator = Participant.objects.create_superuser(
            email="history-reviewer@example.com",
            nickname="History Reviewer",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        self.client.post(
            reverse("admin:registry_challengerun_approve", args=(run.pk,))
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
        run.refresh_from_db()

        review = build_run_review(run)

        self.assertEqual(review["comparison"]["changed_sequences"], [2])
        self.assertTrue(
            any(
                finding["title"] == "Previously approved history changed"
                and finding["level"] == "danger"
                for finding in review["findings"]
            )
        )
