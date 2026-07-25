import asyncio
import logging
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme

from pages.models import Page

from .forms import (
    AccountClosureRequestForm,
    AgeEligibilityForm,
    AvatarUploadForm,
    PasswordResetRequestForm,
    RegistrationForm,
    ResendVerificationForm,
    SignInForm,
    RunSubmissionForm,
)
from .avatar_moderation import InvalidAvatar, remove_avatar, submit_avatar
from .models import (
    ChallengeRun,
    Notification,
    Participant,
    RunSubmission,
    StreamingAccount,
    StreamingMedia,
)
from .run_exports import InvalidRunExport, decode_run_export
from .challenge_modes import resolve_challenge_mode
from .notifications import notify
from .rate_limit import exceeded, request_ip
from .tokens import create_verification_token, read_verification_token
from .turnstile import validate_turnstile
from .streaming import (
    TwitchIntegrationError,
    apply_twitch_credentials,
    begin_twitch_authorization,
    consume_twitch_state,
    exchange_twitch_code,
    revoke_twitch_account,
    refresh_twitch_media,
    twitch_is_configured,
    validate_twitch_token,
)
from .discord_integration import (
    DiscordIntegrationError,
    apply_discord_credentials,
    begin_discord_authorization,
    consume_discord_state,
    discord_is_configured,
    exchange_discord_code,
    fetch_discord_identity,
    revoke_discord_account,
)
from .verification_email import send_password_reset_email, send_verification_email


logger = logging.getLogger(__name__)


def managed_page_queryset():
    return Page.objects.prefetch_related(
        "sections__blocks__items",
        "sections__blocks__gallery_images__image",
    )


def prepare_managed_page(page):
    if not page:
        return page
    column_counts = {
        "single": 1,
        "two": 2,
        "wide_left": 2,
        "wide_right": 2,
        "three": 3,
        "four": 4,
    }
    for section in page.sections.all():
        columns = [[] for _ in range(column_counts.get(section.layout, 1))]
        for block in section.blocks.all():
            if block.is_visible:
                columns[min(block.column, len(columns) - 1)].append(block)
        section.render_columns = columns
    return page


def home(request):
    page = managed_page_queryset().filter(slug="home", is_published=True).first()
    prepare_managed_page(page)
    return render(request, "registry/home.html", {"managed_page": page})


def page_detail(request, page_path):
    page = get_object_or_404(
        managed_page_queryset(), public_path=page_path.strip("/"), is_published=True
    )
    if page.slug == "home":
        return redirect("registry:home")
    prepare_managed_page(page)
    return render(request, "registry/page.html", {"managed_page": page})


def legacy_page(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return redirect(page.get_absolute_url(), permanent=True)


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if request.user.is_authenticated:
        return redirect("registry:account")
    form = SignInForm(request=request, data=request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("registry:account")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse("registry:account")
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"signed_in": True, "redirect": next_url})
        return redirect(next_url)
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "signed_in": False,
                "error": "The email or password was not recognised, or this account is not yet active.",
            },
            status=400,
        )
    return render(request, "registry/login.html", {"form": form, "next": next_url})


AGE_ELIGIBILITY_SESSION_KEY = "registration_age_eligibility"
AGE_ELIGIBILITY_HANDOFF_KEY = "registration_age_eligibility_handoff"
AGE_ELIGIBILITY_SESSION_SECONDS = 60 * 60


def has_current_age_eligibility(request):
    eligibility = request.session.get(AGE_ELIGIBILITY_SESSION_KEY, {})
    checked_at = eligibility.get("checked_at")
    if (
        eligibility.get("policy_version") != settings.AGE_ELIGIBILITY_POLICY_VERSION
        or not isinstance(checked_at, (int, float))
    ):
        return False
    return timezone.now().timestamp() - checked_at <= AGE_ELIGIBILITY_SESSION_SECONDS


def is_hard_refresh(request):
    cache_control = request.headers.get("Cache-Control", "").casefold()
    pragma = request.headers.get("Pragma", "").casefold()
    return (
        "no-cache" in cache_control
        or "max-age=0" in cache_control
        or "no-cache" in pragma
    )


def issue_verification(participant, request):
    verification_url = request.build_absolute_uri(
        reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )
    )
    send_verification_email(participant, verification_url)
    participant.verification_sent_at = timezone.now()
    participant.save(update_fields=("verification_sent_at",))
    return verification_url


