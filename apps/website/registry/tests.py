import re
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from PIL import Image

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from branding.models import SiteBranding
from pages.models import NavigationItem, Page, PageBlock, PageSection
from .admin import export_registrations, promote_to_role
from .avatar_moderation import approve_pending_avatar, reject_pending_avatar
from .models import AccountClosureRecord, Notification, Participant, StreamingAccount
from .tokens import create_verification_token
from .streaming import TWITCH_STATE_SESSION_KEY, TwitchIntegrationError, decrypt_token


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        turnstile_patcher = patch(
            "registry.views.validate_turnstile", return_value=True
        )
        self.turnstile = turnstile_patcher.start()
        self.addCleanup(turnstile_patcher.stop)

    def registration_data(self, **overrides):
        session = self.client.session
        session["registration_age_eligibility"] = {
            "checked_at": timezone.now().timestamp(),
            "policy_version": settings.AGE_ELIGIBILITY_POLICY_VERSION,
        }
        session.save()
        data = {
            "nickname": "Spiffo Fan",
            "email": "player@example.com",
            "password": "Local-test-password-482!",
            "password_confirmation": "Local-test-password-482!",
            "acknowledge_privacy": True,
            "registration_submission": "1",
        }
        data.update(overrides)
        return data

    def test_registration_page_loads(self):
        response = self.client.get(reverse("registry:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign Up")
        self.assertContains(
            response,
            "<title>The Great Spiffo&#x27;s Rat Race | Sign Up</title>",
            html=True,
        )
        self.assertContains(response, "Please enter your date of birth")
        self.assertContains(response, "Your date of birth is not stored")
        self.assertContains(response, 'type="date"')
        self.assertNotContains(response, "cf-turnstile")
        self.assertContains(response, "Already have an account?")
        self.assertContains(response, reverse("registry:login"))
        self.assertContains(response, reverse("registry:privacy"))
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, 'data-site-menu-toggle')
        self.assertContains(response, 'aria-controls="primary-menu"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'autocomplete="bday"')
        self.assertContains(response, "data-privacy-dialog")
        self.assertContains(response, "Participant privacy notice")

    def test_eligible_date_of_birth_unlocks_single_registration_form(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": "1984-04-25"},
        )

        self.assertRedirects(response, reverse("registry:register"))
        form_page = self.client.get(reverse("registry:register"))
        self.assertContains(form_page, 'autocomplete="email"')
        self.assertContains(form_page, 'autocomplete="new-password"', count=2)
        self.assertContains(form_page, "cf-turnstile")
        self.assertContains(form_page, "Create account")
        self.assertNotContains(form_page, "I confirm that I am aged 18 or over")

    def test_age_gate_redirect_survives_inherited_refresh_header(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": "1984-04-25"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("registry:register"))

        form_page = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="max-age=0"
        )

        self.assertContains(form_page, "Create account")
        self.assertNotContains(form_page, "Please enter your date of birth")

    def test_hard_refresh_clears_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="no-cache"
        )

        self.assertContains(response, "Please enter your date of birth")
        self.assertNotIn("registration_age_eligibility", self.client.session)

    def test_control_refresh_header_clears_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="max-age=0"
        )

        self.assertContains(response, "Please enter your date of birth")
        self.assertNotIn("registration_age_eligibility", self.client.session)

    def test_ordinary_refresh_preserves_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(reverse("registry:register"))

        self.assertContains(response, "Create account")
        self.assertIn("registration_age_eligibility", self.client.session)

    def test_home_introduces_challenge_and_links_to_signup(self):
        response = self.client.get(reverse("registry:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A survival challenge measured in stories")
        self.assertContains(response, "Join The Rat Race")
        self.assertContains(response, reverse("registry:register"))

    def test_branding_controls_public_sign_in_prompt(self):
        branding = SiteBranding.current()
        branding.sign_in_prompt = "Returning Survivor?"
        branding.save(update_fields=("sign_in_prompt",))

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, "Returning Survivor?")
        self.assertContains(response, "Sign In")
        self.assertNotContains(response, 'data-registration-form')
        self.assertContains(response, "Indie Stone Terms")
        self.assertContains(response, 'target="_blank"')

    def test_published_managed_pages_render_and_join_navigation_in_order(self):
        later = Page.objects.create(
            title="Challenge rules", public_path="media/rules", is_published=True,
        )
        earlier = Page.objects.create(
            title="About the challenge", public_path="about", is_published=True,
        )
        media = NavigationItem.objects.create(label="Media", position=20)
        NavigationItem.objects.create(label="Rules", page=later, parent=media, position=10)
        NavigationItem.objects.create(label="About", page=earlier, position=10)
        section = PageSection.objects.create(page=later, name="Rules", position=0)
        PageBlock.objects.create(
            section=section, position=0, block_type=PageBlock.BlockType.TEXT,
            text_role=PageBlock.TextRole.HEADING,
            content="How the challenge works",
        )

        response = self.client.get(later.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How the challenge works")
        self.assertContains(response, "| Challenge rules")
        self.assertContains(
            response,
            f'href="{later.get_absolute_url()}" aria-current="page"',
        )
        menu = response.content.decode().split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
        earlier_url = earlier.get_absolute_url()
        later_url = later.get_absolute_url()
        self.assertLess(menu.index(earlier_url), menu.index(later_url))
        self.assertContains(response, "Media")
        self.assertContains(response, "site-nav-submenu")
        self.assertContains(response, 'class="site-nav-group-toggle"')
        self.assertContains(response, 'aria-label="Show Media menu"')

    def test_unpublished_and_non_navigation_pages_are_not_public_navigation(self):
        unpublished = Page.objects.create(
            title="Draft", public_path="draft", is_published=False,
        )
        hidden = Page.objects.create(
            title="Direct link", public_path="direct", is_published=True,
        )
        NavigationItem.objects.create(label="Draft", page=unpublished)

        response = self.client.get(reverse("registry:home"))

        self.assertNotContains(
            response, unpublished.get_absolute_url()
        )
        self.assertNotContains(response, hidden.get_absolute_url())
        self.assertEqual(
            self.client.get(unpublished.get_absolute_url()).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(hidden.get_absolute_url()).status_code,
            200,
        )

    def test_home_managed_page_address_redirects_to_site_root(self):
        response = self.client.get(reverse("registry:legacy_page", args=("home",)))
        self.assertRedirects(response, reverse("registry:home"), status_code=301)

    def test_homepage_editorial_content_comes_from_managed_page(self):
        page = Page.objects.get(slug="home")
        section = page.sections.get(position=0)
        blocks = section.blocks.all()
        changes = {
            PageBlock.TextRole.EYEBROW: "Custom small heading",
            PageBlock.TextRole.HEADING: "Custom main heading",
            PageBlock.TextRole.PARAGRAPH: "Custom homepage introduction.",
        }
        for text_role, content in changes.items():
            block = blocks.get(block_type=PageBlock.BlockType.TEXT, text_role=text_role)
            block.content = content
            block.save(update_fields=("content",))
        join_action = blocks.get(destination=PageBlock.Destination.REGISTER)
        join_action.content = "Custom join action"
        join_action.save(update_fields=("content",))
        login_action = blocks.get(destination=PageBlock.Destination.LOGIN)
        login_action.content = "Custom returning-player action"
        login_action.save(update_fields=("content",))
        account_action = blocks.get(destination=PageBlock.Destination.ACCOUNT)
        account_action.content = "Custom account action"
        account_action.save(update_fields=("content",))
        card_group = blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        items = list(card_group.items.all())
        items[0].heading = "Custom first step"
        items[0].save()
        items[1].description = "Custom second description."
        items[1].save()
        items[2].description = "Custom third description."
        items[2].save()

        response = self.client.get(reverse("registry:home"))

        for expected in (
            "Custom small heading",
            "Custom main heading",
            "Custom homepage introduction.",
            "Custom join action",
            "Custom returning-player action",
            "Custom first step",
            "Custom second description.",
            "Custom third description.",
        ):
            self.assertContains(response, expected)
        self.assertNotContains(
            response, "A survival challenge measured in stories"
        )

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
        self.assertContains(response, "Unverified registrations are deleted after 30 days")
        self.assertContains(response, "Routine security and email-delivery logs are kept for 90 days")
        self.assertContains(response, "We do not currently rely on consent")
        self.assertContains(response, "Former Rat Racer")
        self.assertContains(response, "Your UK data-protection rights")
        self.assertContains(response, "within one calendar month")
        self.assertContains(response, "https://ico.org.uk/make-a-complaint/")

    @override_settings(
        SITE_LEGAL_NAME="Configured Operator Ltd",
        SITE_COMPANY_NUMBER="12345678",
        SITE_REGISTERED_OFFICE="1 Test Street, Testville",
        SITE_PRIVACY_EMAIL="privacy@example.com",
        SITE_PUBLIC_URL="https://example.com",
        SITE_FULL_TITLE="Configured Challenge",
        SITE_SHORT_TITLE="Configured Race",
        SITE_TAGLINE="Configured tagline",
        SITE_WELCOME_MESSAGE="Configured welcome!",
        SITE_FORMER_PARTICIPANT_LABEL="Configured Former Player",
        SITE_DISCLAIMER="Configured disclaimer.",
    )
    def test_public_operator_identity_comes_from_configuration(self):
        SiteBranding.objects.all().delete()
        response = self.client.get(reverse("registry:privacy"))

        self.assertContains(response, "Configured Operator Ltd")
        self.assertContains(response, "12345678")
        self.assertContains(response, "1 Test Street, Testville")
        self.assertContains(response, "privacy@example.com")
        self.assertContains(response, "Configured Challenge")
        self.assertContains(response, "Configured tagline")
        self.assertContains(response, "Configured Former Player")
        self.assertContains(response, "Configured disclaimer.")
        self.assertNotContains(response, "Sentinel Tech Ltd")
        self.assertNotContains(response, "The Great Spiffo&#x27;s Rat Race")

    def test_database_branding_overrides_environment_defaults(self):
        SiteBranding.objects.update_or_create(
            pk=SiteBranding.SINGLETON_PK,
            defaults={
                "full_title": "Database Challenge",
                "short_title": "Database Race",
                "tagline": "Database tagline",
                "welcome_message": "Database welcome!",
                "former_participant_label": "Database Former Player",
                "disclaimer": "Database disclaimer.",
            },
        )

        response = self.client.get(reverse("registry:privacy"))

        self.assertContains(response, "Database Challenge")
        self.assertContains(response, "Database tagline")
        self.assertContains(response, "Database Former Player")
        self.assertContains(response, "Database disclaimer.")

    def test_participant_can_download_only_their_account_data(self):
        participant = Participant.objects.create_user(
            email="export@example.com",
            nickname="Export Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
            privacy_notice_acknowledged_at=timezone.now(),
            privacy_notice_version="draft-1",
            age_eligibility_confirmed_at=timezone.now(),
            age_policy_version="18-plus-v1",
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
        self.assertEqual(payload["participant"]["age_policy_version"], "18-plus-v1")
        self.assertIsNotNone(
            payload["participant"]["age_eligibility_confirmed_at"]
        )

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
        self.assertContains(response, reverse("registry:account_settings"))
        self.assertNotContains(response, reverse("registry:password_change"))
        self.assertContains(response, "Personal Best")
        self.assertContains(response, "Active Runs")
        self.assertContains(response, "Past Runs")
        self.assertContains(response, "Awaiting Review")
        self.assertContains(response, reverse("registry:logout"))
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, ">Administration<")
        self.assertNotContains(response, ">Admin Dashboard</a>")

    def test_staff_account_omits_administration_from_public_navigation(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        participant.refresh_from_db()
        participant.is_staff = True
        participant.save(update_fields=("is_staff",))
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Administration<")
        self.assertNotContains(response, "Challenge administration")
        self.assertContains(response, reverse("admin:index"))
        self.assertContains(response, ">Admin Dashboard</a>")
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'rel="noopener"')

    def test_account_settings_hub_contains_security_privacy_and_closure_actions(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account settings")
        self.assertContains(response, "player@example.com")
        self.assertContains(response, reverse("registry:password_change"))
        self.assertContains(response, reverse("registry:notifications"))
        self.assertContains(response, reverse("registry:download_my_data"))
        self.assertContains(response, reverse("registry:privacy"))
        self.assertContains(response, reverse("registry:account_closure"))
        self.assertContains(response, "Connected channels")
        self.assertContains(response, "Twitch")
        self.assertContains(response, "YouTube")
        self.assertContains(response, 'aria-current="page"')

    def test_account_settings_shows_connected_streaming_channel(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
            channel_url="https://www.twitch.tv/spiffostreams",
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertContains(response, "SpiffoStreams")
        self.assertContains(response, "Connected")
        self.assertContains(response, "https://www.twitch.tv/spiffostreams")
        self.assertContains(response, "View channel")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_account_settings_hides_disconnect_for_disconnected_channel(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
            channel_url="https://www.twitch.tv/spiffostreams",
            status=StreamingAccount.Status.DISCONNECTED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertContains(response, ">Reconnect</a>")
        self.assertNotContains(response, ">Disconnect</button>")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_twitch_connect_starts_state_protected_authorization(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:connect_twitch"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://id.twitch.tv/oauth2/authorize?"))
        self.assertIn("response_type=code", response.url)
        self.assertIn(TWITCH_STATE_SESSION_KEY, self.client.session)

    @patch("registry.views.refresh_twitch_media")
    def test_revoked_twitch_credentials_require_reconnect(self, refresh_media):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
        )
        refresh_media.side_effect = TwitchIntegrationError(
            "Twitch access has been revoked. Reconnect Twitch to restore access.",
            status=401,
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:refresh_twitch_media"))

        self.assertRedirects(response, reverse("registry:submit_run"))
        account.refresh_from_db()
        self.assertEqual(
            account.status,
            StreamingAccount.Status.RECONNECT_REQUIRED,
        )

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.views.validate_twitch_token")
    @patch("registry.views.exchange_twitch_code")
    def test_twitch_callback_links_owned_channel_and_encrypts_tokens(
        self, exchange_code, validate_token
    ):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        session = self.client.session
        session[TWITCH_STATE_SESSION_KEY] = {
            "value": "safe-state",
            "created_at": timezone.now().timestamp(),
        }
        session.save()
        exchange_code.return_value = {
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "expires_in": 3600,
            "scope": [],
        }
        validate_token.return_value = {
            "client_id": "client-id",
            "user_id": "42",
            "login": "spiffostreams",
            "expires_in": 3600,
            "scopes": None,
        }

        response = self.client.get(
            reverse("registry:twitch_callback"),
            {"code": "authorization-code", "state": "safe-state"},
        )

        self.assertRedirects(response, reverse("registry:account_settings"))
        account = StreamingAccount.objects.get(participant=participant)
        self.assertEqual(account.display_name, "spiffostreams")
        self.assertEqual(account.granted_scopes, [])
        self.assertNotIn("access-secret", account.encrypted_access_token)
        self.assertNotIn("refresh-secret", account.encrypted_refresh_token)
        self.assertEqual(decrypt_token(account.encrypted_access_token), "access-secret")
        self.assertEqual(decrypt_token(account.encrypted_refresh_token), "refresh-secret")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_twitch_callback_rejects_invalid_state_without_exchanging_code(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        with patch("registry.views.exchange_twitch_code") as exchange_code:
            response = self.client.get(
                reverse("registry:twitch_callback"),
                {"code": "authorization-code", "state": "wrong-state"},
            )

        self.assertRedirects(response, reverse("registry:account_settings"))
        exchange_code.assert_not_called()
        self.assertFalse(StreamingAccount.objects.exists())

    def test_avatar_upload_is_quarantined_when_moderation_is_not_configured(self):
        participant = Participant.objects.create_user(
            email="avatar@example.com", nickname="Avatar User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        image_buffer = BytesIO()
        Image.new("RGB", (300, 200), "orange").save(image_buffer, "PNG")
        upload = SimpleUploadedFile("avatar.png", image_buffer.getvalue(), content_type="image/png")

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(
                MEDIA_ROOT=media_root,
                AVATAR_QUARANTINE_ROOT=quarantine_root,
                OPENAI_API_KEY="",
            ):
                response = self.client.post(reverse("registry:upload_avatar"), {"avatar": upload})
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.PENDING)
                self.assertFalse(participant.avatar)
                self.assertTrue((Path(quarantine_root) / participant.avatar_review_path).is_file())

    def test_pending_replacement_keeps_approved_avatar_visible_until_approval(self):
        old_image = BytesIO()
        Image.new("RGB", (512, 512), "green").save(old_image, "WEBP")
        replacement = BytesIO()
        Image.new("RGB", (300, 300), "blue").save(replacement, "PNG")

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(
                MEDIA_ROOT=media_root,
                AVATAR_QUARANTINE_ROOT=quarantine_root,
                OPENAI_API_KEY="",
            ):
                participant = Participant.objects.create_user(
                    email="replacement-avatar@example.com", nickname="Replacement Avatar",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.APPROVED,
                )
                participant.avatar.save(
                    "existing.webp",
                    SimpleUploadedFile("existing.webp", old_image.getvalue(), content_type="image/webp"),
                )
                original_name = participant.avatar.name
                original_url = participant.avatar.url
                self.client.force_login(participant)

                response = self.client.post(
                    reverse("registry:upload_avatar"),
                    {"avatar": SimpleUploadedFile("replacement.png", replacement.getvalue(), content_type="image/png")},
                )
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.PENDING)
                self.assertEqual(participant.avatar.name, original_name)
                self.assertTrue((Path(media_root) / original_name).is_file())
                self.assertContains(self.client.get(reverse("registry:account")), original_url)

                reject_pending_avatar(participant)
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.REJECTED)
                self.assertEqual(participant.avatar.name, original_name)
                self.assertContains(self.client.get(reverse("registry:account")), original_url)

                replacement.seek(0)
                self.client.post(
                    reverse("registry:upload_avatar"),
                    {"avatar": SimpleUploadedFile("replacement.png", replacement.getvalue(), content_type="image/png")},
                )
                participant.refresh_from_db()
                self.assertTrue(approve_pending_avatar(participant))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertNotEqual(participant.avatar.name, original_name)
                self.assertFalse((Path(media_root) / original_name).exists())

    @patch("registry.avatar_moderation.moderate_avatar", return_value=("approved", "Passed automatic moderation."))
    def test_approved_avatar_is_reencoded_and_published(self, moderate):
        participant = Participant.objects.create_user(
            email="approved-avatar@example.com", nickname="Approved Avatar",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        image_buffer = BytesIO()
        Image.new("RGB", (200, 300), "green").save(image_buffer, "JPEG")
        upload = SimpleUploadedFile("avatar.jpg", image_buffer.getvalue(), content_type="image/jpeg")

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.post(reverse("registry:upload_avatar"), {"avatar": upload})
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertTrue(participant.avatar.name.endswith(".webp"))
                with Image.open(Path(media_root) / participant.avatar.name) as saved:
                    self.assertEqual(saved.size, (512, 512))
        moderate.assert_called_once()

    def test_admin_can_approve_or_decline_avatar_beside_preview(self):
        administrator = Participant.objects.create_superuser(
            email="avatar-admin@example.com", nickname="Avatar Admin",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        image_buffer = BytesIO()
        Image.new("RGB", (512, 512), "purple").save(image_buffer, "WEBP")
        image_bytes = image_buffer.getvalue()

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(MEDIA_ROOT=media_root, AVATAR_QUARANTINE_ROOT=quarantine_root):
                participant = Participant.objects.create_user(
                    email="approve-me@example.com", nickname="Approve Me",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.PENDING,
                    avatar_review_path="approve.webp",
                )
                (Path(quarantine_root) / "approve.webp").write_bytes(image_bytes)
                change_url = reverse("admin:registry_participant_change", args=(participant.pk,))
                page = self.client.get(change_url)
                self.assertContains(page, "Pending review")
                self.assertContains(page, "Approve")
                self.assertContains(page, "Decline")
                self.assertContains(page, 'name="avatar_status"')
                self.assertNotContains(page, '<select name="avatar_status"')

                response = self.client.post(reverse("admin:registry_participant_avatar_approve", args=(participant.pk,)))
                self.assertRedirects(response, change_url)
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertTrue(participant.avatar)

                declined = Participant.objects.create_user(
                    email="decline-me@example.com", nickname="Decline Me",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.PENDING,
                    avatar_review_path="decline.webp",
                )
                (Path(quarantine_root) / "decline.webp").write_bytes(image_bytes)
                response = self.client.post(reverse("admin:registry_participant_avatar_decline", args=(declined.pk,)))
                self.assertRedirects(response, reverse("admin:registry_participant_change", args=(declined.pk,)))
                declined.refresh_from_db()
                self.assertEqual(declined.avatar_status, Participant.AvatarStatus.REJECTED)
                self.assertFalse((Path(quarantine_root) / "decline.webp").exists())

    def test_account_dashboard_leaves_notifications_to_notification_menu(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        Notification.objects.create(
            recipient=participant,
            title="Submission received",
            message="Your first run update is waiting for review.",
            category=Notification.Category.SUBMISSION,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<h3>Notifications</h3>", html=True)
        self.assertContains(response, "Personal Best")
        self.assertContains(response, "Active Runs")
        self.assertContains(response, "Past Runs")
        self.assertContains(response, "Awaiting Review")
        self.assertNotContains(response, "Unread notifications")

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

        self.assertRedirects(response, reverse("registry:home"))
        account_response = self.client.get(reverse("registry:account"))
        self.assertRedirects(
            account_response,
            f"{reverse('registry:login')}?next={reverse('registry:account')}",
        )

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("registry:login"))

        self.assertContains(response, "Sign In")
        self.assertContains(response, "Don&rsquo;t have an account?")
        self.assertContains(response, "Forgot your password?")
        self.assertContains(response, reverse("registry:password_reset"))

    def test_compact_sign_in_returns_json_and_preserves_safe_destination(self):
        participant = Participant.objects.create_user(
            email="compact@example.com", nickname="Compact User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        response = self.client.post(
            reverse("registry:login"),
            {"username": participant.email, "password": "Local-test-password-482!", "next": "/account/"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"signed_in": True, "redirect": "/account/"})

    def test_compact_sign_in_rejects_invalid_credentials_without_account_disclosure(self):
        response = self.client.post(
            reverse("registry:login"),
            {"username": "unknown@example.com", "password": "incorrect"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["signed_in"])
        self.assertIn("not recognised", response.json()["error"])

    def test_registration_and_verification_create_durable_notifications(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.assertTrue(participant.notifications.filter(title="Registration received").exists())

        self.client.get(reverse("registry:verify", kwargs={"token": create_verification_token(participant)}))

        self.assertTrue(participant.notifications.filter(title="Account verified").exists())

    def test_notification_panel_history_and_read_tracking(self):
        participant = Participant.objects.create_user(
            email="notify@example.com", nickname="Notify User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        notification = Notification.objects.create(
            recipient=participant,
            category=Notification.Category.SUBMISSION,
            title="Submission received",
            message="Your submission has been received.",
            destination=reverse("registry:account"),
        )
        self.client.force_login(participant)

        account_response = self.client.get(reverse("registry:account"))
        self.assertNotContains(account_response, "<h3>Notifications</h3>", html=True)
        self.assertContains(account_response, 'class="notification-count">1</span>')
        history_response = self.client.get(reverse("registry:notifications"))
        self.assertContains(history_response, "Your submission has been received.")

        opened = self.client.get(reverse("registry:open_notification", args=(notification.pk,)))
        self.assertRedirects(opened, reverse("registry:account"))
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_participant_can_mark_all_notifications_read(self):
        participant = Participant.objects.create_user(
            email="read-all@example.com", nickname="Read All",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        Notification.objects.create(recipient=participant, title="First", message="First message")
        Notification.objects.create(recipient=participant, title="Second", message="Second message")
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:mark_notifications_read"))

        self.assertRedirects(response, reverse("registry:notifications"))
        self.assertFalse(participant.notifications.filter(read_at__isnull=True).exists())

    def test_notification_popup_can_mark_all_read_and_return_to_current_page(self):
        participant = Participant.objects.create_user(
            email="popup-read@example.com", nickname="Popup Read",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        Notification.objects.create(
            recipient=participant, title="Update", message="An update is ready."
        )
        self.client.force_login(participant)

        account_response = self.client.get(reverse("registry:account"))
        self.assertContains(account_response, "Mark all as read")
        response = self.client.post(
            reverse("registry:mark_notifications_read"),
            {"next": reverse("registry:account")},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "unread_count": 0})
        self.assertFalse(
            participant.notifications.filter(read_at__isnull=True).exists()
        )

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

    def test_former_rat_racer_nickname_is_reserved_for_anonymous_display(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(nickname="Former Rat Racer"),
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "nickname is reserved by the system")

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

    def test_password_error_reopens_security_step(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(password_confirmation="A-different-password-482!"),
        )

        self.assertContains(response, "The passwords do not match.")

    def test_privacy_notice_acknowledgement_is_required(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(acknowledge_privacy=False),
        )
        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "confirm that you have read the privacy notice")

    def test_registration_submission_requires_completed_age_gate(self):
        data = self.registration_data()
        session = self.client.session
        session.pop("registration_age_eligibility", None)
        session.save()

        response = self.client.post(
            reverse("registry:register"),
            data,
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertRedirects(response, reverse("registry:register"))

    def test_underage_date_of_birth_does_not_unlock_registration(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": timezone.now().date().isoformat()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "aged 18 or over", status_code=400)
        self.assertNotIn("registration_age_eligibility", self.client.session)

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
        self.assertContains(confirmation, "Former Rat Racer")
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())

        processed = self.client.post(admin_url, {**selection, "confirm": "yes"})

        self.assertEqual(processed.status_code, 302)
        self.assertFalse(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(
            Participant.objects.filter(
                id="00000000-0000-0000-0000-000000000001"
            ).exists()
        )
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
