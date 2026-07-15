import re
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .admin import export_registrations, promote_to_role
from .models import AccountClosureRecord, Participant
from .tokens import create_verification_token


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        turnstile_patcher = patch(
            "registry.views.validate_turnstile", return_value=True
        )
        self.turnstile = turnstile_patcher.start()
        self.addCleanup(turnstile_patcher.stop)

    def registration_data(self, **overrides):
        data = {
            "nickname": "Spiffo Fan",
            "email": "player@example.com",
            "password": "Local-test-password-482!",
            "password_confirmation": "Local-test-password-482!",
            "accept_privacy": True,
        }
        data.update(overrides)
        return data

    def test_registration_page_loads(self):
        response = self.client.get(reverse("registry:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reserve your nickname")
        self.assertContains(
            response,
            "<title>The Great Spiffo&#x27;s Rat Race | Reserve your nickname</title>",
            html=True,
        )
        self.assertContains(response, "cf-turnstile")
        self.assertContains(response, "Already signed up?")
        self.assertContains(response, reverse("registry:login"))
        self.assertContains(response, reverse("registry:privacy"))
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'autocomplete="email"')
        self.assertContains(response, 'autocomplete="new-password"', count=2)

    def test_login_error_is_clear_without_revealing_account_state(self):
        response = self.client.post(
            reverse("registry:login"),
            {"username": "unknown@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The email or password was not recognised, or this account is not yet active.",
        )
        self.assertContains(response, reverse("registry:resend"))

    def test_draft_privacy_notice_is_public(self):
        response = self.client.get(reverse("registry:privacy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant privacy notice")
        self.assertContains(response, "Draft for development review")
        self.assertContains(response, "Sentinel Tech Ltd")
        self.assertContains(response, "thegreatspiffo@machus.co.uk")

    def test_participant_can_download_only_their_account_data(self):
        participant = Participant.objects.create_user(
            email="export@example.com",
            nickname="Export Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
            consented_at=timezone.now(),
            privacy_notice_version="draft-1",
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:download_my_data"))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(payload["participant"]["nickname"], "Export Test")
        self.assertEqual(payload["participant"]["email"], "export@example.com")
        self.assertNotContains(response, participant.password)
        self.assertNotIn("admin_notes", payload["participant"])
        self.assertNotIn("normalized_email", payload["participant"])

    def test_account_closure_requires_current_password(self):
        participant = Participant.objects.create_user(
            email="closure@example.com",
            nickname="Closure Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:account_closure"),
            {
                "current_password": "wrong-password",
                "note": "Please close this.",
                "confirm": True,
            },
        )

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "current password is incorrect")
        self.assertIsNone(participant.deletion_requested_at)

    def test_account_closure_request_enters_admin_review_queue(self):
        participant = Participant.objects.create_user(
            email="closure@example.com",
            nickname="Closure Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:account_closure"),
            {
                "current_password": "Local-test-password-482!",
                "note": "Please close this.",
                "confirm": True,
            },
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("registry:account_closure_received"))
        self.assertIsNotNone(participant.deletion_requested_at)
        self.assertEqual(participant.deletion_request_note, "Please close this.")
        self.assertTrue(participant.is_active)

    def test_registration_rejects_failed_human_verification(self):
        self.turnstile.return_value = False

        response = self.client.post(
            reverse("registry:register"), self.registration_data()
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Please complete the human verification", status_code=400
        )
        self.assertEqual(Participant.objects.count(), 0)

    @override_settings(SIGNUP_RATE_LIMIT=1)
    def test_signup_rate_limit_blocks_repeated_attempts(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(
                nickname="Another Player", email="another@example.com"
            ),
        )

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many signup attempts", status_code=429)
        self.assertEqual(Participant.objects.count(), 1)

    def test_valid_registration_creates_pending_participant(self):
        response = self.client.post(
            reverse("registry:register"), self.registration_data()
        )
        participant = Participant.objects.get()
        self.assertRedirects(response, reverse("registry:thanks"))
        self.assertEqual(participant.nickname, "Spiffo Fan")
        self.assertEqual(participant.status, Participant.Status.PENDING)
        self.assertIsNotNone(participant.verification_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(participant.email, mail.outbox[0].to)
        self.assertTrue(participant.check_password("Local-test-password-482!"))
        self.assertFalse(participant.is_active)

    def test_verification_link_marks_participant_verified(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        verification_url = re.search(
            r"http://testserver/verify/\S+", mail.outbox[0].body
        ).group(0)

        response = self.client.get(verification_url)

        participant = Participant.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email verified")
        self.assertEqual(participant.status, Participant.Status.VERIFIED)
        self.assertIsNotNone(participant.verified_at)
        self.assertTrue(participant.is_active)

    def test_verified_participant_can_login_with_email(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(reverse("registry:verify", kwargs={"token": create_verification_token(participant)}))
        self.assertTrue(self.client.login(email="player@example.com", password="Local-test-password-482!"))
        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Spiffo Fan")

    def test_account_page_shows_profile_and_controls(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.login(
            email="player@example.com", password="Local-test-password-482!"
        )

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to the Rat Race!")
        self.assertContains(response, "Spiffo Fan")
        self.assertContains(response, "player@example.com")
        self.assertContains(response, "Verified")
        self.assertContains(response, reverse("registry:password_change"))
        self.assertContains(response, "Run-update submissions will appear here")
        self.assertContains(response, reverse("registry:logout"))
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, ">Administration<")

    def test_participant_can_change_password_and_remains_logged_in(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.login(
            email="player@example.com", password="Local-test-password-482!"
        )

        response = self.client.post(
            reverse("registry:password_change"),
            {
                "old_password": "Local-test-password-482!",
                "new_password1": "Changed-local-password-951!",
                "new_password2": "Changed-local-password-951!",
            },
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("registry:password_change_done"))
        self.assertTrue(participant.check_password("Changed-local-password-951!"))
        self.assertFalse(participant.check_password("Local-test-password-482!"))
        self.assertEqual(self.client.get(reverse("registry:account")).status_code, 200)

    def test_logout_ends_participant_session(self):
        participant = Participant.objects.create_user(
            email="logout@example.com",
            nickname="Logout Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:logout"))

        self.assertRedirects(response, reverse("registry:register"))
        account_response = self.client.get(reverse("registry:account"))
        self.assertRedirects(
            account_response,
            f"{reverse('registry:login')}?next={reverse('registry:account')}",
        )

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("registry:login"))

        self.assertContains(response, "Forgot your password?")
        self.assertContains(response, reverse("registry:password_reset"))

    def test_authenticated_participant_is_redirected_away_from_auth_forms(self):
        participant = Participant.objects.create_user(
            email="signed-in@example.com",
            nickname="Signed In",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        login_response = self.client.get(reverse("registry:login"))
        signup_response = self.client.get(reverse("registry:register"))

        self.assertRedirects(login_response, reverse("registry:account"))
        self.assertRedirects(signup_response, reverse("registry:account"))

    def test_password_reset_changes_password_and_link_becomes_invalid(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        mail.outbox.clear()

        request_response = self.client.post(
            reverse("registry:password_reset"), {"email": "PLAYER@example.com"}
        )
        reset_url = re.search(
            r"http://testserver/password-reset/\S+", mail.outbox[0].body
        ).group(0)
        reset_response = self.client.post(
            reset_url,
            {
                "new_password1": "New-local-password-736!",
                "new_password2": "New-local-password-736!",
            },
        )

        participant.refresh_from_db()
        self.assertEqual(request_response.status_code, 200)
        self.assertContains(request_response, "Check your email")
        self.assertRedirects(
            reset_response, reverse("registry:password_reset_complete")
        )
        self.assertTrue(participant.check_password("New-local-password-736!"))
        self.assertFalse(participant.check_password("Local-test-password-482!"))
        reused_response = self.client.get(reset_url)
        self.assertEqual(reused_response.status_code, 400)
        self.assertContains(reused_response, "already been used", status_code=400)

    def test_password_reset_does_not_reveal_unknown_email(self):
        response = self.client.post(
            reverse("registry:password_reset"), {"email": "unknown@example.com"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If an active participant account exists")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_rejects_failed_human_verification(self):
        self.turnstile.return_value = False

        response = self.client.post(
            reverse("registry:password_reset"), {"email": "unknown@example.com"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Please complete the human verification", status_code=400
        )

    def test_promoted_participant_keeps_credentials_and_gains_staff_access(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        class AdminStub:
            def message_user(self, *args, **kwargs):
                pass

        promote_to_role(AdminStub(), None, Participant.objects.all(), "Moderator")
        participant = Participant.objects.get()
        self.assertTrue(participant.is_staff)
        self.assertTrue(participant.groups.filter(name="Moderator").exists())
        self.assertTrue(participant.check_password("Local-test-password-482!"))

    def test_staff_access_follows_staff_role_membership(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        moderator = Group.objects.create(name="Moderator")

        participant.groups.add(moderator)
        participant.refresh_from_db()
        self.assertTrue(participant.is_staff)

        participant.groups.remove(moderator)
        participant.refresh_from_db()
        self.assertFalse(participant.is_staff)

    def test_verification_link_can_be_reopened(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )
        self.client.get(verify_url)

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email verified")

    def test_invalid_verification_link_is_rejected(self):
        response = self.client.get(
            reverse("registry:verify", kwargs={"token": "not-a-valid-token"})
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "verification link is invalid", status_code=400)

    @override_settings(VERIFICATION_LINK_MAX_AGE=-1)
    def test_expired_verification_link_is_rejected(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )

        response = self.client.get(verify_url)

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "verification link has expired", status_code=400)
        self.assertEqual(participant.status, Participant.Status.PENDING)

    def test_disabled_registration_cannot_be_verified(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        participant.status = Participant.Status.DISABLED
        participant.save(update_fields=("status",))
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "registration is unavailable", status_code=403)

    def test_nickname_is_unique_ignoring_case(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(
                nickname="spiffo fan", email="another@example.com"
            ),
        )
        self.assertEqual(Participant.objects.count(), 1)
        self.assertContains(response, "nickname is already reserved")

    def test_redacted_nickname_is_reserved_for_system_use(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(nickname="Redacted"),
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "nickname is reserved by the system")

    def test_redacted_email_is_reserved_for_system_use(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(email="redacted@rat-race.invalid"),
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "email address is reserved by the system")

    def test_email_is_unique_ignoring_case(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(nickname="Another Player", email="PLAYER@example.com"),
        )
        self.assertEqual(Participant.objects.count(), 1)
        self.assertContains(response, "email address is already registered")
        self.assertContains(response, "Resend verification")
        self.assertContains(response, reverse("registry:resend"))

    def test_privacy_consent_is_required(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(accept_privacy=False),
        )
        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "must accept the privacy notice")

    def test_resend_reactivates_expired_registration(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        participant.status = Participant.Status.EXPIRED
        participant.save(update_fields=("status",))
        mail.outbox.clear()

        response = self.client.post(
            reverse("registry:resend"), {"email": "PLAYER@example.com"}
        )

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If a pending registration exists")
        self.assertEqual(participant.status, Participant.Status.PENDING)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_does_not_reveal_unknown_email(self):
        response = self.client.post(
            reverse("registry:resend"), {"email": "unknown@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If a pending registration exists")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(RESEND_EMAIL_RATE_LIMIT=1)
    def test_resend_rate_limit_blocks_repeated_email_requests(self):
        first = self.client.post(
            reverse("registry:resend"), {"email": "unknown@example.com"}
        )
        second = self.client.post(
            reverse("registry:resend"), {"email": "UNKNOWN@example.com"}
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertContains(second, "Too many requests", status_code=429)

    def test_old_pending_registration_is_expired(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        Participant.objects.filter(id=participant.id).update(
            verification_sent_at=timezone.now() - timedelta(days=8)
        )
        output = StringIO()

        call_command("expire_pending_registrations", stdout=output)

        participant.refresh_from_db()
        self.assertEqual(participant.status, Participant.Status.EXPIRED)
        self.assertIn("Expired 1 registration", output.getvalue())

    def test_admin_requires_login_and_lists_participants(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        admin_url = reverse("admin:registry_participant_changelist")
        anonymous_response = self.client.get(admin_url)
        self.assertEqual(anonymous_response.status_code, 302)

        user = get_user_model().objects.create_superuser(
            email="local-admin@example.com",
            nickname="Local Admin",
            password="test-password-only",
        )
        self.client.force_login(user)
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spiffo Fan")

    def test_admin_home_redirects_to_participants(self):
        user = get_user_model().objects.create_superuser(
            email="breadcrumb-admin@example.com",
            nickname="Breadcrumb Admin",
            password="test-password-only",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(
            response,
            reverse("admin:registry_participant_changelist"),
            fetch_redirect_response=False,
        )

    def test_challenge_admin_can_confirm_and_process_account_closure(self):
        admin_user = get_user_model().objects.create_superuser(
            email="closure-admin@example.com",
            nickname="Closure Admin",
            password="test-password-only",
        )
        closure_reference = uuid.uuid4()
        participant = Participant.objects.create_user(
            email="leaving@example.com",
            nickname="Leaving Player",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
            deletion_requested_at=timezone.now(),
            deletion_request_reference=closure_reference,
        )
        self.client.force_login(admin_user)
        admin_url = reverse("admin:registry_participant_changelist")
        selection = {
            "action": "process_account_closures",
            "_selected_action": str(participant.pk),
        }

        confirmation = self.client.post(admin_url, selection)

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Confirm account closure and redaction")
        self.assertContains(confirmation, "Leaving Player")
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())

        processed = self.client.post(admin_url, {**selection, "confirm": "yes"})

        self.assertEqual(processed.status_code, 302)
        self.assertFalse(Participant.objects.filter(pk=participant.pk).exists())
        redacted = Participant.objects.get(
            id="00000000-0000-0000-0000-000000000001"
        )
        self.assertEqual(redacted.nickname, "Redacted")
        self.assertTrue(redacted.is_system_account)
        self.assertFalse(redacted.is_active)
        self.assertFalse(redacted.has_usable_password())
        self.assertTrue(
            AccountClosureRecord.objects.filter(reference=closure_reference).exists()
        )

    def test_staff_account_is_not_eligible_for_closure_processing(self):
        admin_user = get_user_model().objects.create_superuser(
            email="closure-admin@example.com",
            nickname="Closure Admin",
            password="test-password-only",
        )
        staff_participant = Participant.objects.create_user(
            email="staff-leaving@example.com",
            nickname="Staff Leaving",
            password="Local-test-password-482!",
            is_active=True,
            is_staff=True,
            status=Participant.Status.VERIFIED,
            deletion_requested_at=timezone.now(),
            deletion_request_reference=uuid.uuid4(),
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:registry_participant_changelist"),
            {
                "action": "process_account_closures",
                "_selected_action": str(staff_participant.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No eligible account-closure requests")
        self.assertTrue(Participant.objects.filter(pk=staff_participant.pk).exists())

    def test_admin_app_landing_page_keeps_navigation_sidebar(self):
        user = get_user_model().objects.create_superuser(
            email="app-index-admin@example.com",
            nickname="App Index Admin",
            password="test-password-only",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:app_list", kwargs={"app_label": "auth"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-filter"')
        self.assertContains(response, "Participant Registry")

    def test_csv_export_contains_selected_registration(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        response = export_registrations(
            None, None, Participant.objects.all()
        )

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("nickname,email,status", content)
        self.assertIn("Spiffo Fan,player@example.com,pending", content)