@require_http_methods(["GET", "POST"])
def register(request):
    is_staff_theme_preview = (
        request.method == "GET"
        and request.GET.get("theme-preview")
        and request.user.is_authenticated
        and request.user.has_perm("branding.change_websitetheme")
    )
    if request.user.is_authenticated and not is_staff_theme_preview:
        return redirect("registry:account")
    if request.method == "GET":
        is_age_gate_handoff = request.session.pop(AGE_ELIGIBILITY_HANDOFF_KEY, False)
        if is_hard_refresh(request) and not is_age_gate_handoff:
            request.session.pop(AGE_ELIGIBILITY_SESSION_KEY, None)
    if request.method == "POST" and "age_gate_submission" in request.POST:
        age_form = AgeEligibilityForm(request.POST)
        if age_form.is_valid():
            request.session[AGE_ELIGIBILITY_SESSION_KEY] = {
                "checked_at": timezone.now().timestamp(),
                "policy_version": settings.AGE_ELIGIBILITY_POLICY_VERSION,
            }
            request.session[AGE_ELIGIBILITY_HANDOFF_KEY] = True
            return redirect("registry:register")
        return render(
            request,
            "registry/register.html",
            {"age_form": age_form, "show_age_gate": True},
            status=400,
        )

    age_eligible = has_current_age_eligibility(request) or bool(is_staff_theme_preview)
    if not age_eligible:
        if request.method == "POST":
            return redirect("registry:register")
        return render(
            request,
            "registry/register.html",
            {"age_form": AgeEligibilityForm(), "show_age_gate": True},
        )

    form = RegistrationForm(request.POST or None)
    status = 200
    if request.method == "POST" and exceeded(
        "signup-ip",
        request_ip(request),
        settings.SIGNUP_RATE_LIMIT,
        settings.SIGNUP_RATE_WINDOW_SECONDS,
    ):
        form.add_error(None, "Too many signup attempts. Please wait and try again.")
        status = 429
    elif request.method == "POST" and form.is_valid():
        if not validate_turnstile(
            request.POST.get("cf-turnstile-response", ""), request_ip(request)
        ):
            form.add_error(None, "Please complete the human verification and try again.")
            return render(
                request,
                "registry/register.html",
                {
                    "form": form,
                    "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
                },
                status=400,
            )
        participant = Participant.objects.create_user(
            nickname=form.cleaned_data["nickname"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            is_active=False,
            privacy_notice_acknowledged_at=timezone.now(),
            privacy_notice_version="draft-1",
            age_eligibility_confirmed_at=timezone.now(),
            age_policy_version=settings.AGE_ELIGIBILITY_POLICY_VERSION,
        )
        participant.groups.add(Group.objects.get_or_create(name="Participant")[0])
        notify(
            participant,
            title="Registration received",
            message="Your registration has been received. Verify your email address to activate your account.",
            destination=reverse("registry:account"),
        )
        verification_url = issue_verification(participant, request)
        request.session["registered_nickname"] = participant.nickname
        request.session.pop(AGE_ELIGIBILITY_SESSION_KEY, None)
        request.session.pop(AGE_ELIGIBILITY_HANDOFF_KEY, None)
        if settings.DEBUG:
            request.session["development_verification_url"] = verification_url
        return redirect("registry:thanks")
    return render(
        request,
        "registry/register.html",
        {
            "form": form,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        },
        status=status,
    )


def thanks(request):
    nickname = request.session.get("registered_nickname")
    if not nickname:
        return redirect("registry:register")
    context = {
        "nickname": nickname,
        "development_verification_url": request.session.get(
            "development_verification_url"
        ),
    }
    return render(request, "registry/thanks.html", context)


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    form = ResendVerificationForm(request.POST or None)
    development_verification_url = None
    submitted = False
    status = 200
    if request.method == "POST" and exceeded(
        "resend-ip",
        request_ip(request),
        settings.RESEND_IP_RATE_LIMIT,
        settings.RESEND_RATE_WINDOW_SECONDS,
    ):
        form.add_error(None, "Too many requests. Please wait and try again.")
        status = 429
    elif request.method == "POST" and form.is_valid() and exceeded(
        "resend-email",
        form.cleaned_data["email"],
        settings.RESEND_EMAIL_RATE_LIMIT,
        settings.RESEND_RATE_WINDOW_SECONDS,
    ):
        form.add_error(None, "Too many requests. Please wait and try again.")
        status = 429
    elif request.method == "POST" and form.is_valid():
        if not validate_turnstile(
            request.POST.get("cf-turnstile-response", ""), request_ip(request)
        ):
            form.add_error(None, "Please complete the human verification and try again.")
            status = 400
        else:
            submitted = True
            participant = Participant.objects.filter(
                normalized_email=form.cleaned_data["email"].casefold(),
                status__in=(Participant.Status.PENDING, Participant.Status.EXPIRED),
            ).first()
            if participant:
                participant.status = Participant.Status.PENDING
                participant.save(update_fields=("status",))
                verification_url = issue_verification(participant, request)
                if settings.DEBUG:
                    development_verification_url = verification_url
    return render(
        request,
        "registry/resend_verification.html",
        {
            "form": form,
            "submitted": submitted,
            "development_verification_url": development_verification_url,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        },
        status=status,
    )


def verify(request, token):
    try:
        payload = read_verification_token(token)
    except signing.SignatureExpired:
        return render(
            request,
            "registry/verification_result.html",
            {"result": "expired"},
            status=400,
        )
    except signing.BadSignature:
        return render(
            request,
            "registry/verification_result.html",
            {"result": "invalid"},
            status=400,
        )

    participant = get_object_or_404(Participant, id=payload["participant_id"])
    if participant.normalized_email != payload["email"]:
        return render(
            request,
            "registry/verification_result.html",
            {"result": "invalid"},
            status=400,
        )
    if participant.status in {
        Participant.Status.EXPIRED,
        Participant.Status.DISABLED,
        Participant.Status.REMOVED,
    }:
        return render(
            request,
            "registry/verification_result.html",
            {"result": "unavailable"},
            status=403,
        )
    if participant.status != Participant.Status.VERIFIED:
        participant.status = Participant.Status.VERIFIED
        participant.verified_at = timezone.now()
        participant.is_active = True
        participant.save(update_fields=("status", "verified_at", "is_active"))
        notify(
            participant,
            title="Account verified",
            message="Your email address has been verified and your participant account is ready.",
            destination=reverse("registry:account"),
        )

    return render(
        request,
        "registry/verification_result.html",
        {"result": "verified", "participant": participant},
    )


def account_dashboard_context(user):
    runs = user.challenge_runs.select_related("challenge_mode").prefetch_related(
        "submissions__challenge_mode"
    )
    return {
        "personal_best": runs.filter(status=ChallengeRun.Status.OFFICIAL)
            .order_by("-current_kills", "first_submitted_at")
            .first(),
        "active_runs": runs.filter(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE),
        "past_runs": runs.exclude(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE),
        "pending_submissions": user.run_submissions.filter(
            status=RunSubmission.Status.RECEIVED
        ).select_related("run", "challenge_mode"),
    }


@login_required
def account(request):
    return render(
        request,
        "registry/account.html",
        account_dashboard_context(request.user),
    )


@login_required
@require_http_methods(["GET"])
def account_dashboard_fragment(request):
    response = render(
        request,
        "registry/_account_dashboard_live.html",
        account_dashboard_context(request.user),
    )
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def submit_run(request):
    form = RunSubmissionForm(request.POST or None, participant=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            decoded = decode_run_export(form.cleaned_data["run_export"])
        except InvalidRunExport as exc:
            form.add_error("run_export", str(exc))
        else:
            challenge_mode = resolve_challenge_mode(
                decoded.challenge_id, decoded.challenge_game_mode
            )
            existing = ChallengeRun.objects.filter(run_id=decoded.run_id).first()
            if existing and existing.participant_id != request.user.id:
                form.add_error(
                    "run_export",
                    "This run is already associated with another participant account.",
                )
            elif RunSubmission.objects.filter(checksum=decoded.checksum).exists():
                form.add_error("run_export", "This exact export has already been submitted.")
            elif existing and decoded.event_sequence < existing.event_sequence:
                form.add_error(
                    "run_export",
                    "This export is older than the latest version already submitted for this run.",
                )
            elif (
                existing
                and decoded.event_sequence == existing.event_sequence
                and decoded.event_hash != existing.event_hash
            ):
                form.add_error(
                    "run_export",
                    "This export conflicts with the existing ledger for this run.",
                )
            else:
                with transaction.atomic():
                    run, _ = ChallengeRun.objects.get_or_create(
                        run_id=decoded.run_id,
                        defaults={
                            "participant": request.user,
                            "export_format": decoded.format,
                            "generated_at": decoded.generated_at,
                            "current_kills": decoded.current_kills,
                            "event_sequence": decoded.event_sequence,
                            "event_hash": decoded.event_hash,
                            "challenge_mode": challenge_mode,
                            "challenge_id": decoded.challenge_id,
                            "challenge_game_mode": decoded.challenge_game_mode,
                            "starting_challenge_mode": challenge_mode,
                            "starting_challenge_id": decoded.challenge_id,
                            "starting_challenge_game_mode": decoded.challenge_game_mode,
                        },
                    )
                    run.participant = request.user
                    if not run.approved_submission_id:
                        run.export_format = decoded.format
                        run.generated_at = decoded.generated_at
                        run.current_kills = decoded.current_kills
                        run.event_sequence = decoded.event_sequence
                        run.event_hash = decoded.event_hash
                        run.character_name = decoded.character_name
                        run.bootstrapped = decoded.bootstrapped
                        run.latest_projection = decoded.projection
                        run.latest_events = decoded.events
                        run.challenge_mode = challenge_mode
                        run.challenge_id = decoded.challenge_id
                        run.challenge_game_mode = decoded.challenge_game_mode
                        run.save()
                    selected_media = form.media_by_id.get(
                        form.cleaned_data.get("evidence_video")
                    )
                    selected_clips = [
                        form.media_by_id[value]
                        for value in form.cleaned_data.get("evidence_clips", [])
                    ]
                    RunSubmission.objects.create(
                        run=run,
                        baseline_submission=run.approved_submission,
                        submitter=request.user,
                        checksum=decoded.checksum,
                        raw_export="".join(form.cleaned_data["run_export"].split()),
                        export_format=decoded.format,
                        generated_at=decoded.generated_at,
                        current_kills=decoded.current_kills,
                        event_sequence=decoded.event_sequence,
                        event_hash=decoded.event_hash,
                        projection=decoded.projection,
                        challenge_mode=challenge_mode,
                        challenge_id=decoded.challenge_id,
                        challenge_game_mode=decoded.challenge_game_mode,
                        evidence_provider=(
                            selected_media.account.provider if selected_media else ""
                        ),
                        evidence_media_type=(
                            selected_media.kind if selected_media else ""
                        ),
                        evidence_media_id=(
                            selected_media.provider_media_id if selected_media else ""
                        ),
                        evidence_url=(
                            selected_media.canonical_url
                            if selected_media
                            else form.cleaned_data.get("manual_evidence_url", "")
                        ),
                        evidence_title=selected_media.title if selected_media else "",
                        evidence_start_seconds=form.cleaned_data.get(
                            "evidence_start_seconds"
                        ),
                        evidence_end_seconds=form.cleaned_data.get(
                            "evidence_end_seconds"
                        ),
                        evidence_clips=[
                            {
                                "provider": clip.account.provider,
                                "media_id": clip.provider_media_id,
                                "url": clip.canonical_url,
                                "title": clip.title,
                                "parent_media_id": clip.parent_media_id,
                                "vod_offset_seconds": clip.vod_offset_seconds,
                            }
                            for clip in selected_clips
                        ],
                    )
                notify(
                    request.user,
                    category=Notification.Category.SUBMISSION,
                    title="Submission received",
                    message="Your Rat Race export passed its integrity checks and is awaiting review.",
                    destination=reverse("registry:account"),
                )
                return redirect("registry:account")
    twitch_account = request.user.streaming_accounts.filter(
        provider=StreamingAccount.Provider.TWITCH,
        status=StreamingAccount.Status.CONNECTED,
    ).first()
    return render(
        request,
        "registry/submit_run.html",
        {
            "form": form,
            "twitch_account": twitch_account,
            "cached_media_count": (
                twitch_account.media.count() if twitch_account else 0
            ),
        },
    )


@login_required
def account_settings(request):
    accounts = {
        account.provider: account
        for account in request.user.streaming_accounts.all()
    }
    streaming_accounts = [
        {
            "provider": provider,
            "label": label,
            "account": accounts.get(provider),
            "configured": (
                provider == StreamingAccount.Provider.TWITCH
                and twitch_is_configured()
            )
            or (
                provider == StreamingAccount.Provider.DISCORD
                and discord_is_configured()
            ),
            "connect_url": reverse(
                "registry:connect_discord"
                if provider == StreamingAccount.Provider.DISCORD
                else "registry:connect_twitch"
                if provider == StreamingAccount.Provider.TWITCH
                else "registry:account_settings"
            ) if provider != StreamingAccount.Provider.YOUTUBE else "",
            "disconnect_url": reverse(
                "registry:disconnect_discord"
                if provider == StreamingAccount.Provider.DISCORD
                else "registry:disconnect_twitch"
                if provider == StreamingAccount.Provider.TWITCH
                else "registry:account_settings"
            ) if provider != StreamingAccount.Provider.YOUTUBE else "",
        }
        for provider, label in StreamingAccount.Provider.choices
    ]
    return render(
        request,
        "registry/account_settings.html",
        {"streaming_accounts": streaming_accounts},
    )


@login_required
def connect_twitch(request):
    try:
        return redirect(begin_twitch_authorization(request))
    except TwitchIntegrationError as exc:
        notify(
            request.user,
            title="Twitch connection unavailable",
            message=str(exc),
            destination=reverse("registry:account_settings"),
        )
        return redirect("registry:account_settings")


@login_required
def twitch_callback(request):
    try:
        consume_twitch_state(request, request.GET.get("state"))
        if request.GET.get("error"):
            raise TwitchIntegrationError("Twitch access was not granted.")
        code = request.GET.get("code")
        if not code:
            raise TwitchIntegrationError("Twitch did not return an authorization code.")
        token_data = exchange_twitch_code(code)
        identity = validate_twitch_token(token_data["access_token"])
        owner = StreamingAccount.objects.filter(
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity=identity["user_id"],
        ).exclude(participant=request.user).first()
        if owner:
            raise TwitchIntegrationError(
                "That Twitch channel is already connected to another Rat Race account."
            )
        account = StreamingAccount.objects.filter(
            participant=request.user,
            provider=StreamingAccount.Provider.TWITCH,
        ).first()
        if account is None:
            account = StreamingAccount(
                participant=request.user,
                provider=StreamingAccount.Provider.TWITCH,
                provider_identity=identity["user_id"],
                channel_identity=identity["user_id"],
                display_name=identity["login"],
                channel_url=f"https://www.twitch.tv/{identity['login']}",
            )
        with transaction.atomic():
            apply_twitch_credentials(account, token_data, identity)
    except (IntegrityError, KeyError, TwitchIntegrationError) as exc:
        if not isinstance(exc, TwitchIntegrationError):
            logger.exception("Twitch callback returned incomplete or conflicting data.")
        message = (
            str(exc)
            if isinstance(exc, TwitchIntegrationError)
            else "Twitch returned an incomplete or conflicting account response."
        )
        notify(
            request.user,
            title="Twitch was not connected",
            message=message,
            destination=reverse("registry:account_settings"),
        )
    else:
        notify(
            request.user,
            title="Twitch connected",
            message=f"Your Twitch channel, {account.display_name}, is now linked.",
            destination=reverse("registry:account_settings"),
        )
    return redirect("registry:account_settings")


@login_required
def connect_discord(request):
    try:
        return redirect(begin_discord_authorization(request))
    except DiscordIntegrationError as exc:
        notify(
            request.user,
            title="Discord connection unavailable",
            message=str(exc),
            destination=reverse("registry:account_settings"),
        )
        return redirect("registry:account_settings")


@login_required
def discord_callback(request):
    try:
        consume_discord_state(request, request.GET.get("state"))
        if request.GET.get("error"):
            raise DiscordIntegrationError("Discord access was not granted.")
        code = request.GET.get("code")
        if not code:
            raise DiscordIntegrationError(
                "Discord did not return an authorization code."
            )
        token_data = exchange_discord_code(code)
        identity = fetch_discord_identity(token_data["access_token"])
        owner = StreamingAccount.objects.filter(
            provider=StreamingAccount.Provider.DISCORD,
            provider_identity=identity["id"],
        ).exclude(participant=request.user).first()
        if owner:
            raise DiscordIntegrationError(
                "That Discord account is already connected to another Rat Race account."
            )
        account = StreamingAccount.objects.filter(
            participant=request.user,
            provider=StreamingAccount.Provider.DISCORD,
        ).first()
        if account is None:
            account = StreamingAccount(
                participant=request.user,
                provider=StreamingAccount.Provider.DISCORD,
                provider_identity=identity["id"],
                channel_identity=identity["id"],
                display_name=identity.get("global_name") or identity["username"],
                channel_url=f"https://discord.com/users/{identity['id']}",
            )
        with transaction.atomic():
            apply_discord_credentials(account, token_data, identity)
    except (IntegrityError, KeyError, DiscordIntegrationError) as exc:
        if not isinstance(exc, DiscordIntegrationError):
            logger.exception("Discord callback returned incomplete or conflicting data.")
        message = (
            str(exc)
            if isinstance(exc, DiscordIntegrationError)
            else "Discord returned an incomplete or conflicting account response."
        )
        notify(
            request.user,
            title="Discord was not connected",
            message=message,
            destination=reverse("registry:account_settings"),
        )
    else:
        notify(
            request.user,
            title="Discord connected",
            message=f"Your Discord account, {account.display_name}, is now linked.",
            destination=reverse("registry:account_settings"),
        )
    return redirect("registry:account_settings")


@login_required
@require_http_methods(["POST"])
def disconnect_discord(request):
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=StreamingAccount.Provider.DISCORD,
    )
    revoke_discord_account(account)
    account.delete()
    notify(
        request.user,
        title="Discord disconnected",
        message="Your Discord identity is no longer linked to your Rat Race account.",
        destination=reverse("registry:account_settings"),
    )
    return redirect("registry:account_settings")


@login_required
@require_http_methods(["POST"])
def disconnect_twitch(request):
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=StreamingAccount.Provider.TWITCH,
    )
    revoke_twitch_account(account)
    account.delete()
    notify(
        request.user,
        title="Twitch disconnected",
        message="Your Twitch channel is no longer linked to your Rat Race account.",
        destination=reverse("registry:account_settings"),
    )
    return redirect("registry:account_settings")


