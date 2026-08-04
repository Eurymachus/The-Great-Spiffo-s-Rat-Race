from unittest.mock import patch

from django.core.management import call_command
from django.contrib.admin.sites import site
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from .models import Participant, WorkshopMod, WorkshopModVote
from .historical_mods import HISTORICAL_UNSTABLE_MODS


class ModsPageTests(TestCase):
    def setUp(self):
        self.racer = Participant.objects.create_user(
            email="mods@example.com",
            nickname="ModRacer",
            password="test-password",
            status=Participant.Status.VERIFIED,
            is_active=True,
        )
        WorkshopMod.objects.create(
            workshop_id="1234567890",
            title="Allowed Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567890",
            ruling=WorkshopMod.Ruling.ALLOWED,
        )
        WorkshopMod.objects.create(
            workshop_id="1234567891",
            title="Disallowed Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567891",
            ruling=WorkshopMod.Ruling.DISALLOWED,
        )

    def test_page_pins_required_mod_and_filters_public_rulings(self):
        page = self.client.get(reverse("registry:mods"), {"ruling": "allowed"})
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "The Great Spiffo&#x27;s Rat Race")
        self.assertContains(page, "Required")
        self.assertContains(page, "Allowed Example")
        self.assertNotContains(page, "Disallowed Example")

    def test_compact_list_view_is_selectable_and_preserved_by_filter_form(self):
        page = self.client.get(reverse("registry:mods"), {"view": "list"})
        self.assertContains(page, "mods-list-compact")
        self.assertContains(page, 'name="view" value="list"')
        self.assertContains(page, 'view=list" class="is-active"')

    def test_recommended_allowed_mods_are_featured_without_duplication(self):
        recommended = WorkshopMod.objects.get(workshop_id="1234567890")
        recommended.is_recommended = True
        recommended.save(update_fields=("is_recommended",))

        page = self.client.get(reverse("registry:mods"))

        self.assertContains(page, "Recommended mods")
        self.assertContains(page, "Recommended")
        self.assertContains(page, "Allowed Example", count=1)

    def test_disallowed_filter_does_not_show_recommended_section(self):
        recommended = WorkshopMod.objects.get(workshop_id="1234567890")
        recommended.is_recommended = True
        recommended.save(update_fields=("is_recommended",))

        page = self.client.get(reverse("registry:mods"), {"ruling": "disallowed"})

        self.assertNotContains(page, "Recommended mods")
        self.assertContains(page, "Disallowed Example")

    def test_mods_page_explains_current_rulings_and_cosmetic_exception(self):
        page = self.client.get(reverse("registry:mods"))

        self.assertContains(page, "Only mods marked")
        self.assertContains(page, "Disallowed</strong> and unlisted mods cannot be used")
        self.assertContains(page, "More Info")
        self.assertContains(page, "purely cosmetic")
        self.assertContains(page, "no information unavailable in the unmodded game")

    def test_duplicate_submission_preserves_reason_and_shows_ruling(self):
        self.client.force_login(self.racer)
        page = self.client.post(
            reverse("registry:mods"),
            {"workshop_id": "1234567890", "reason": "Useful quality of life."},
        )
        self.assertContains(page, "already Allowed")
        self.assertContains(page, "Useful quality of life.")
        self.assertContains(page, "data-open-on-load")

    def test_workshop_lookup_requires_authentication(self):
        response = self.client.get(
            reverse("registry:workshop_mod_lookup"), {"q": "Better Containers"}
        )

        self.assertEqual(response.status_code, 302)

    @patch("registry.views.fetch_project_zomboid_workshop_item")
    def test_workshop_lookup_resolves_an_exact_id_or_url(self, fetch_item):
        fetch_item.return_value = {
            "workshop_id": "3586216562",
            "title": "Better Containers",
            "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=3586216562",
            "preview_url": "https://example.com/container.jpg",
            "creator_steam_id": "76561198000000000",
        }
        self.client.force_login(self.racer)

        response = self.client.get(
            reverse("registry:workshop_mod_lookup"),
            {"q": "https://steamcommunity.com/sharedfiles/filedetails/?id=3586216562"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["title"], "Better Containers")
        self.assertFalse(response.json()["results"][0]["existing"])
        fetch_item.assert_called_once_with("3586216562")

    @patch("registry.views.search_project_zomboid_workshop_items")
    def test_workshop_lookup_searches_names_and_reports_existing_rulings(self, search):
        search.return_value = [
            {
                "workshop_id": "1234567890",
                "title": "Allowed Example",
                "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=1234567890",
                "preview_url": "",
                "creator_steam_id": "",
            }
        ]
        self.client.force_login(self.racer)

        response = self.client.get(
            reverse("registry:workshop_mod_lookup"), {"q": "Allowed Example"}
        )

        result = response.json()["results"][0]
        self.assertTrue(result["existing"])
        self.assertEqual(result["ruling"], "Allowed")

    @patch("registry.views.fetch_project_zomboid_workshop_item")
    def test_valid_steam_item_creates_pending_review(self, fetch_item):
        fetch_item.return_value = {
            "workshop_id": "1234567892",
            "title": "New Example",
            "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=1234567892",
            "preview_url": "https://example.com/preview.jpg",
            "creator_steam_id": "76561198000000000",
        }
        self.client.force_login(self.racer)
        response = self.client.post(
            reverse("registry:mods"),
            {"workshop_id": "1234567892", "reason": "Adds useful accessibility."},
        )
        self.assertRedirects(response, reverse("registry:mods"))
        request = WorkshopMod.objects.get(workshop_id="1234567892")
        self.assertEqual(request.ruling, WorkshopMod.Ruling.PENDING)
        self.assertEqual(request.submitted_by, self.racer)
        self.assertEqual(request.submission_reason, "Adds useful accessibility.")

    def test_historical_manifest_preserves_discord_rulings(self):
        self.assertEqual(len(HISTORICAL_UNSTABLE_MODS), 59)
        self.assertEqual(HISTORICAL_UNSTABLE_MODS["3413529369"][0], "allowed")
        self.assertEqual(HISTORICAL_UNSTABLE_MODS["2852309899"][0], "disallowed")

    @patch("registry.management.commands.import_historical_mods.fetch_project_zomboid_workshop_item")
    def test_historical_import_keeps_current_ruling_pending(self, fetch_item):
        fetch_item.return_value = {
            "workshop_id": "3413529369",
            "title": "OSRS XP Drops Retextured",
            "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=3413529369",
            "preview_url": "",
            "creator_steam_id": "",
        }
        with patch.dict(
            "registry.management.commands.import_historical_mods.HISTORICAL_UNSTABLE_MODS",
            {"3413529369": ("allowed", "Historical test ruling.")},
            clear=True,
        ):
            call_command("import_historical_mods")
        mod = WorkshopMod.objects.get(workshop_id="3413529369")
        self.assertEqual(mod.ruling, WorkshopMod.Ruling.PENDING)
        self.assertEqual(
            mod.previous_unstable_ruling,
            WorkshopMod.PreviousUnstableRuling.ALLOWED,
        )

    def test_bulk_ruling_actions_are_super_admin_only_and_protect_required(self):
        admin_user = Participant.objects.create_superuser(
            email="mods-admin@example.com",
            nickname="ModsAdmin",
            password="test-password",
        )
        request = RequestFactory().get("/admin/registry/workshopmod/")
        request.user = self.racer
        model_admin = site._registry[WorkshopMod]
        self.assertNotIn("allow_selected_mods", model_admin.get_actions(request))
        self.assertNotIn("reset_selected_rulings", model_admin.get_actions(request))

        request.user = admin_user
        actions = model_admin.get_actions(request)
        self.assertIn("allow_selected_mods", actions)
        self.assertIn("disallow_selected_mods", actions)
        self.assertIn("reset_selected_rulings", actions)

        required = WorkshopMod.objects.get(ruling=WorkshopMod.Ruling.REQUIRED)
        disallowed = WorkshopMod.objects.get(workshop_id="1234567891")
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("admin:registry_workshopmod_changelist"),
            {
                "action": "allow_selected_mods",
                ACTION_CHECKBOX_NAME: [str(required.pk), str(disallowed.pk)],
                "index": "0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        required.refresh_from_db()
        disallowed.refresh_from_db()
        self.assertEqual(required.ruling, WorkshopMod.Ruling.REQUIRED)
        self.assertEqual(disallowed.ruling, WorkshopMod.Ruling.ALLOWED)
        self.assertEqual(disallowed.reviewed_by, admin_user)
        self.assertIsNotNone(disallowed.reviewed_at)
        self.assertContains(response, "1 mod(s) marked Allowed.")

    def test_super_admin_can_reset_rulings_without_resetting_provenance(self):
        admin_user = Participant.objects.create_superuser(
            email="mods-reset-admin@example.com",
            nickname="ModsResetAdmin",
            password="test-password",
        )
        allowed = WorkshopMod.objects.get(workshop_id="1234567890")
        allowed.is_recommended = True
        allowed.public_rationale = "Previously approved for testing."
        allowed.previous_unstable_ruling = WorkshopMod.PreviousUnstableRuling.ALLOWED
        allowed.unstable_ruling_notes = "Historical decision."
        allowed.reviewed_by = admin_user
        allowed.reviewed_at = allowed.updated_at
        allowed.save()
        required = WorkshopMod.objects.get(ruling=WorkshopMod.Ruling.REQUIRED)
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:registry_workshopmod_changelist"),
            {
                "action": "reset_selected_rulings",
                ACTION_CHECKBOX_NAME: [str(required.pk), str(allowed.pk)],
                "index": "0",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        allowed.refresh_from_db()
        required.refresh_from_db()
        self.assertEqual(allowed.ruling, WorkshopMod.Ruling.PENDING)
        self.assertFalse(allowed.is_recommended)
        self.assertEqual(allowed.public_rationale, "")
        self.assertIsNone(allowed.reviewed_by)
        self.assertIsNone(allowed.reviewed_at)
        self.assertEqual(
            allowed.previous_unstable_ruling,
            WorkshopMod.PreviousUnstableRuling.ALLOWED,
        )
        self.assertEqual(allowed.unstable_ruling_notes, "Historical decision.")
        self.assertEqual(required.ruling, WorkshopMod.Ruling.REQUIRED)
        self.assertContains(response, "1 mod ruling(s) reset to Pending review.")

    def test_admin_has_pending_queue_and_focused_review_page(self):
        admin_user = Participant.objects.create_superuser(
            email="mod-review-admin@example.com",
            nickname="ModReviewAdmin",
            password="test-password",
        )
        pending = WorkshopMod.objects.create(
            workshop_id="1234567892",
            title="Pending Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567892",
            ruling=WorkshopMod.Ruling.PENDING,
            submission_reason="Please review this quality-of-life mod.",
            submitted_by=self.racer,
        )
        self.client.force_login(admin_user)

        queue = self.client.get(reverse("admin:registry_workshopmod_changelist"))
        self.assertContains(queue, "Mod approval queue")
        self.assertContains(queue, "Pending reviews (1)")
        self.assertContains(queue, ">Review</a>")

        review = self.client.get(
            reverse("admin:registry_workshopmod_change", args=(pending.pk,))
        )
        self.assertContains(review, "Mod approval review")
        self.assertContains(review, "Please review this quality-of-life mod.")
        self.assertContains(review, "View on Steam")
        self.assertContains(review, "Public rationale templates")
        self.assertContains(review, 'data-ruling="allowed"')
        self.assertContains(review, 'data-ruling="disallowed"')
        self.assertContains(
            review,
            "This mod provides gameplay information that is not available in the unmodified game.",
        )
        self.assertContains(review, "registry/admin_mod_review.js")

    def test_final_ruling_requires_rationale_and_records_reviewer(self):
        admin_user = Participant.objects.create_superuser(
            email="mod-final-reviewer@example.com",
            nickname="ModFinalReviewer",
            password="test-password",
        )
        pending = WorkshopMod.objects.create(
            workshop_id="1234567892",
            title="Pending Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567892",
            ruling=WorkshopMod.Ruling.PENDING,
        )
        self.client.force_login(admin_user)
        change_url = reverse("admin:registry_workshopmod_change", args=(pending.pk,))
        form_data = {
            "ruling": WorkshopMod.Ruling.ALLOWED,
            "public_rationale": "",
            "is_recommended": "",
            "previous_unstable_ruling": WorkshopMod.PreviousUnstableRuling.NOT_REVIEWED,
            "unstable_ruling_notes": "",
            "_continue": "Save and continue editing",
        }

        rejected = self.client.post(change_url, form_data)
        self.assertContains(rejected, "Enter the public reason for this final ruling.")
        pending.refresh_from_db()
        self.assertEqual(pending.ruling, WorkshopMod.Ruling.PENDING)

        form_data["public_rationale"] = "Purely cosmetic and within the published rules."
        accepted = self.client.post(change_url, form_data)
        self.assertEqual(accepted.status_code, 302)
        pending.refresh_from_db()
        self.assertEqual(pending.ruling, WorkshopMod.Ruling.ALLOWED)
        self.assertEqual(pending.reviewed_by, admin_user)
        self.assertIsNotNone(pending.reviewed_at)

    def test_approver_can_cast_and_change_attributable_team_vote(self):
        approver = Participant.objects.create_user(
            email="mod-voter@example.com",
            nickname="ModVoter",
            password="test-password",
            is_staff=True,
        )
        approver_group = Group.objects.create(name="Workshop Mod Approver")
        approver_group.permissions.add(
            Permission.objects.get(codename="view_workshopmod")
        )
        approver.groups.add(approver_group)
        pending = WorkshopMod.objects.create(
            workshop_id="1234567892",
            title="Pending Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567892",
            ruling=WorkshopMod.Ruling.PENDING,
        )
        self.client.force_login(approver)
        vote_url = reverse("admin:registry_workshopmod_vote", args=(pending.pk,))

        missing_reason = self.client.post(vote_url, {"decision": "disallow"}, follow=True)
        self.assertContains(missing_reason, "Enter a reason for a Disallow or Discuss vote.")
        self.assertFalse(WorkshopModVote.objects.exists())

        self.client.post(
            vote_url,
            {"decision": "disallow", "reason": "Changes gameplay balance."},
        )
        vote = WorkshopModVote.objects.get(workshop_mod=pending, voter=approver)
        self.assertEqual(vote.decision, WorkshopModVote.Decision.DISALLOW)
        self.assertEqual(vote.voter_name, "ModVoter")

        self.client.post(vote_url, {"decision": "allow", "reason": "Cosmetic only."})
        vote.refresh_from_db()
        self.assertEqual(vote.decision, WorkshopModVote.Decision.ALLOW)
        self.assertEqual(WorkshopModVote.objects.count(), 1)

        review = self.client.get(
            reverse("admin:registry_workshopmod_change", args=(pending.pk,))
        )
        self.assertContains(review, "Recommend Allow")
        self.assertContains(review, "ModVoter")
        self.assertContains(review, "Cosmetic only.")
        self.assertContains(review, f'formaction="{vote_url}"')
        self.assertNotContains(review, f'<form method="post" action="{vote_url}"')

    def test_team_vote_does_not_change_ruling_and_closes_after_final_decision(self):
        admin_user = Participant.objects.create_superuser(
            email="mod-vote-admin@example.com",
            nickname="ModVoteAdmin",
            password="test-password",
        )
        pending = WorkshopMod.objects.create(
            workshop_id="1234567892",
            title="Pending Example",
            steam_url="https://steamcommunity.com/sharedfiles/filedetails/?id=1234567892",
            ruling=WorkshopMod.Ruling.PENDING,
        )
        self.client.force_login(admin_user)
        vote_url = reverse("admin:registry_workshopmod_vote", args=(pending.pk,))
        self.client.post(vote_url, {"decision": "discuss", "reason": "Needs testing."})
        pending.refresh_from_db()
        self.assertEqual(pending.ruling, WorkshopMod.Ruling.PENDING)

        pending.ruling = WorkshopMod.Ruling.ALLOWED
        pending.public_rationale = "Approved after review."
        pending.save()
        closed = self.client.post(vote_url, {"decision": "disallow", "reason": "Changed mind."}, follow=True)
        self.assertContains(closed, "Voting is closed because this mod has a final ruling.")
        vote = WorkshopModVote.objects.get(workshop_mod=pending, voter=admin_user)
        self.assertEqual(vote.decision, WorkshopModVote.Decision.DISCUSS)

    def test_bootstrap_roles_separates_mod_and_run_approval_authority(self):
        legacy = Group.objects.create(name="Approver")
        legacy.permissions.add(Permission.objects.get(codename="view_workshopmod"))

        call_command("bootstrap_roles", verbosity=0)

        mod_group = Group.objects.get(name="Workshop Mod Approver")
        run_group = Group.objects.get(name="Run Submission Approver")
        self.assertSetEqual(
            set(mod_group.permissions.values_list("codename", flat=True)),
            {"view_workshopmod"},
        )
        self.assertSetEqual(
            set(run_group.permissions.values_list("codename", flat=True)),
            {"view_challengerun", "view_runsubmission", "change_runsubmission"},
        )
        self.assertFalse(legacy.permissions.exists())

        mod_approver = Participant.objects.create_user(
            email="scoped-mod-approver@example.com",
            nickname="ScopedModApprover",
            password="test-password",
        )
        mod_approver.groups.add(mod_group)
        run_approver = Participant.objects.create_user(
            email="scoped-run-approver@example.com",
            nickname="ScopedRunApprover",
            password="test-password",
        )
        run_approver.groups.add(run_group)
        model_admin = site._registry[WorkshopMod]
        self.assertTrue(model_admin.can_vote(mod_approver))
        self.assertFalse(model_admin.can_vote(run_approver))
