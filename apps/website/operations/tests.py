import io
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from operations.reference_update import installed_build_id
from operations.decompilation import run_decompilation
from operations.management.commands.run_reference_update_worker import (
    run_wiki_icon_sync,
)
from operations.models import (
    CatalogueImportReview,
    PZWikiArtworkSyncJob,
    ReferenceSource,
    ReferenceUpdateJob,
)
from operations.catalogue_review import (
    approve_catalogue_review,
    catalogue_diff,
    revert_catalogue_review,
)
from zomboid_catalogue.models import (
    CatalogueAsset,
    CatalogueEntry,
    ItemDisplayCategory,
    ItemDetails,
    SkillDetails,
)
from operations import steam_auth
from operations.steam_auth import begin_authentication
from registry.models import ChallengeRun, Notification, Participant, RunSubmission


class SystemOperationChangelistTests(TestCase):
    def setUp(self):
        self.admin = Participant.objects.create_superuser(
            email="operations-admin@example.com",
            nickname="OperationsAdmin",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def test_record_changelists_enable_clickable_rows(self):
        changelists = (
            "admin:operations_referencesource_changelist",
            "admin:operations_referenceupdatejob_changelist",
            "admin:operations_catalogueimportreview_changelist",
            "admin:operations_pzwikiartworksyncjob_changelist",
        )

        for changelist in changelists:
            with self.subTest(changelist=changelist):
                response = self.client.get(reverse(changelist))
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "operations/js/clickable-operation-rows.js",
                )

    def test_run_submission_changelist_uses_review_title_and_clickable_rows(self):
        response = self.client.get(
            reverse("admin:registry_runsubmission_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Run submission reviews")
        self.assertNotContains(response, "Select run submission to change")
        self.assertContains(
            response,
            "operations/js/clickable-operation-rows.js",
        )


class RunDataDangerZoneTests(TestCase):
    def setUp(self):
        self.admin = Participant.objects.create_superuser(
            email="purge-admin@example.com",
            nickname="PurgeAdmin",
            password="test-password",
        )
        self.participant = Participant.objects.create_user(
            email="runner@example.com",
            nickname="Runner",
            password="test-password",
        )
        self.run = ChallengeRun.objects.create(
            participant=self.participant,
            run_id="rr-danger-zone-test",
            export_format=3,
            generated_at=timezone.now(),
            event_hash="a" * 64,
        )
        self.submission = RunSubmission.objects.create(
            run=self.run,
            submitter=self.participant,
            checksum="b" * 64,
            raw_export="test export",
            export_format=3,
            generated_at=timezone.now(),
            event_hash="c" * 64,
        )
        self.run.approved_submission = self.submission
        self.run.save(update_fields=("approved_submission",))
        Notification.objects.create(
            recipient=self.participant,
            category=Notification.Category.SUBMISSION,
            title="Submission received",
            message="Awaiting review.",
            destination="/account/",
        )
        Notification.objects.create(
            recipient=self.participant,
            category=Notification.Category.ACCOUNT,
            title="Account retained",
            message="This must survive the purge.",
        )
        self.url = reverse("admin:operations_rundatadangerzone_changelist")

    def test_danger_zone_is_superuser_only(self):
        self.client.force_login(self.participant)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response["Location"])

    def test_confirmation_must_match_exactly(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"confirmation": "delete"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ChallengeRun.objects.exists())
        self.assertTrue(RunSubmission.objects.exists())

    def test_confirmed_purge_removes_run_graph_and_submission_notifications(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url,
            {"confirmation": "DELETE ALL RUN DATA"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChallengeRun.objects.exists())
        self.assertFalse(RunSubmission.objects.exists())
        self.assertFalse(
            Notification.objects.filter(
                category=Notification.Category.SUBMISSION
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(category=Notification.Category.ACCOUNT).exists()
        )
        self.assertTrue(Participant.objects.filter(pk=self.participant.pk).exists())


class ReferenceUpdateTests(TestCase):
    def test_reference_source_is_seeded(self):
        self.assertTrue(ReferenceSource.objects.filter(app_id=108600).exists())

    def test_reads_installed_build_id(self):
        with TemporaryDirectory() as root:
            manifest = Path(root) / "steamapps" / "appmanifest_108600.acf"
            manifest.parent.mkdir()
            manifest.write_text('"buildid" "123456"', encoding="utf-8")
            self.assertEqual(installed_build_id(root), "123456")

    def test_reads_build_id_from_a_steam_game_install_root(self):
        with TemporaryDirectory() as root:
            game_root = Path(root) / "steamapps" / "common" / "ProjectZomboid"
            game_root.mkdir(parents=True)
            manifest = Path(root) / "steamapps" / "appmanifest_108600.acf"
            manifest.write_text('"buildid" "654321"', encoding="utf-8")
            self.assertEqual(installed_build_id(game_root), "654321")

    @override_settings(
        STEAMCMD_USERNAME="reference-account",
        STEAMCMD_UPDATE_TIMEOUT_SECONDS=30,
    )
    def test_authentication_failure_is_recorded_and_notified(self):
        Participant.objects.create_superuser(
            email="admin@example.com", nickname="Admin", password="test-password"
        )
        with TemporaryDirectory() as root:
            executable = Path(root) / "steamcmd.exe"
            executable.touch()
            with self.settings(
                STEAMCMD_EXECUTABLE=executable,
                PZ_REFERENCE_ROOT=Path(root) / "pz",
            ), patch("subprocess.run") as run:
                run.return_value.returncode = 5
                run.return_value.stdout = "Account Login Denied Failed"
                run.return_value.stderr = ""
                call_command("update_pz_reference")
                call_command("run_reference_update_worker", once=True)

        source = ReferenceSource.objects.get()
        self.assertEqual(
            source.authentication_status,
            ReferenceSource.AuthenticationStatus.AUTHENTICATION_REQUIRED,
        )
        self.assertEqual(
            ReferenceUpdateJob.objects.get().status,
            ReferenceUpdateJob.Status.AUTHENTICATION_REQUIRED,
        )
        self.assertTrue(
            Participant.objects.get(email="admin@example.com").notifications.filter(
                title="Steam authentication required"
            ).exists()
        )

    @override_settings(
        STEAMCMD_EXECUTABLE="",
        STEAMCMD_USERNAME="",
        PZ_REFERENCE_ROOT="",
        STEAMCMD_UPDATE_TIMEOUT_SECONDS=30,
    )
    def test_update_uses_reference_source_configuration(self):
        with TemporaryDirectory() as root:
            executable = Path(root) / "steamcmd.exe"
            executable.touch()
            install_root = Path(root) / "pz"
            source = ReferenceSource.objects.get()
            source.account_name = "reference-account"
            source.steamcmd_path = str(executable)
            source.install_root = str(install_root)
            source.save()
            with patch("subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "Success"
                run.return_value.stderr = ""
                call_command("update_pz_reference")
                call_command("run_reference_update_worker", once=True)
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[0], str(executable))
        self.assertIn("reference-account", arguments)

    @override_settings(
        JAVA_EXECUTABLE="",
        VINEFLOWER_JAR="",
        PZ_DECOMPILED_ROOT="",
        PZ_DECOMPILATION_TIMEOUT_SECONDS=30,
    )
    def test_decompilation_replaces_reference_only_after_validation(self):
        with TemporaryDirectory() as root:
            library = Path(root)
            install_root = library / "steamapps" / "common" / "ProjectZomboid"
            install_root.mkdir(parents=True)
            (install_root / "projectzomboid.jar").touch()
            manifest = library / "steamapps" / "appmanifest_108600.acf"
            manifest.write_text('"buildid" "777"', encoding="utf-8")
            java = library / "java.exe"
            java.touch()
            decompiler = library / "vineflower.jar"
            decompiler.touch()
            output_parent = install_root / "decompiled"
            old_file = output_parent / "old-reference" / "old.txt"
            old_file.parent.mkdir(parents=True)
            old_file.write_text("old", encoding="utf-8")

            source = ReferenceSource.objects.get()
            source.install_root = str(install_root)
            source.java_executable = str(java)
            source.decompiler_jar = str(decompiler)
            source.save()
            job = ReferenceUpdateJob.objects.create(
                source=source,
                operation=ReferenceUpdateJob.Operation.DECOMPILE,
                status=ReferenceUpdateJob.Status.RUNNING,
            )

            def write_decompiled_output(arguments, **kwargs):
                staging = Path(arguments[-1])
                sentinel = (
                    staging
                    / "zombie"
                    / "characters"
                    / "skills"
                    / "PerkFactory.java"
                )
                sentinel.parent.mkdir(parents=True)
                sentinel.write_text("class PerkFactory {}", encoding="utf-8")
                return MagicMock(returncode=0)

            with self.settings(PZ_DECOMPILED_ROOT=output_parent), patch(
                "operations.decompilation.subprocess.run",
                side_effect=write_decompiled_output,
            ):
                run_decompilation(job)

            job.refresh_from_db()
            source.refresh_from_db()
            self.assertEqual(job.status, ReferenceUpdateJob.Status.UPDATED)
            self.assertEqual(source.decompiled_build_id, "777")
            self.assertTrue(old_file.exists())
            output_root = Path(source.decompiled_root)
            self.assertEqual(
                (output_root / ".tgsrr-build-id").read_text(encoding="utf-8"),
                "777\n",
            )

    @override_settings(PZ_DECOMPILATION_TIMEOUT_SECONDS=30)
    def test_invalid_decompilation_preserves_existing_reference(self):
        with TemporaryDirectory() as root:
            library = Path(root)
            install_root = library / "steamapps" / "common" / "ProjectZomboid"
            install_root.mkdir(parents=True)
            (install_root / "projectzomboid.jar").touch()
            (library / "steamapps" / "appmanifest_108600.acf").write_text(
                '"buildid" "888"', encoding="utf-8"
            )
            java = library / "java.exe"
            java.touch()
            decompiler = library / "vineflower.jar"
            decompiler.touch()
            output_parent = install_root / "decompiled"
            old_file = output_parent / "old-reference" / "old.txt"
            old_file.parent.mkdir(parents=True)
            old_file.write_text("old", encoding="utf-8")

            source = ReferenceSource.objects.get()
            source.install_root = str(install_root)
            source.java_executable = str(java)
            source.decompiler_jar = str(decompiler)
            source.save()
            job = ReferenceUpdateJob.objects.create(
                source=source,
                operation=ReferenceUpdateJob.Operation.DECOMPILE,
                status=ReferenceUpdateJob.Status.RUNNING,
            )
            with self.settings(PZ_DECOMPILED_ROOT=output_parent), patch(
                "operations.decompilation.subprocess.run"
            ) as run:
                run.return_value.returncode = 0
                run_decompilation(job)

            job.refresh_from_db()
            self.assertEqual(job.status, ReferenceUpdateJob.Status.FAILED)
            self.assertEqual(old_file.read_text(encoding="utf-8"), "old")


class SteamAuthenticationTests(TestCase):
    def setUp(self):
        self.source = ReferenceSource.objects.get()
        self.superuser = Participant.objects.create_superuser(
            email="root@example.com", nickname="Root", password="admin-password"
        )
        self.user = Participant.objects.create_user(
            email="user@example.com", nickname="User", password="user-password"
        )
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))

    def test_connection_view_requires_superuser(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "admin:operations_referencesource_connect", args=(self.source.pk,)
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_update_check_queues_an_audited_manual_job(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse(
                "admin:operations_referencesource_check_updates",
                args=(self.source.pk,),
            )
        )
        self.assertEqual(response.status_code, 302)
        job = ReferenceUpdateJob.objects.get()
        self.assertEqual(job.status, ReferenceUpdateJob.Status.QUEUED)
        self.assertEqual(job.trigger, ReferenceUpdateJob.Trigger.MANUAL)
        self.assertEqual(job.requested_by, self.superuser)

    def test_duplicate_update_check_reuses_active_job(self):
        self.client.force_login(self.superuser)
        url = reverse(
            "admin:operations_referencesource_check_updates",
            args=(self.source.pk,),
        )
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(ReferenceUpdateJob.objects.count(), 1)

    def test_decompile_action_queues_an_audited_manual_job(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse(
                "admin:operations_referencesource_decompile",
                args=(self.source.pk,),
            )
        )
        self.assertEqual(response.status_code, 302)
        job = ReferenceUpdateJob.objects.get()
        self.assertEqual(job.operation, ReferenceUpdateJob.Operation.DECOMPILE)
        self.assertEqual(job.status, ReferenceUpdateJob.Status.QUEUED)
        self.assertEqual(job.requested_by, self.superuser)

    def test_manual_pzwiki_sync_queues_latest_approved_catalogue(self):
        review = CatalogueImportReview.objects.create(
            source=self.source,
            status=CatalogueImportReview.Status.APPROVED,
            game_version="42.19",
            installed_build_id="123",
            decompiled_build_id="123",
            install_root="C:/pz",
            decompiled_root="C:/pz/decompiled",
            reviewed_by=self.superuser,
            reviewed_at=timezone.now(),
        )
        self.client.force_login(self.superuser)
        url = reverse(
            "admin:operations_referencesource_sync_pzwiki_artwork",
            args=(self.source.pk,),
        )

        page_response = self.client.get(url)
        self.assertEqual(page_response.status_code, 200)
        self.assertEqual(
            page_response.content.decode().count(
                "<h1>Sync PZWiki catalogue artwork</h1>"
            ),
            1,
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        job = PZWikiArtworkSyncJob.objects.get(catalogue_review=review)
        self.assertEqual(job.status, PZWikiArtworkSyncJob.Status.QUEUED)
        self.assertEqual(job.trigger, PZWikiArtworkSyncJob.Trigger.MANUAL)

    def test_admin_password_is_required_before_steam_is_called(self):
        self.client.force_login(self.superuser)
        with TemporaryDirectory() as root:
            executable = Path(root) / "steamcmd.exe"
            executable.touch()
            self.source.steamcmd_path = str(executable)
            self.source.save(update_fields=("steamcmd_path",))
            with patch("operations.admin.begin_authentication") as begin:
                response = self.client.post(
                    reverse(
                        "admin:operations_referencesource_connect",
                        args=(self.source.pk,),
                    ),
                    {
                        "account_name": "steam-user",
                        "steam_password": "not-persisted",
                        "admin_password": "wrong",
                    },
                )
        self.assertEqual(response.status_code, 200)
        begin.assert_not_called()

    @override_settings(STEAMCMD_AUTH_TIMEOUT_SECONDS=30)
    def test_steam_secret_is_sent_on_stdin_not_process_arguments(self):
        with TemporaryDirectory() as root:
            executable = Path(root) / "steamcmd.exe"
            executable.touch()
            process = MagicMock()
            process.stdin = io.BytesIO()
            process.stdout = io.BytesIO()
            process.poll.return_value = 0
            with patch("operations.steam_auth.os.name", "posix"), patch(
                "operations.steam_auth.subprocess.Popen", return_value=process
            ) as popen:
                attempt = steam_auth._start_session(
                    executable, "steam-user", "private-password"
                )
                written = process.stdin.getvalue()
        self.assertEqual(
            popen.call_args.args[0][0].replace("\\", "/"),
            str(executable).replace("\\", "/"),
        )
        self.assertNotIn("private-password", repr(popen.call_args.args[0]))
        self.assertIn(b"private-password", written)
        attempt.destroy()

    @override_settings(STEAMCMD_AUTH_TIMEOUT_SECONDS=1)
    def test_waiting_steam_guard_prompt_becomes_guard_step(self):
        attempt = MagicMock()
        attempt.expires_at = float("inf")
        with patch(
            "operations.steam_auth._start_session", return_value=attempt
        ), patch(
            "operations.steam_auth._wait_for_status", return_value="guard_required"
        ):
            status, token = begin_authentication(
                "steamcmd.exe", "steam-user", "private-password"
            )
        self.assertEqual(status, "guard_required")
        self.assertTrue(token)
        steam_auth._attempts.pop(token).destroy()


class CatalogueImportReviewTests(TestCase):
    def setUp(self):
        self.source = ReferenceSource.objects.get()
        self.source.install_root = "C:/pz"
        self.source.decompiled_root = "C:/pz/decompiled/build-123"
        self.source.installed_build_id = "123"
        self.source.decompiled_build_id = "123"
        self.source.save()
        self.admin = Participant.objects.create_superuser(
            email="catalogue-admin@example.com",
            nickname="CatalogueAdmin",
            password="admin-password",
        )
        self.snapshot = [{
            "kind": CatalogueEntry.Kind.SKILL,
            "stable_id": "FlintKnapping",
            "display_name": "Knapping",
            "icon_key": "perk_FlintKnapping",
            "details": {
                "description": "",
                "category": "Crafting",
                "level_xp": [75],
                "is_passive": False,
            },
            "asset": None,
        }]

    def review(self):
        return CatalogueImportReview.objects.create(
            source=self.source,
            status=CatalogueImportReview.Status.READY,
            game_version="42.19",
            installed_build_id="123",
            decompiled_build_id="123",
            install_root="C:/pz",
            decompiled_root="C:/pz/decompiled/build-123",
            snapshot=self.snapshot,
            diff={"added": [], "changed": [], "removed": []},
        )

    def test_diff_is_non_mutating(self):
        before = CatalogueEntry.objects.count()
        diff = catalogue_diff(self.snapshot, "42.19")
        self.assertEqual(CatalogueEntry.objects.count(), before)
        self.assertEqual(diff["added"][0]["display_name"], "Knapping")

    def test_approval_applies_the_reviewed_snapshot(self):
        review = approve_catalogue_review(self.review(), self.admin)
        entry = CatalogueEntry.objects.get(stable_id="FlintKnapping")
        self.assertEqual(entry.display_name, "Knapping")
        self.assertEqual(entry.skill_details.level_xp, [75])
        self.assertEqual(review.status, CatalogueImportReview.Status.APPROVED)
        self.assertEqual(review.reviewed_by, self.admin)
        job = PZWikiArtworkSyncJob.objects.get(catalogue_review=review)
        self.assertEqual(job.status, PZWikiArtworkSyncJob.Status.QUEUED)
        self.assertEqual(
            job.trigger, PZWikiArtworkSyncJob.Trigger.CATALOGUE_APPROVAL
        )

    def test_approval_resolves_item_category_and_weapon_skill_relationships(self):
        self.snapshot.extend([
            {
                "kind": CatalogueEntry.Kind.SKILL,
                "stable_id": "SmallBlunt",
                "display_name": "Small Blunt",
                "icon_key": "",
                "details": {
                    "description": "",
                    "category": "Combat",
                    "level_xp": [75],
                    "is_passive": False,
                },
                "asset": None,
            },
            {
                "kind": CatalogueEntry.Kind.ITEM,
                "stable_id": "Base.Hammer",
                "display_name": "Claw Hammer",
                "icon_key": "Hammer",
                "details": {
                    "pz_item_type": "base:weapon",
                    "display_category_stable_id": "ToolWeapon",
                    "display_category_display_name": "Tool/Weapon",
                    "tags": ["base:hammer"],
                    "capabilities": ["tool", "weapon"],
                    "weapon_categories": ["base:smallblunt"],
                    "weapon_skill_stable_id": "SmallBlunt",
                    "weight": 1.0,
                    "raw_properties": {"ItemType": "base:weapon"},
                },
                "asset": None,
            },
        ])

        approve_catalogue_review(self.review(), self.admin)

        item = CatalogueEntry.objects.get(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.Hammer",
        ).item_details
        self.assertEqual(item.display_category.stable_id, "ToolWeapon")
        self.assertEqual(item.display_category.display_name, "Tool/Weapon")
        self.assertEqual(item.weapon_skill.entry.stable_id, "SmallBlunt")

    def test_approval_preserves_an_imported_wiki_icon_for_a_packed_game_asset(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            entry = CatalogueEntry.objects.create(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id="FlintKnapping",
                display_name="Old Knapping",
                introduced_in="42.19",
            )
            SkillDetails.objects.create(entry=entry)
            asset = CatalogueAsset.objects.create(
                entry=entry,
                role=CatalogueAsset.Role.ICON,
                source_key="perk_FlintKnapping",
                availability=CatalogueAsset.Availability.IMPORTED,
                source_type=CatalogueAsset.SourceType.PZWIKI,
                source_path="https://pzwiki.net/wiki/example.png",
                alt_text="Old Knapping",
            )
            asset.file.save("knapping.png", ContentFile(b"wiki-icon"), save=True)
            self.snapshot[0]["asset"] = {
                "source_key": "perk_FlintKnapping",
                "source_path": "",
                "source_checksum": "",
                "copy_file": False,
            }

            approve_catalogue_review(self.review(), self.admin)

            asset.refresh_from_db()
            self.assertEqual(
                asset.availability,
                CatalogueAsset.Availability.IMPORTED,
            )
            self.assertTrue(asset.file)
            self.assertEqual(asset.source_type, CatalogueAsset.SourceType.PZWIKI)
            self.assertEqual(
                asset.game_availability,
                CatalogueAsset.GameAvailability.PACKED,
            )
            self.assertEqual(asset.alt_text, "Knapping")

    def test_approval_records_unpacked_game_provenance_without_replacing_wiki(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            entry = CatalogueEntry.objects.create(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id="FlintKnapping",
                display_name="Old Knapping",
                introduced_in="42.19",
            )
            SkillDetails.objects.create(entry=entry)
            asset = CatalogueAsset.objects.create(
                entry=entry,
                role=CatalogueAsset.Role.ICON,
                source_key="perk_FlintKnapping",
                availability=CatalogueAsset.Availability.IMPORTED,
                source_type=CatalogueAsset.SourceType.PZWIKI,
                source_path="https://pzwiki.net/wiki/example.png",
                alt_text="Old Knapping",
            )
            asset.file.save("wiki.png", ContentFile(b"wiki-icon"), save=True)
            game_icon = Path(media_root) / "game-icon.png"
            game_icon.write_bytes(b"unpacked-game-icon")
            checksum = hashlib.sha256(game_icon.read_bytes()).hexdigest()
            self.snapshot[0]["asset"] = {
                "source_key": "perk_FlintKnapping",
                "source_path": str(game_icon),
                "source_checksum": checksum,
                "copy_file": True,
            }

            approve_catalogue_review(self.review(), self.admin)

            asset.refresh_from_db()
            self.assertEqual(asset.source_type, CatalogueAsset.SourceType.PZWIKI)
            self.assertEqual(
                asset.game_availability,
                CatalogueAsset.GameAvailability.UNPACKED,
            )
            self.assertNotEqual(asset.source_checksum, checksum)
            self.assertEqual(asset.game_source_checksum, checksum)
            self.assertTrue(asset.file.name.endswith("wiki.png"))

    def test_approval_deactivates_records_missing_from_reviewed_source(self):
        old = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="RemovedSkill",
            display_name="Removed skill",
            introduced_in="42.19",
        )
        SkillDetails.objects.create(entry=old)
        approve_catalogue_review(self.review(), self.admin)
        old.refresh_from_db()
        self.assertFalse(old.is_active)

    def test_revert_restores_previous_snapshot_and_removes_added_items(self):
        baseline = approve_catalogue_review(self.review(), self.admin)
        replacement = self.review()
        replacement.snapshot.append(
            {
                "kind": CatalogueEntry.Kind.ITEM,
                "stable_id": "Base.Hammer",
                "display_name": "Claw Hammer",
                "icon_key": "Hammer",
                "details": {
                    "pz_item_type": "base:weapon",
                    "display_category_stable_id": "ToolWeapon",
                    "display_category_display_name": "Tool/Weapon",
                    "tags": ["base:hammer"],
                    "capabilities": ["tool", "weapon"],
                    "weapon_categories": ["base:smallblunt"],
                    "weapon_skill_stable_id": "SmallBlunt",
                    "weight": 1.0,
                    "raw_properties": {"ItemType": "base:weapon"},
                },
                "asset": None,
            }
        )
        replacement.save(update_fields=("snapshot",))
        replacement = approve_catalogue_review(replacement, self.admin)

        revert_catalogue_review(replacement, self.admin)

        replacement.refresh_from_db()
        self.assertEqual(
            replacement.status,
            CatalogueImportReview.Status.REVERTED,
        )
        self.assertFalse(
            CatalogueEntry.objects.filter(
                kind=CatalogueEntry.Kind.ITEM,
                stable_id="Base.Hammer",
            ).exists()
        )
        self.assertTrue(
            CatalogueEntry.objects.filter(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id="FlintKnapping",
            ).exists()
        )
        self.assertIn(f"#{baseline.pk}", replacement.summary)

    def test_changed_reference_marks_review_stale_without_mutation(self):
        review = self.review()
        self.source.installed_build_id = "124"
        self.source.save(update_fields=("installed_build_id",))
        approve_catalogue_review(review, self.admin)
        review.refresh_from_db()
        self.assertEqual(review.status, CatalogueImportReview.Status.STALE)
        self.assertFalse(CatalogueEntry.objects.filter(stable_id="FlintKnapping").exists())

    def test_review_page_identifies_affected_catalogue_tables(self):
        review = self.review()
        review.diff["changed"] = [{
            "kind": CatalogueEntry.Kind.SKILL,
            "stable_id": "FlintKnapping",
            "display_name": "Knapping",
            "fields": ["details"],
        }]
        review.save(update_fields=("diff",))
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin:operations_catalogueimportreview_change", args=(review.pk,))
        )

        self.assertContains(response, "Affected catalogue tables")
        self.assertContains(response, CatalogueEntry._meta.db_table)
        self.assertContains(response, SkillDetails._meta.db_table)
        self.assertContains(response, "<th>Changed</th>", html=True)
        self.assertContains(response, "1 changed")

    def test_review_page_identifies_item_details_table(self):
        review = self.review()
        review.snapshot.append(
            {
                "kind": CatalogueEntry.Kind.ITEM,
                "stable_id": "Base.Hammer",
                "display_name": "Claw Hammer",
                "icon_key": "Hammer",
                "details": {
                    "pz_item_type": "base:weapon",
                    "display_category_stable_id": "ToolWeapon",
                    "display_category_display_name": "Tool/Weapon",
                    "tags": ["base:hammer"],
                    "capabilities": ["tool", "weapon"],
                    "weapon_categories": ["base:smallblunt"],
                    "weapon_skill_stable_id": "SmallBlunt",
                    "weight": 1.0,
                    "raw_properties": {"ItemType": "base:weapon"},
                },
                "asset": None,
            }
        )
        review.save(update_fields=("snapshot",))
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin:operations_catalogueimportreview_change", args=(review.pk,))
        )

        self.assertContains(response, ItemDetails._meta.db_table)

    def test_wiki_icon_reconciliation_records_completion(self):
        review = self.review()
        review.status = CatalogueImportReview.Status.APPROVED
        review.save(update_fields=("status",))
        job = PZWikiArtworkSyncJob.objects.create(
            source=review.source,
            catalogue_review=review,
            status=PZWikiArtworkSyncJob.Status.RUNNING,
            trigger=PZWikiArtworkSyncJob.Trigger.CATALOGUE_APPROVAL,
        )

        with patch(
            "operations.management.commands.run_reference_update_worker.call_command"
        ) as command:
            def complete_sync(*args, **kwargs):
                kwargs["report_output"].append(
                    {
                        "kind": "item",
                        "stable_id": "Base.Unknown",
                        "display_name": "Unknown item",
                        "icon_key": "Unknown",
                        "expected_filename": "Unknown.png",
                        "reason": "not_found_on_pzwiki",
                    }
                )
                kwargs["stdout"].write("Imported 95 PZwiki icons.\n")

            command.side_effect = complete_sync
            run_wiki_icon_sync(job)

        job.refresh_from_db()
        self.assertEqual(job.status, PZWikiArtworkSyncJob.Status.COMPLETE)
        self.assertEqual(job.summary, "Imported 95 PZwiki icons.")
        self.assertEqual(len(job.unavailable_artwork), 1)
        self.assertEqual(
            job.unavailable_artwork[0]["reason"],
            "not_found_on_pzwiki",
        )


class SteamAuthenticationApprovalTests(TestCase):
    def test_mobile_approval_completes_without_sending_guard_code(self):
        attempt = MagicMock()
        attempt.expires_at = float("inf")
        steam_auth._attempts["approval-token"] = attempt
        with patch(
            "operations.steam_auth._wait_for_status", return_value="authenticated"
        ), patch("operations.steam_auth._write") as write:
            success = steam_auth.complete_authentication(
                "steamcmd.exe", "approval-token", "ABCDE"
            )
        self.assertTrue(success)
        write.assert_called_once_with(attempt, "quit")

    def test_mobile_approval_poll_finishes_existing_session(self):
        attempt = MagicMock()
        attempt.expires_at = float("inf")
        steam_auth._attempts["approval-token"] = attempt
        with patch(
            "operations.steam_auth._status_from_output",
            return_value="authenticated",
        ), patch("operations.steam_auth._finish") as finish:
            status = steam_auth.poll_authentication("approval-token")
        self.assertEqual(status, "authenticated")
        self.assertNotIn("approval-token", steam_auth._attempts)
        finish.assert_called_once_with(attempt)

    def test_mobile_approval_can_be_confirmed_by_cached_session(self):
        attempt = MagicMock()
        attempt.expires_at = float("inf")
        attempt.executable = "steamcmd.exe"
        attempt.account_name = "steam-user"
        attempt.next_cache_check = 0
        steam_auth._attempts["approval-token"] = attempt
        with patch(
            "operations.steam_auth._status_from_output",
            return_value="guard_required",
        ), patch(
            "operations.steam_auth._cached_session_valid", return_value=True
        ), patch("operations.steam_auth._finish") as finish:
            status = steam_auth.poll_authentication("approval-token")
        self.assertEqual(status, "authenticated")
        finish.assert_called_once_with(attempt)