@login_required
@require_http_methods(["POST"])
def refresh_twitch_media_view(request):
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=StreamingAccount.Provider.TWITCH,
        status=StreamingAccount.Status.CONNECTED,
    )
    try:
        videos, clips = refresh_twitch_media(account)
    except TwitchIntegrationError as exc:
        if exc.status == 401:
            account.status = StreamingAccount.Status.RECONNECT_REQUIRED
            account.save(update_fields=("status",))
        notify(
            request.user,
            title="Twitch media could not be refreshed",
            message=str(exc),
            destination=reverse("registry:submit_run"),
        )
    else:
        notify(
            request.user,
            title="Twitch media refreshed",
            message=f"Found {videos} recent broadcasts and {clips} clips.",
            destination=reverse("registry:submit_run"),
        )
    return redirect("registry:submit_run")


def avatar_return_url(request):
    candidate = request.META.get("HTTP_REFERER", "")
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, request.is_secure()):
        return candidate
    return reverse("registry:account")


@login_required
@require_http_methods(["POST"])
def upload_avatar(request):
    form = AvatarUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        notify(request.user, title="Avatar not accepted", message=" ".join(form.errors.get("avatar", ["Choose a valid image."])))
        return redirect(avatar_return_url(request))
    try:
        outcome = submit_avatar(request.user, form.cleaned_data["avatar"])
    except InvalidAvatar as exc:
        form.add_error("avatar", str(exc))
        notify(request.user, title="Avatar not accepted", message=str(exc))
        return redirect(avatar_return_url(request))
    if outcome == "approved":
        notify(request.user, title="Avatar updated", message="Your new avatar has been approved and published.")
    elif outcome == "pending":
        notify(request.user, title="Avatar awaiting review", message="Your avatar is private while it waits for moderation review.")
    else:
        notify(request.user, title="Avatar not accepted", message="Your current avatar has not changed. Please choose another image.")
    return redirect(avatar_return_url(request))


