from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse
from zomboid_catalogue.models import CatalogueEntry, TraitDetails

from .leaderboard import build_current_leaderboard, build_ranking_table, weighted_completion
from .models import ChallengeRun, Participant, RunSubmission, StreamingAccount


class LeaderboardTests(TestCase):
    def setUp(self):
        self.racer = Participant.objects.create_user(
            email="leader@example.com",
            nickname="Leader",
            password="test-password",
            status=Participant.Status.VERIFIED,
            is_active=True,
        )
        positive_trait = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.TRAIT,
            stable_id="base:fit",
            display_name="Fit",
        )
        TraitDetails.objects.create(
            entry=positive_trait,
            point_cost=6,
            description="Improved fitness.<br>Can run for longer.",
        )
        negative_trait = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.TRAIT,
            stable_id="base:unfit",
            display_name="Unfit",
        )
        TraitDetails.objects.create(entry=negative_trait, point_cost=-6)

    def create_run(self, suffix, completion, *, lifecycle="active", official=True):
        projection = {
            "character": {
                "current": {"displayName": f"Survivor {suffix}", "professionId": "unemployed"},
                "selectedStartingTraits": ["base:fit", "base:unfit"],
                "currentEffectiveTraits": ["base:fit"],
            },
            "challengeProgress": {
                "categories": {
                    key: {"available": True, "progress": value}
                    for key, value in completion.items()
                }
            },
            "outposts": [
                {"id": "one", "complete": True, "progress": 1},
                {"id": "two", "complete": False, "progress": 0},
            ],
            "skills": [{"id": "Aiming", "categoryId": "Firearm", "level": 10}],
        }
        recorded = datetime(2026, 7, 31, 12, int(suffix), tzinfo=timezone.utc)
        run = ChallengeRun.objects.create(
            participant=self.racer,
            run_id=f"leaderboard-{suffix}",
            status=ChallengeRun.Status.OFFICIAL if official else ChallengeRun.Status.PENDING,
            lifecycle_status=lifecycle,
            export_format=3,
            generated_at=recorded,
            current_kills=100 + int(suffix),
            event_sequence=int(suffix),
            event_hash=str(suffix) * 64,
            character_name=f"Survivor {suffix}",
            latest_projection={"challengeProgress": {"categories": {}}},
            latest_events=[{"world_age_hours": 48}],
        )
        submission = RunSubmission.objects.create(
            run=run,
            submitter=self.racer,
            status=RunSubmission.Status.APPROVED,
            checksum=(str(int(suffix) + 1) * 64),
            raw_export=f"export-{suffix}",
            export_format=3,
            generated_at=recorded,
            current_kills=100 + int(suffix),
            event_sequence=int(suffix),
            event_hash=str(suffix) * 64,
            projection=projection,
            reviewed_at=recorded,
        )
        run.approved_submission = submission
        run.save(update_fields=("approved_submission",))
        return run

    def test_weighted_completion_gives_kills_half_of_the_score(self):
        projection = {"challengeProgress": {"categories": {
            "kills": {"available": True, "progress": 1},
            "outposts": {"available": True, "progress": 0},
            "skills": {"available": True, "progress": 0},
        }}}
        self.assertEqual(weighted_completion(projection), 50.0)

    def test_leaderboard_uses_active_personal_best_from_approved_snapshot(self):
        self.create_run("1", {"kills": 0.2, "outposts": 0.2, "skills": 0.2})
        best = self.create_run("2", {"kills": 0.8, "outposts": 0.8, "skills": 0.8})
        self.create_run("3", {"kills": 1, "outposts": 1, "skills": 1}, lifecycle="deceased")
        self.create_run("4", {"kills": 1, "outposts": 1, "skills": 1}, official=False)

        entries = build_current_leaderboard()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["run"], best)
        self.assertEqual(entries[0]["completion"], 80.0)
        self.assertEqual(entries[0]["outposts_completed"], 1)
        self.assertEqual(entries[0]["maxed_skills"], 1)

    def test_public_page_prompts_guests_and_shows_build_to_participants(self):
        run = self.create_run("5", {"kills": 0.5, "outposts": 0.5, "skills": 0.5})
        url = reverse("registry:leaderboard")

        guest = self.client.get(url)
        self.assertEqual(guest.status_code, 200)
        self.assertContains(guest, "Sign in to view survivor details")
        self.assertNotContains(guest, "View survivor record")

        self.client.force_login(self.racer)
        signed_in = self.client.get(url)
        self.assertContains(signed_in, "Show Build")
        self.assertContains(signed_in, "Selected starting traits")
        self.assertContains(signed_in, "Negative traits")
        self.assertContains(signed_in, "Positive traits")
        self.assertContains(signed_in, "+6")
        self.assertContains(signed_in, "-6")
        self.assertContains(signed_in, "Improved fitness.<br>Can run for longer.")
        self.assertContains(signed_in, "registry/images/Profession_custom.png")
        self.assertContains(signed_in, reverse("registry:public_run_detail", args=(run.pk,)))

    def test_ranking_table_filters_lifecycle_and_supports_all_rows(self):
        active = self.create_run("6", {"kills": 0.2, "outposts": 0.2, "skills": 0.2})
        deceased = self.create_run(
            "7", {"kills": 0.9, "outposts": 0.9, "skills": 0.9}, lifecycle="deceased"
        )

        entries = build_ranking_table({
            "lifecycles": ["deceased"],
            "selection": "all",
            "ordering": "weighted_completion",
            "limit": 10,
        })

        self.assertEqual([entry["run"] for entry in entries], [deceased])
        self.assertNotIn(active, [entry["run"] for entry in entries])

    def test_ranking_table_can_select_latest_run_per_participant(self):
        self.create_run("8", {"kills": 1, "outposts": 1, "skills": 1})
        latest = self.create_run("9", {"kills": 0.1, "outposts": 0.1, "skills": 0.1})

        entries = build_ranking_table({
            "lifecycles": ["active"],
            "selection": "latest_per_participant",
            "ordering": "weighted_completion",
            "limit": 10,
        })

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["run"], latest)

    def test_ranking_table_uses_participants_selected_primary_channel(self):
        account = StreamingAccount.objects.create(
            participant=self.racer,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="leader-twitch",
            channel_identity="leader-twitch",
            display_name="Leader Live",
            channel_url="https://www.twitch.tv/leaderlive",
        )
        self.racer.primary_streaming_account = account
        self.racer.save(update_fields=("primary_streaming_account",))
        self.create_run("1", {"kills": 0.2, "outposts": 0.2, "skills": 0.2})

        entries = build_ranking_table()

        self.assertEqual(entries[0]["stream_provider"], "twitch")
        self.assertEqual(entries[0]["source_url"], "https://www.twitch.tv/leaderlive")
