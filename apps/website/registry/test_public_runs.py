from datetime import datetime, timezone

from django.test import TestCase
from django.urls import reverse

from zomboid_catalogue.models import (
    CatalogueAsset,
    CatalogueEntry,
    OccupationDetails,
    SkillDetails,
    TraitDetails,
)

from .models import (
    ChallengeMode,
    ChallengeRun,
    Participant,
    RunOutpost,
    RunOutpostDeliverable,
    RunKillSummary,
    RunSkill,
    RunStartingLocation,
    RunSubmission,
)


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
        aiming = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="Aiming",
            display_name="Aiming",
            introduced_in="42.19",
        )
        SkillDetails.objects.create(entry=aiming, category="Firearm")
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
        map_entry = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.Map",
            display_name="Map",
            introduced_in="42.20",
        )
        map_asset = CatalogueAsset.objects.create(
            entry=map_entry,
            role=CatalogueAsset.Role.ICON,
            source_key="Map",
            source_type=CatalogueAsset.SourceType.PZWIKI,
            availability=CatalogueAsset.Availability.IMPORTED,
            alt_text="Map",
        )
        map_asset.file.name = "catalogue/42.20/item/Map.png"
        map_asset.save(update_fields=("file",))
        occupation = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.OCCUPATION,
            stable_id="base:carpenter",
            display_name="Carpenter",
            introduced_in="42.19",
        )
        OccupationDetails.objects.create(entry=occupation, point_cost=-2)
        trait_costs = {
            "base:fit": 6,
            "base:dextrous": 2,
            "base:fastlearner": 0,
            "base:outdoorsman": 4,
        }
        for stable_id, point_cost in trait_costs.items():
            trait = CatalogueEntry.objects.create(
                kind=CatalogueEntry.Kind.TRAIT,
                stable_id=stable_id,
                display_name=stable_id.removeprefix("base:").replace("learner", " Learner").title(),
                introduced_in="42.19",
            )
            TraitDetails.objects.create(
                entry=trait,
                point_cost=point_cost,
                xp_boosts=(
                    {"Lightfoot": 1, "Nimble": 1}
                    if stable_id == "base:fastlearner"
                    else {}
                ),
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
            "weaponKills": {
                "sources": [
                    {"id": "Base.Axe", "kills": 27},
                    {"id": "Base.Hammer", "kills": 8},
                ]
            },
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
                    },
                    "landmarks": {
                        "available": True,
                        "current": 1,
                        "target": 21,
                        "progress": 1 / 21,
                        "status": "active",
                    },
                    "outposts": {
                        "available": True,
                        "current": 0,
                        "target": 13,
                        "progress": 0,
                        "status": "active",
                    },
                    "skills": {
                        "available": True,
                        "current": 0,
                        "target": 35,
                        "progress": 0,
                        "status": "active",
                    },
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
        RunStartingLocation.objects.create(
            run=self.run,
            chosen_region_schema=1,
            selection_mode=RunStartingLocation.SelectionMode.RANDOM,
            resolved_region_raw_id="Irvington, KY",
            chosen_region_captured_utc=1786823597,
            x=1912,
            y=14381,
            z=0,
            building_def_id="15762628760567811",
            captured_utc=1786823632,
            world_age_hours=2,
            partial=False,
        )
        RunSkill.objects.create(
            run=self.run,
            raw_skill_id="Aiming",
            raw_category_id="Firearm",
            catalogue_entry=CatalogueEntry.objects.get(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id="Aiming",
            ),
            level=2,
            xp=150,
        )
        RunSkill.objects.create(
            run=self.run,
            raw_skill_id="FlintKnapping",
            raw_category_id="Crafting",
            catalogue_entry=CatalogueEntry.objects.get(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id="FlintKnapping",
            ),
            level=5,
            xp=3028.6,
        )
        outpost = RunOutpost.objects.create(
            run=self.run,
            raw_outpost_id="echo_creek",
            catalogue_entry=CatalogueEntry.objects.get(
                kind=CatalogueEntry.Kind.OUTPOST,
                stable_id="echo_creek",
            ),
            discovered=True,
            discovered_world_age_hours=12,
            stage="in_progress",
            complete=False,
            progress=0.75,
            passed_requirements=10,
            total_requirements=14,
            work_started_world_age_hours=14,
            completion_count=2,
            regression_count=2,
            current_state="incomplete",
        )
        RunOutpostDeliverable.objects.create(
            outpost=outpost,
            raw_deliverable_id="engine_start",
            available=True,
            passed=True,
            current_value=1,
            required_value=1,
            observed_state="complete",
            progress=1,
            observed_world_age_hours=15,
            completion_count=2,
            regression_count=1,
            current_state="complete",
        )
        RunOutpostDeliverable.objects.create(
            outpost=outpost,
            raw_deliverable_id="doors_closed",
            available=True,
            passed=True,
            current_value=5,
            required_value=5,
            observed_state="",
            progress=1,
            observed_world_age_hours=15,
            current_state="complete",
        )
        RunOutpostDeliverable.objects.create(
            outpost=outpost,
            raw_deliverable_id="window_barricades",
            available=True,
            passed=False,
            current_value=0,
            required_value=21,
            observed_state="",
            progress=0,
            observed_world_age_hours=15,
            current_state="incomplete",
        )
        RunOutpost.objects.create(
            run=self.run,
            raw_outpost_id="rosewood",
            discovered=False,
            stage="unexplored",
            current_state="incomplete",
        )
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
        self.assertContains(
            response,
            'class="card card-wide account-dashboard run-public-page"',
        )
        content = response.content.decode()
        self.assertLess(
            content.index('aria-label="Breadcrumb"'),
            content.index('class="account-dashboard-header run-public-hero"'),
        )
        self.assertContains(response, profile_url, count=2)
        self.assertContains(response, "Back to RatRacer")
        self.assertContains(response, "Esteban Grossman")
        self.assertContains(response, "RatRacer")
        self.assertContains(response, "TGSRR")
        self.assertContains(response, "6,124")
        self.assertContains(response, "Echo Creek")
        self.assertContains(response, "Challenge progress")
        self.assertContains(response, 'data-run-build-open="run-build-dialog"')
        self.assertContains(response, 'id="run-build-dialog"')
        self.assertContains(response, "Profession")
        self.assertContains(
            response,
            'Carpenter <span class="profession-point-cost is-negative">-2</span>',
        )
        self.assertContains(response, "Selected starting traits")
        self.assertContains(response, "Currently effective traits")
        self.assertContains(response, "Passive")
        self.assertContains(response, "Starts with +1 Lightfoot and +1 Nimble.")
        self.assertContains(response, "Gained")
        self.assertContains(response, "No longer effective")
        self.assertContains(response, "Lost")
        self.assertContains(response, "is-passive")
        self.assertContains(response, 'role="tablist"')
        self.assertContains(response, 'data-build-tab="selected"')
        self.assertContains(response, 'data-build-tab="current"')
        self.assertContains(response, 'aria-label="Current weight: 79.1 kg"')
        self.assertContains(response, 'aria-label="Favourite weapon: Axe, 27 kills"')
        self.assertNotContains(response, "Current state")
        self.assertNotContains(response, "Most frequently broken weapon")
        self.assertContains(response, "10 / 14")
        self.assertNotContains(response, "completions")
        self.assertNotContains(response, "regressions")
        self.assertContains(response, "Spare car started")
        self.assertContains(response, "Doors closed")
        self.assertContains(response, "5 / 5")
        self.assertContains(response, "Discovery")
        self.assertContains(response, "Passed")
        self.assertContains(response, "Pending")
        self.assertContains(response, "Undiscovered")
        self.assertContains(response, "In Progress")
        self.assertContains(response, '<details class="run-outpost-detail', count=1)
        self.assertContains(response, 'class="run-outpost-detail run-outpost-undiscovered"', count=12)
        self.assertContains(response, 'data-outpost-dialog-open="run-outpost-dialog"')
        self.assertContains(response, 'id="run-outpost-dialog"')
        self.assertContains(response, 'data-skills-dialog-open="run-skills-dialog"')
        self.assertContains(response, 'id="run-skills-dialog"')
        self.assertContains(response, "1 / 12 towns visited.")
        self.assertNotContains(response, "World progress")
        self.assertNotContains(response, 'class="run-public-summary"')
        self.assertLess(
            content.index("Day 225"),
            content.index('<div class="run-public-name-row">'),
        )
        self.assertLess(
            content.index('data-run-build-open="run-build-dialog"'),
            content.index('aria-label="Current weight: 79.1 kg"'),
        )
        self.assertLess(
            content.index('aria-label="Current weight: 79.1 kg"'),
            content.index('aria-label="Favourite weapon: Axe, 27 kills"'),
        )
        self.assertLess(content.index("Kills"), content.index("Skills"))
        self.assertLess(content.index("Skills"), content.index("Outposts"))
        self.assertLess(content.index("Outposts"), content.index("Landmarks"))
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
        self.assertNotContains(response, "skills mastered")
        self.assertContains(response, "Fast Learner")
        self.assertContains(response, "Spawn choice")
        self.assertContains(response, "Random Spawn, KY")
        self.assertContains(response, "Starting location")
        self.assertNotContains(response, ">1912, 14381<")
        self.assertContains(
            response, "https://map.projectzomboid.com?1912x14381x0"
        )
        self.assertContains(
            response,
            'src="/media/catalogue/42.20/item/Map.png" alt="View map"',
        )
        self.assertNotContains(response, "Irvington, KY")
        self.assertNotContains(response, "15762628760567811")
        self.assertNotContains(response, self.run.run_id)
        self.assertNotContains(response, self.submission.checksum)
        self.assertNotContains(response, self.run.event_hash)

    def test_long_road_uses_authoritative_kills_when_derived_progress_is_stale(self):
        self.client.force_login(self.participant)
        self.submission.projection["challengeProgress"]["categories"]["kills"].update(
            current=0,
            progress=0,
        )
        self.submission.save(update_fields=("projection",))
        self.run.current_kills = 18_190
        self.run.save(update_fields=("current_kills",))
        RunKillSummary.objects.create(run=self.run, current_kills=18_190)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "18,190 / 1,000,000")

    def test_long_road_accepts_missing_derived_progress(self):
        self.client.force_login(self.participant)
        self.submission.projection.pop("challengeProgress")
        self.submission.save(update_fields=("projection",))
        self.run.current_kills = 18_190
        self.run.save(update_fields=("current_kills",))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "18,190 / 1,000,000")

    def test_skill_progress_percentage_includes_partial_skill_levels(self):
        self.client.force_login(self.participant)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0 / 2")
        self.assertContains(response, "35.0%")

    def test_outposts_are_grouped_by_completion_and_discovery_state(self):
        RunOutpost.objects.filter(
            run=self.run,
            raw_outpost_id="rosewood",
        ).update(
            discovered=True,
            stage="completed",
            complete=True,
            progress=1,
            passed_requirements=14,
            total_requirements=14,
            current_state="complete",
        )
        self.client.force_login(self.participant)

        response = self.client.get(self.url)

        content = response.content.decode()
        self.assertLess(
            content.index("<strong>Rosewood</strong>"),
            content.index("<strong>Echo Creek</strong>"),
        )
        self.assertLess(
            content.index("<strong>Echo Creek</strong>"),
            content.index("<strong>Brandenburg</strong>"),
        )

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