@login_required
@require_http_methods(["POST"])
def delete_avatar(request):
    remove_avatar(request.user)
    return redirect(avatar_return_url(request))


@login_required
def notifications(request):
    page = Paginator(request.user.notifications.all(), 25).get_page(request.GET.get("page"))
    return render(
        request,
        "registry/notifications.html",
        {"notifications": page, "notification_page": page},
    )


def notification_summary_payload(user):
    notifications = list(user.notifications.all()[:5])
    return {
        "unread_count": user.notifications.filter(read_at__isnull=True).count(),
        "notifications": [
            {
                "id": str(notification.pk),
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "age": f"{timesince(notification.created_at, timezone.now())} ago",
                "is_read": notification.is_read,
                "open_url": reverse(
                    "registry:open_notification", args=(notification.pk,)
                ),
            }
            for notification in notifications
        ],
        "all_url": reverse("registry:notifications"),
    }


@login_required
@require_http_methods(["GET"])
def notification_summary(request):
    response = JsonResponse(notification_summary_payload(request.user))
    response["Cache-Control"] = "no-store"
    return response


async def _notification_stream_state(user_id):
    notifications = Notification.objects.filter(recipient_id=user_id)
    latest = await notifications.values("id", "created_at").afirst()
    return (
        await notifications.filter(read_at__isnull=True).acount(),
        str(latest["id"]) if latest else "",
        latest["created_at"].isoformat() if latest else "",
    )


