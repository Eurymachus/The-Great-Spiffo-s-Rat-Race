from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse

from zomboid_catalogue.models import CatalogueAsset, CatalogueEntry, SkillDetails

from .models import ChallengeMode, ChallengeRun, Participant, RunSubmission


class PublicRunDetailTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create_user(
            email="racer@example.com",
            nickname="RatRacer",
            password="correct horse battery staple",
            status=Participant.Status.VERIFIED,
            is_active=True,
        )
        self.mode = ChallengeMode.objects.get(key="TGSRR")
        skill = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="FlintKnapping",
            display_name="Knapping",
            introduced_in="42.19",
        )
        SkillDetails.objects.create(entry=skill, category="Crafting")
        skill_asset = CatalogueAsset.objects.create(
            entry=skill,
            role=CatalogueAsset.Role.ICON,
            source_key="perk_FlintKnapping",
            source_type=CatalogueAsset.SourceType.PZWIKI,
            availability=CatalogueAsset.Availability.IMPORTED,
        )
        skill_asset.file.name = "catalogue/42.19/skill/Knapping.png"
        skill_asset.save(update_fields=("file",))
        game_skill_asset = CatalogueAsset.objects.create(
            entry=skill,
            role=CatalogueAsset.Role.ICON,
            source_key="TGSRR_Skill_FlintKnapping",
            source_type=CatalogueAsset.SourceType.GAME,
            availability=CatalogueAsset.Availability.IMPORTED,
        )
        game_skill_asset.file.name = "catalogue/42.19/skill/mod-knapping.png"
        game_skill_asset.save(update_fields=("file",))
        CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.OCCUPATION,
            stable_id="base:carpenter",
            display_name="Carpenter",
            introduced_in="42.19",
        )
        recorded_at = datetime(2026, 7, 28, 10, 3, 49, tzinfo=timezone.utc)
        self.projection = {
            "schema": 1,
            "currentKills": 6124,
            "character": {
                "current": {
                    "displayName": "Esteban Grossman",
                    "professionId": "carpenter",
                },
                "selectedStartingTraits": [
                    "base:fit",
                    "base:dextrous",
                    "base:fastlearner",
                ],
                "currentEffectiveTraits": ["base:fit", "base:outdoorsman"],
            },
            "weight": {"currentKilograms": 79.1},
            "distance": {"travelledMeters": 1703},
            "activeGameplay": {"milliseconds": 3_600_000},
            "nimbleStance": {"movementMilliseconds": 60_000},
            "challengeProgress": {
                "categories": {
                    "kills": {
                        "available": True,
                        "current": 6124,
                        "target": 1_000_000,
                        "progress": 0.006124,
                        "status": "in_progress",
                    }
                }
            },
            "skills": [
                {"id": "Aiming", "categoryId": "Firearm", "level": 2, "xp": 150},
                {
                    "id": "FlintKnapping",
                    "categoryId": "Crafting",
                    "level": 5,
                    "xp": 3028.6,
                },
            ],
            "outposts": [
                {
                    "id": "echo_creek",
                    "stage": "active",
                    "progress": 0.5,
                    "passedRequirements": 5,
                    "totalRequirements": 10,
                    "complete": False,
                }
            ],
            "townVisits": {
                "towns": [
                    {"id": "muldraugh", "visited": True},
                    {"id": "rosewood", "visited": False},
                ]
            },
            "injuries": {"all": {"total": 0}},
            "fishCaught": {"total": 2},
            "animalsTrapped": {"total": 0},
            "animalsSlaughtered": {"total": 0},
            "animalBirths": {"total": 0},
            "brokenWeapons": {"total": 1},
            "milkCollected": {"total": 0},
            "butterProduced": {"count": 0},
            "fireDeaths": {"count": 0},
        }
        self.run = ChallengeRun.objects.create(
            participant=self.participant,
            run_id="rr-private-technical-identifier",
            status=ChallengeRun.Status.PENDING,
            challenge_mode=self.mode,
            challenge_id="TGSRR",
            challenge_game_mode="The Great Spiffo's Rat Race",
            export_format=3,
            generated_at=recorded_at,
            current_kills=6124,
            event_sequence=21,
            event_hash="a" * 64,
            character_name="Esteban Grossman",
            latest_projection=self.projection,
            latest_events=[{"world_age_hours": 5376}],
        )
        self.submission = RunSubmission.objects.create(
            run=self.run,
            submitter=self.participant,
            status=RunSubmission.Status.APPROVED,
            checksum="b" * 64,
            raw_export="not exposed publicly",
            export_format=3,
            generated_at=recorded_at,
            current_kills=6124,
            event_sequence=21,
            event_hash="a" * 64,
            projection=self.projection,
            challenge_mode=self.mode,
            challenge_id="TGSRR",
            challenge_game_mode="The Great Spiffo's Rat Race",
            reviewed_at=recorded_at,
        )
        self.run.status = ChallengeRun.Status.OFFICIAL
        self.run.approved_submission = self.submission
        self.run.save(update_fields=("status", "approved_submission"))
        self.url = reverse("registry:public_run_detail", args=(self.run.pk,))

    def test_verified_run_requires_sign_in(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f"{reverse('registry:login')}?next={self.url}",
        )

    def test_verified_run_is_player_facing_after_sign_in(self):
        self.client.force_login(self.participant)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verified Rat Race run")
        profile_url = reverse(
            "registry:participant_profile", args=(self.participant.pk,)
        )
        self.assertContains(response, 'aria-label="Breadcrumb"')
        self.assertContains(response, profile_url, count=2)
        self.assertContains(response, "Back to RatRacer")
        self.assertContains(response, "Esteban Grossman")
        self.assertContains(response, "RatRacer")
        self.assertContains(response, "TGSRR - Standard")
        self.assertContains(response, "6,124")
        self.assertContains(response, "Echo Creek")
        self.assertContains(response, "Muldraugh")
        self.assertContains(response, "Aiming")
        self.assertContains(response, "Knapping")
        self.assertNotContains(response, ">Flint Knapping<")
        self.assertContains(response, "Combat - Firearms")
        self.assertContains(response, "pz-skill-segments")
        self.assertContains(
            response,
            "/media/catalogue/42.19/skill/Knapping.png",
        )
        self.assertNotContains(response, "TGSRR_Skill_")
        self.assertNotContains(response, "mod-knapping.png")
        self.assertContains(response, "0 of 2 skills mastered (35.0%)")
        self.assertContains(response, "Fast Learner")
        self.assertNotContains(response, self.run.run_id)
        self.assertNotContains(response, self.submission.checksum)
        self.assertNotContains(response, self.run.event_hash)

    def test_pending_run_is_not_public(self):
        self.client.force_login(self.participant)
        self.run.status = ChallengeRun.Status.PENDING
        self.run.save(update_fields=("status",))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_account_run_dialog_links_to_public_page(self):
        self.client.force_login(self.participant)

        response = self.client.get(reverse("registry:account"))

        self.assertContains(response, self.url)
        self.assertContains(response, "View full details")