@login_required
@require_http_methods(["GET"])
async def notification_stream(request):
    # A long-lived response would occupy a WSGI worker. Refuse the stream there
    # so the browser's ordinary polling fallback remains the safe degradation.
    if not hasattr(request, "scope"):
        response = JsonResponse(
            {"detail": "Live notifications require the ASGI application."},
            status=503,
        )
        response["Cache-Control"] = "no-store"
        return response

    user = await request.auser()
    user_id = user.pk

    async def events():
        state = await _notification_stream_state(user_id)
        yield "event: ready\ndata: {}\n\n"
        elapsed = 0
        try:
            while True:
                await asyncio.sleep(3)
                elapsed += 3
                next_state = await _notification_stream_state(user_id)
                if next_state != state:
                    state = next_state
                    yield "event: notifications-changed\ndata: {}\n\n"
                    elapsed = 0
                elif elapsed >= 18:
                    yield ": keep-alive\n\n"
                    elapsed = 0
        except asyncio.CancelledError:
            return

    response = StreamingHttpResponse(
        events(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache, no-store"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_http_methods(["GET"])
def open_notification(request, notification_id):
    notification = get_object_or_404(
        Notification, pk=notification_id, recipient=request.user
    )
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    destination = notification.destination or reverse("registry:notifications")
    if not destination.startswith("/") or destination.startswith("//"):
        destination = reverse("registry:notifications")
    return redirect(destination)


@login_required
@require_http_methods(["POST"])
def mark_notifications_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "unread_count": 0})
    next_url = request.POST.get("next", "")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("registry:notifications")


def privacy_notice(request):
    return render(request, "registry/privacy_notice.html")


@login_required
@require_http_methods(["GET"])
def download_my_data(request):
    participant = request.user
    payload = {
        "exported_at": timezone.now().isoformat(),
        "participant": {
            "id": str(participant.id),
            "nickname": participant.nickname,
            "email": participant.email,
            "status": participant.status,
            "registered_at": participant.registered_at.isoformat(),
            "verified_at": (
                participant.verified_at.isoformat()
                if participant.verified_at
                else None
            ),
            "privacy_notice_acknowledged_at": (
                participant.privacy_notice_acknowledged_at.isoformat()
                if participant.privacy_notice_acknowledged_at
                else None
            ),
            "privacy_notice_version": participant.privacy_notice_version,
            "age_eligibility_confirmed_at": (
                participant.age_eligibility_confirmed_at.isoformat()
                if participant.age_eligibility_confirmed_at
                else None
            ),
            "age_policy_version": participant.age_policy_version,
            "roles": list(
                participant.groups.order_by("name").values_list("name", flat=True)
            ),
            "connected_accounts": [
                {
                    "provider": account.provider,
                    "provider_identity": account.provider_identity,
                    "display_name": account.display_name,
                    "profile_url": account.channel_url,
                    "status": account.status,
                    "granted_scopes": account.granted_scopes,
                    "provider_metadata": account.provider_metadata,
                    "connected_at": account.connected_at.isoformat(),
                    "refreshed_at": (
                        account.refreshed_at.isoformat()
                        if account.refreshed_at
                        else None
                    ),
                }
                for account in participant.streaming_accounts.all()
            ],
            "deletion_requested_at": (
                participant.deletion_requested_at.isoformat()
                if participant.deletion_requested_at
                else None
            ),
            "notifications": [
                {
                    "id": str(notification.id),
                    "category": notification.category,
                    "title": notification.title,
                    "message": notification.message,
                    "destination": notification.destination,
                    "created_at": notification.created_at.isoformat(),
                    "read_at": notification.read_at.isoformat() if notification.read_at else None,
                }
                for notification in participant.notifications.all()
            ],
            "challenge_runs": [
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "lifecycle_status": run.lifecycle_status,
                    "character_name": run.character_name,
                    "generated_at": run.generated_at.isoformat(),
                    "current_kills": run.current_kills,
                    "event_sequence": run.event_sequence,
                    "event_hash": run.event_hash,
                    "bootstrapped": run.bootstrapped,
                    "first_submitted_at": run.first_submitted_at.isoformat(),
                    "updated_at": run.updated_at.isoformat(),
                    "submissions": [
                        {
                            "id": str(submission.id),
                            "status": submission.status,
                            "checksum": submission.checksum,
                            "generated_at": submission.generated_at.isoformat(),
                            "current_kills": submission.current_kills,
                            "event_sequence": submission.event_sequence,
                            "event_hash": submission.event_hash,
                            "submitted_at": submission.submitted_at.isoformat(),
                            "reviewed_at": (
                                submission.reviewed_at.isoformat()
                                if submission.reviewed_at
                                else None
                            ),
                        }
                        for submission in run.submissions.all()
                    ],
                }
                for run in participant.challenge_runs.prefetch_related("submissions")
            ],
        },
    }
    response = JsonResponse(payload, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = (
        'attachment; filename="rat-race-participant-data.json"'
    )
    return response


@login_required
@require_http_methods(["GET", "POST"])
def request_account_closure(request):
    if request.user.deletion_requested_at:
        return redirect("registry:account_closure_received")

    form = AccountClosureRequestForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.user.deletion_requested_at = timezone.now()
        request.user.deletion_request_reference = uuid.uuid4()
        request.user.deletion_request_note = form.cleaned_data["note"].strip()
        request.user.save(
            update_fields=(
                "deletion_requested_at",
                "deletion_request_reference",
                "deletion_request_note",
            )
        )
        return redirect("registry:account_closure_received")
    return render(request, "registry/account_closure.html", {"form": form})


@login_required
def account_closure_received(request):
    if not request.user.deletion_requested_at:
        return redirect("registry:account_closure")
    return render(request, "registry/account_closure_received.html")


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    form = PasswordResetRequestForm(request.POST or None)
    submitted = False
    development_reset_url = None
    status = 200
    if request.method == "POST" and exceeded(
        "password-reset-ip",
        request_ip(request),
        settings.PASSWORD_RESET_IP_RATE_LIMIT,
        settings.PASSWORD_RESET_RATE_WINDOW_SECONDS,
    ):
        form.add_error(None, "Too many requests. Please wait and try again.")
        status = 429
    elif request.method == "POST" and form.is_valid() and exceeded(
        "password-reset-email",
        form.cleaned_data["email"],
        settings.PASSWORD_RESET_EMAIL_RATE_LIMIT,
        settings.PASSWORD_RESET_RATE_WINDOW_SECONDS,
    ):
        form.add_error(None, "Too many requests. Please wait and try again.")
        status = 429
    elif request.method == "POST" and form.is_valid():
        if not validate_turnstile(
            request.POST.get("cf-turnstile-response", ""), request_ip(request)
        ):
            form.add_error(None, "Please complete the human verification and try again.")
            status = 400
        else:
            submitted = True
            participant = Participant.objects.filter(
                normalized_email=form.cleaned_data["email"].casefold(),
                status=Participant.Status.VERIFIED,
                is_active=True,
            ).first()
            if participant:
                uid = urlsafe_base64_encode(force_bytes(participant.pk))
                token = default_token_generator.make_token(participant)
                reset_url = request.build_absolute_uri(
                    reverse(
                        "registry:password_reset_confirm",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )
                send_password_reset_email(participant, reset_url)
                if settings.DEBUG:
                    development_reset_url = reset_url
    return render(
        request,
        "registry/password_reset_request.html",
        {
            "form": form,
            "submitted": submitted,
            "development_reset_url": development_reset_url,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        },
        status=status,
    )


@require_http_methods(["GET", "POST"])
def password_reset_confirm(request, uidb64, token):
    try:
        participant_id = urlsafe_base64_decode(uidb64).decode("utf-8")
        participant = Participant.objects.get(pk=participant_id)
    except (ValueError, UnicodeDecodeError, Participant.DoesNotExist):
        participant = None

    if participant is None or not default_token_generator.check_token(
        participant, token
    ):
        return render(
            request,
            "registry/password_reset_confirm.html",
            {"valid_link": False},
            status=400,
        )

    form = SetPasswordForm(participant, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("registry:password_reset_complete")
    return render(
        request,
        "registry/password_reset_confirm.html",
        {"valid_link": True, "form": form},
    )


def password_reset_complete(request):
    return render(request, "registry/password_reset_complete.html")
