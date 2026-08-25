import asyncio
import logging
import re
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.http import url_has_allowed_host_and_scheme

from pages.models import Page, PageSection

from .forms import (
    AccountClosureRequestForm,
    AgeEligibilityForm,
    AvatarUploadForm,
    PasswordResetRequestForm,
    RegistrationForm,
    ResendVerificationForm,
    SignInForm,
    LegacyRunSubmissionForm,
    RunSubmissionForm,
    ModReviewRequestForm,
    validate_registration_email,
    validate_registration_nickname,
)
from .avatar_moderation import InvalidAvatar, remove_avatar, submit_avatar
from .models import (
    ChallengeRun,
    LegacyRun,
    LegacyRunClaim,
    LegacyRunSubmission,
    ExploitRuling,
    Notification,
    Participant,
    ParticipantChallengeModeLimit,
    RunSubmission,
    StreamingAccount,
    StreamingMedia,
    WorkshopMod,
)
from .run_exports import InvalidRunExport
from .run_block_cache import attach_verified_blocks, decode_run_export_cached
from .run_public import build_public_run_context
from .steam_workshop import (
    SteamWorkshopError,
    fetch_project_zomboid_workshop_item,
    search_project_zomboid_workshop_items,
)
from .challenge_modes import resolve_challenge_mode
from .notifications import notify
from .legacy_submissions import calculate_legacy_progress
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


class SubmissionBlocked(Exception):
    """Raised when a valid export cannot enter the submission workflow."""


def effective_run_limits(participant, challenge_mode):
    override = ParticipantChallengeModeLimit.objects.filter(
        participant=participant,
        challenge_mode=challenge_mode,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).first()
    active = challenge_mode.max_active_runs_per_participant
    pending_deceased = challenge_mode.max_pending_deceased_runs_per_participant
    if override:
        if override.max_active_runs is not None:
            active = override.max_active_runs
        if override.max_pending_deceased_runs is not None:
            pending_deceased = override.max_pending_deceased_runs
    return active, pending_deceased


def submission_media_payload(form, kind):
    return [
        {
            "value": str(item.pk),
            "title": item.title or item.provider_media_id,
            "thumbnail_url": item.thumbnail_url,
            "published_at": item.published_at.isoformat() if item.published_at else "",
            "duration_seconds": item.duration_seconds,
            "provider": item.account.provider,
        }
        for item in form.media_by_id.values()
        if item.kind == kind
    ]

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
from .youtube_integration import (
    YouTubeIntegrationError,
    apply_youtube_credentials,
    begin_youtube_authorization,
    consume_youtube_state,
    exchange_youtube_code,
    fetch_google_identity,
    fetch_youtube_channel,
    refresh_youtube_media,
    revoke_youtube_account,
    youtube_is_configured,
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
        if section.section_type == PageSection.SectionType.TABS:
            section.render_tabs = [
                {"config": config, "blocks": columns[index], "index": index}
                for index, config in enumerate(section.normalised_tabs())
            ]
    return page


def home(request):
    page = get_object_or_404(
        managed_page_queryset(), slug="home", is_published=True
    )
    if not page.is_visible_to(request.user):
        raise Http404
    prepare_managed_page(page)
    return render(request, "registry/home.html", {"managed_page": page})


def page_detail(request, page_path):
    page = get_object_or_404(
        managed_page_queryset(), public_path=page_path.strip("/"), is_published=True
    )
    if not page.is_visible_to(request.user):
        raise Http404
    if page.slug == "home":
        return redirect("registry:home")
    prepare_managed_page(page)
    return render(request, "registry/page.html", {"managed_page": page})


def legacy_page(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    if not page.is_visible_to(request.user):
        raise Http404
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


@sensitive_post_parameters("value")
@never_cache
@require_http_methods(["POST"])
def validate_registration_field(request):
    if not has_current_age_eligibility(request):
        return JsonResponse({"error": "Registration eligibility has expired."}, status=403)
    if exceeded("signup-validation-ip", request_ip(request), 120, 60):
        return JsonResponse({"error": "Too many validation requests."}, status=429)

    field_name = request.POST.get("field", "")
    value = request.POST.get("value", "")
    if field_name not in {"nickname", "email", "password"}:
        return JsonResponse({"error": "Unsupported registration field."}, status=400)
    if not value:
        return JsonResponse({"valid": False, "errors": []})

    try:
        if field_name == "nickname":
            cleaned_value = RegistrationForm.base_fields["nickname"].clean(value)
            validate_registration_nickname(cleaned_value)
            message = "This nickname is available."
        elif field_name == "email":
            cleaned_value = RegistrationForm.base_fields["email"].clean(value)
            validate_registration_email(cleaned_value)
            message = "This email address is available."
        else:
            validate_password(value)
            message = "This password meets the requirements."
    except ValidationError as exc:
        return JsonResponse({"valid": False, "errors": list(exc.messages)})

    return JsonResponse({"valid": True, "errors": [], "message": message})


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
            privacy_notice_version=settings.PRIVACY_NOTICE_VERSION,
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


def _attach_profile_progress(runs, progress_cache=None):
    progress_cache = progress_cache if progress_cache is not None else {}
    prepared = list(runs)
    for run in prepared:
        if run.pk not in progress_cache:
            progress_cache[run.pk] = (
                build_public_run_context(run)["progress"]
                if run.status == ChallengeRun.Status.OFFICIAL
                and run.approved_submission_id
                else []
            )
        run.profile_progress = progress_cache[run.pk]
    return prepared


def account_dashboard_context(user):
    runs = user.challenge_runs.select_related(
        "challenge_mode", "approved_submission"
    ).prefetch_related(
        "submissions__challenge_mode"
    )
    legacy_run = user.claimed_legacy_runs.select_related(
        "current_submission", "best_submission"
    ).first()
    legacy_claim = None
    if legacy_run is None:
        legacy_claim = user.legacy_run_claims.select_related("run").first()
    legacy_dashboard_submission = None
    if legacy_run is not None:
        legacy_dashboard_submission = (
            legacy_run.current_submission
            if legacy_run.lifecycle == LegacyRun.Lifecycle.ACTIVE
            else legacy_run.best_submission
        )
    pending_legacy_submission = None
    if legacy_run is not None:
        pending_legacy_submission = legacy_run.submissions.filter(
            source=LegacyRunSubmission.Source.PARTICIPANT,
            status=LegacyRunSubmission.Status.RECEIVED,
        ).first()
    personal_best = (
        runs.filter(status=ChallengeRun.Status.OFFICIAL)
        .order_by("-current_kills", "first_submitted_at")
        .first()
    )
    progress_cache = {}
    if personal_best:
        _attach_profile_progress((personal_best,), progress_cache)
    active_runs = _attach_profile_progress(
        runs.filter(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE), progress_cache
    )
    past_runs = list(runs.exclude(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE))
    return {
        "personal_best": personal_best,
        "active_runs": active_runs,
        "past_runs": past_runs,
        "pending_submissions": user.run_submissions.filter(
            status=RunSubmission.Status.RECEIVED
        ).select_related("run", "challenge_mode"),
        "legacy_run": legacy_run,
        "legacy_claim": legacy_claim,
        "legacy_dashboard_submission": legacy_dashboard_submission,
        "pending_legacy_submission": pending_legacy_submission,
    }


@login_required
def account(request):
    context = account_dashboard_context(request.user)
    context["journey_items"] = (
        {"label": "Dashboard", "url": ""},
    )
    return render(
        request,
        "registry/account.html",
        context,
    )


@login_required
@require_http_methods(["GET"])
def participant_profile(request, participant_id):
    participant = get_object_or_404(
        Participant,
        pk=participant_id,
        status=Participant.Status.VERIFIED,
        is_active=True,
    )
    runs = participant.challenge_runs.filter(
        status=ChallengeRun.Status.OFFICIAL,
        approved_submission__isnull=False,
    ).select_related("challenge_mode", "approved_submission")
    legacy_run = participant.claimed_legacy_runs.select_related(
        "current_submission", "best_submission"
    ).first()
    legacy_submission = None
    if legacy_run is not None:
        legacy_submission = (
            legacy_run.current_submission
            if legacy_run.lifecycle == LegacyRun.Lifecycle.ACTIVE
            else legacy_run.best_submission
        )
    personal_best = runs.order_by("-current_kills", "first_submitted_at").first()
    progress_cache = {}
    if personal_best:
        _attach_profile_progress((personal_best,), progress_cache)
    active_runs = _attach_profile_progress(
        runs.filter(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE), progress_cache
    )
    past_runs = list(runs.exclude(lifecycle_status=ChallengeRun.Lifecycle.ACTIVE))
    return render(
        request,
        "registry/participant_profile.html",
        {
            "profile_participant": participant,
            "personal_best": personal_best,
            "active_runs": active_runs,
            "past_runs": past_runs,
            "legacy_run": legacy_run,
            "legacy_submission": legacy_submission,
            "journey_items": (
                {"label": "Rankings", "url": reverse("registry:leaderboard")},
                {"label": participant.nickname, "url": ""},
            ),
        },
    )


@login_required
@require_http_methods(["POST"])
def claim_legacy_run(request, run_id):
    next_url = request.POST.get("next") or reverse("registry:account")
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("registry:account")

    with transaction.atomic():
        legacy_run = get_object_or_404(
            LegacyRun.objects.select_for_update(),
            pk=run_id,
        )
        if legacy_run.claimed_participant_id:
            if legacy_run.claimed_participant_id == request.user.pk:
                messages.info(request, "This legacy run is already linked to your account.")
            else:
                messages.error(request, "This legacy run has already been claimed.")
            return redirect(next_url)

        if LegacyRun.objects.filter(claimed_participant=request.user).exclude(pk=run_id).exists():
            messages.error(request, "Your account is already linked to a legacy run.")
            return redirect(next_url)

        if LegacyRunClaim.objects.filter(
            participant=request.user,
            status__in=(LegacyRunClaim.Status.PENDING, LegacyRunClaim.Status.APPROVED),
        ).exclude(run=legacy_run).exists():
            messages.error(request, "You already have a legacy run claim awaiting review.")
            return redirect(next_url)

        claim, created = LegacyRunClaim.objects.get_or_create(
            run=legacy_run,
            participant=request.user,
            defaults={"status": LegacyRunClaim.Status.PENDING},
        )
        if created:
            messages.success(request, "Your legacy run claim has been submitted for review.")
        elif claim.status == LegacyRunClaim.Status.PENDING:
            messages.info(request, "Your claim for this legacy run is already awaiting review.")
        elif claim.status == LegacyRunClaim.Status.APPROVED:
            messages.info(request, "This legacy run is already linked to your account.")
        else:
            messages.error(
                request,
                "This legacy run claim was declined. Contact the team if it should be reconsidered.",
            )

    return redirect(next_url)


@login_required
@require_http_methods(["GET"])
def public_run_detail(request, run_id):
    run = get_object_or_404(
        ChallengeRun.objects.select_related(
            "participant", "challenge_mode", "approved_submission"
        ),
        pk=run_id,
        status=ChallengeRun.Status.OFFICIAL,
        approved_submission__isnull=False,
    )
    context = build_public_run_context(run)
    profile_url = reverse("registry:participant_profile", args=(run.participant_id,))
    context.update({
        "participant_profile_url": profile_url,
        "journey_items": (
            {"label": "Rankings", "url": reverse("registry:leaderboard")},
            {"label": run.participant.nickname, "url": profile_url},
            {"label": run.character_name or "Rat Race survivor", "url": ""},
        ),
    })
    return render(request, "registry/public_run_detail.html", context)


@require_http_methods(["GET"])
def leaderboard(request):
    return page_detail(request, "leaderboard")


@require_http_methods(["GET", "POST"])
def mods_catalogue(request):
    form = ModReviewRequestForm(request.POST or None)
    open_submission_modal = request.method == "POST"
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('registry:login')}?next={reverse('registry:mods')}")
        if form.is_valid():
            workshop_id = form.cleaned_data["workshop_id"]
            existing = WorkshopMod.objects.filter(workshop_id=workshop_id).first()
            if existing:
                form.add_error(
                    "workshop_id",
                    f"This mod is already {existing.get_ruling_display()}.",
                )
            else:
                try:
                    steam_item = fetch_project_zomboid_workshop_item(workshop_id)
                except SteamWorkshopError as exc:
                    form.add_error("workshop_id", str(exc))
                else:
                    try:
                        WorkshopMod.objects.create(
                            **steam_item,
                            ruling=WorkshopMod.Ruling.PENDING,
                            submission_reason=form.cleaned_data["reason"],
                            submitted_by=request.user,
                            steam_checked_at=timezone.now(),
                        )
                    except IntegrityError:
                        form.add_error(
                            "workshop_id",
                            "This mod has already been submitted for review.",
                        )
                    else:
                        messages.success(request, "Mod submitted for team review.")
                        return redirect("registry:mods")

    query = request.GET.get("q", "").strip()[:100]
    ruling = request.GET.get("ruling", "all")
    view_mode = request.GET.get("view", "cards")
    if view_mode not in {"cards", "list"}:
        view_mode = "cards"
    if ruling not in {"all", WorkshopMod.Ruling.ALLOWED, WorkshopMod.Ruling.DISALLOWED}:
        ruling = "all"
    mods = WorkshopMod.objects.filter(
        ruling__in=(WorkshopMod.Ruling.ALLOWED, WorkshopMod.Ruling.DISALLOWED)
    )
    if ruling != "all":
        mods = mods.filter(ruling=ruling)
    if query:
        mods = mods.filter(Q(title__icontains=query) | Q(workshop_id__icontains=query))
    recommended_mods = mods.filter(is_recommended=True)
    mods = mods.filter(is_recommended=False)
    return render(
        request,
        "registry/mods.html",
        {
            "required_mods": WorkshopMod.objects.filter(
                ruling=WorkshopMod.Ruling.REQUIRED
            ),
            "recommended_mods": recommended_mods,
            "mods": mods,
            "query": query,
            "selected_ruling": ruling,
            "view_mode": view_mode,
            "submission_form": form,
            "open_submission_modal": open_submission_modal,
        },
    )


@require_http_methods(["GET"])
def exploits_catalogue(request):
    rulings = ExploitRuling.objects.filter(is_published=True).prefetch_related(
        "example_images__image"
    )
    return render(
        request,
        "registry/exploits.html",
        {"exploit_rulings": rulings},
    )


@login_required
@never_cache
@require_http_methods(["GET"])
def workshop_mod_lookup(request):
    if exceeded(
        "workshop-search-ip",
        request_ip(request),
        30,
        60,
    ):
        return JsonResponse(
            {"error": "Too many Workshop searches. Please wait and try again."},
            status=429,
        )
    query = request.GET.get("q", "").strip()[:200]
    match = re.search(r"(?:[?&]id=)?([0-9]{6,20})(?:\D|$)", query)
    exact_id = match.group(1) if match and (query.isdigit() or "steamcommunity.com" in query) else ""
    try:
        items = (
            [fetch_project_zomboid_workshop_item(exact_id)]
            if exact_id
            else search_project_zomboid_workshop_items(query)
            if len(query) >= 3
            else []
        )
    except SteamWorkshopError as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    existing = {
        mod.workshop_id: mod
        for mod in WorkshopMod.objects.filter(
            workshop_id__in=[item["workshop_id"] for item in items]
        )
    }
    results = []
    for item in items:
        mod = existing.get(item["workshop_id"])
        results.append(
            {
                **item,
                "existing": bool(mod),
                "ruling": mod.get_ruling_display() if mod else "",
            }
        )
    return JsonResponse({"results": results})


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
    connected_streaming_accounts = list(
        request.user.streaming_accounts.filter(
            status=StreamingAccount.Status.CONNECTED,
            provider__in=(
                StreamingAccount.Provider.TWITCH,
                StreamingAccount.Provider.YOUTUBE,
            ),
        ).order_by("provider")
    )
    primary = request.user.primary_streaming_account
    selected_provider = (
        primary.provider
        if primary in connected_streaming_accounts
        else connected_streaming_accounts[0].provider if connected_streaming_accounts else ""
    )
    form = RunSubmissionForm(
        request.POST or None,
        participant=request.user,
        selected_provider=selected_provider,
    )
    submission_videos = [
        item
        for item in form.media_by_id.values()
        if item.kind == StreamingMedia.Kind.VIDEO
    ]
    submission_clips = [
        item
        for item in form.media_by_id.values()
        if item.kind == StreamingMedia.Kind.CLIP
    ]
    selected_video_id = str(form["evidence_video"].value() or "")
    selected_clip_ids = {
        str(value) for value in (form["evidence_clips"].value() or [])
    }
    submission_blocked_message = ""
    submission_blocked_run = None
    if request.method == "POST" and form.is_valid():
        try:
            decoded = decode_run_export_cached(form.cleaned_data["run_export"])
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
            elif existing and existing.participant_deactivated_at:
                submission_blocked_message = (
                    "This run was deactivated and cannot receive further updates. "
                    "Start a new character to submit another run."
                )
                form.add_error(None, submission_blocked_message)
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
                try:
                    with transaction.atomic():
                        Participant.objects.select_for_update().get(pk=request.user.pk)
                        locked_existing = (
                            ChallengeRun.objects.select_for_update()
                            .filter(run_id=decoded.run_id)
                            .first()
                        )
                        if locked_existing and locked_existing.participant_deactivated_at:
                            raise SubmissionBlocked(
                                "This run was deactivated and cannot receive further updates. "
                                "Start a new character to submit another run."
                            )
                        reported_lifecycle = decoded.lifecycle
                        if challenge_mode:
                            active_limit, deceased_limit = effective_run_limits(
                                request.user, challenge_mode
                            )
                            active_runs = ChallengeRun.objects.select_for_update().filter(
                                participant=request.user,
                                challenge_mode=challenge_mode,
                                reported_lifecycle_status=ChallengeRun.Lifecycle.ACTIVE,
                            )
                            if locked_existing:
                                active_runs = active_runs.exclude(pk=locked_existing.pk)
                            active_count = active_runs.count()
                            if reported_lifecycle == ChallengeRun.Lifecycle.ACTIVE and active_count >= active_limit:
                                submission_blocked_run = (
                                    active_runs.select_related("challenge_mode")
                                    .prefetch_related("submissions__challenge_mode")
                                    .order_by("first_submitted_at", "pk")
                                    .first()
                                )
                                noun = "run" if active_limit == 1 else "runs"
                                raise SubmissionBlocked(
                                    f"You already have the maximum of {active_limit} active {noun} "
                                    f"for {challenge_mode.display_name}. Deactivate an existing "
                                    "run before submitting a new character."
                                )
                            adds_pending_deceased = (
                                reported_lifecycle == ChallengeRun.Lifecycle.DECEASED
                                and (not locked_existing or locked_existing.reported_lifecycle_status != ChallengeRun.Lifecycle.DECEASED)
                            )
                            if adds_pending_deceased and deceased_limit is not None:
                                pending_deceased = ChallengeRun.objects.filter(
                                    participant=request.user,
                                    challenge_mode=challenge_mode,
                                    reported_lifecycle_status=ChallengeRun.Lifecycle.DECEASED,
                                    submissions__status=RunSubmission.Status.RECEIVED,
                                ).distinct().count()
                                if pending_deceased >= deceased_limit:
                                    raise SubmissionBlocked(
                                        f"You already have the maximum of {deceased_limit} pending deceased runs for {challenge_mode.display_name}."
                                    )
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
                                "reported_lifecycle_status": reported_lifecycle,
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
                            run.reported_lifecycle_status = reported_lifecycle
                            run.save()
                        elif run.reported_lifecycle_status != reported_lifecycle:
                            run.reported_lifecycle_status = reported_lifecycle
                            run.save(update_fields=("reported_lifecycle_status", "updated_at"))
                        selected_media = form.media_by_id.get(
                            form.cleaned_data.get("evidence_video")
                        )
                        selected_clips = [
                            form.media_by_id[value]
                            for value in form.cleaned_data.get("evidence_clips", [])
                        ]
                        submission = RunSubmission.objects.create(
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
                            reported_lifecycle_status=reported_lifecycle,
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
                        attach_verified_blocks(submission, decoded)
                except SubmissionBlocked as exc:
                    submission_blocked_message = str(exc)
                    form.add_error(None, submission_blocked_message)
                else:
                    notify(
                        request.user,
                        category=Notification.Category.SUBMISSION,
                        title="Submission received",
                        message="Your Rat Race export passed its integrity checks and is awaiting review.",
                        destination=reverse("registry:account"),
                    )
                    return redirect("registry:account")
    return render(
        request,
        "registry/submit_run.html",
        {
            "form": form,
            "streaming_accounts": connected_streaming_accounts,
            "selected_provider": form.selected_provider,
            "cached_media_count": (
                sum(
                    account.media.filter(kind=StreamingMedia.Kind.VIDEO).count()
                    for account in connected_streaming_accounts
                    if account.provider == form.selected_provider
                )
            ),
            "submission_blocked_message": submission_blocked_message,
            "submission_blocked_run": submission_blocked_run,
            "submission_videos": submission_videos,
            "submission_clips": submission_clips,
            "selected_video_id": selected_video_id,
            "selected_clip_ids": selected_clip_ids,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def submit_legacy_run(request):
    legacy_run = request.user.claimed_legacy_runs.select_related(
        "current_submission", "best_submission"
    ).first()
    if legacy_run is None:
        messages.error(request, "An approved legacy run claim is required before submitting an update.")
        return redirect("registry:account")
    if legacy_run.lifecycle != LegacyRun.Lifecycle.ACTIVE:
        messages.error(request, "Only an Active legacy run can receive participant updates.")
        return redirect("registry:account")
    if LegacyRunSubmission.objects.filter(
        run=legacy_run,
        source=LegacyRunSubmission.Source.PARTICIPANT,
        status=LegacyRunSubmission.Status.RECEIVED,
    ).exists():
        messages.info(request, "Your legacy run already has an update awaiting review.")
        return redirect("registry:account")

    connected_streaming_accounts = list(
        request.user.streaming_accounts.filter(
            status=StreamingAccount.Status.CONNECTED,
            provider__in=(StreamingAccount.Provider.TWITCH, StreamingAccount.Provider.YOUTUBE),
        ).order_by("provider")
    )
    primary = request.user.primary_streaming_account
    selected_provider = (
        primary.provider
        if primary in connected_streaming_accounts
        else connected_streaming_accounts[0].provider if connected_streaming_accounts else ""
    )
    form = LegacyRunSubmissionForm(
        request.POST or None,
        participant=request.user,
        selected_provider=selected_provider,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked_run = LegacyRun.objects.select_for_update().get(pk=legacy_run.pk)
            if locked_run.claimed_participant_id != request.user.pk:
                raise Http404
            if locked_run.lifecycle != LegacyRun.Lifecycle.ACTIVE:
                form.add_error(None, "This legacy run is no longer Active.")
            elif LegacyRunSubmission.objects.filter(
                run=locked_run,
                source=LegacyRunSubmission.Source.PARTICIPANT,
                status=LegacyRunSubmission.Status.RECEIVED,
            ).exists():
                form.add_error(None, "An update for this legacy run is already awaiting review.")
            else:
                selected_media = form.media_by_id.get(form.cleaned_data.get("evidence_video"))
                LegacyRunSubmission.objects.create(
                    run=locked_run,
                    status=LegacyRunSubmission.Status.RECEIVED,
                    source=LegacyRunSubmission.Source.PARTICIPANT,
                    character_name=form.cleaned_data["character_name"],
                    zombie_kills=form.cleaned_data["zombie_kills"],
                    survival_time_input=form.cleaned_data["survival_time"],
                    survival_time_full=form.normalized_survival_time,
                    survival_days=form.survival_days,
                    outposts_cleared=form.cleaned_data["outposts_cleared"],
                    maxed_skills=form.cleaned_data["maxed_skills"],
                    challenge_progress=calculate_legacy_progress(
                        form.cleaned_data["zombie_kills"],
                        form.cleaned_data["outposts_cleared"],
                        form.cleaned_data["maxed_skills"],
                    ),
                    reports_death=form.cleaned_data["run_state"] == "dead",
                    submitted_by=request.user,
                    evidence_provider=selected_media.account.provider if selected_media else "",
                    evidence_media_type=selected_media.kind if selected_media else "",
                    evidence_media_id=selected_media.provider_media_id if selected_media else "",
                    evidence_url=(selected_media.canonical_url if selected_media else form.cleaned_data.get("manual_evidence_url", "")),
                    evidence_title=selected_media.title if selected_media else "",
                    evidence_start_seconds=form.cleaned_data.get("evidence_start_seconds"),
                    evidence_end_seconds=form.cleaned_data.get("evidence_end_seconds"),
                )
                notify(
                    request.user,
                    category=Notification.Category.SUBMISSION,
                    title="Legacy update received",
                    message="Your legacy Rat Race update is awaiting moderator review.",
                    destination=reverse("registry:account"),
                )
                messages.success(request, "Your legacy run update has been submitted for review.")
                return redirect("registry:account")

    return render(request, "registry/submit_legacy_run.html", {
        "form": form,
        "legacy_run": legacy_run,
        "streaming_accounts": connected_streaming_accounts,
        "selected_provider": form.selected_provider,
        "cached_media_count": sum(
            account.media.filter(kind=StreamingMedia.Kind.VIDEO).count()
            for account in connected_streaming_accounts
            if account.provider == form.selected_provider
        ),
    })


@login_required
@require_http_methods(["POST"])
def deactivate_run(request, run_id):
    return_to_submission = request.POST.get("return_to_submission") == "1"
    wants_json = "application/json" in request.headers.get("Accept", "")
    if request.POST.get("confirm_deactivation") != "deactivate":
        if wants_json:
            return JsonResponse(
                {"ok": False, "message": "Run deactivation was not confirmed."},
                status=400,
            )
        messages.error(request, "Run deactivation was not confirmed.")
        return redirect("registry:account")

    with transaction.atomic():
        run = get_object_or_404(
            ChallengeRun.objects.select_for_update(),
            pk=run_id,
            participant=request.user,
        )
        if run.participant_deactivated_at:
            if wants_json:
                return JsonResponse(
                    {"ok": False, "message": "This run has already been deactivated."},
                    status=409,
                )
            messages.info(request, "This run has already been deactivated.")
            return redirect("registry:account")
        if run.lifecycle_status != ChallengeRun.Lifecycle.ACTIVE:
            if wants_json:
                return JsonResponse(
                    {"ok": False, "message": "Only an active run can be deactivated."},
                    status=409,
                )
            messages.error(request, "Only an active run can be deactivated.")
            return redirect("registry:account")

        deactivated_at = timezone.now()
        run.lifecycle_status = ChallengeRun.Lifecycle.ABANDONED
        run.reported_lifecycle_status = ChallengeRun.Lifecycle.ABANDONED
        run.participant_deactivated_at = deactivated_at
        run.save(update_fields=(
            "lifecycle_status", "reported_lifecycle_status",
            "participant_deactivated_at", "updated_at"
        ))
        run.submissions.filter(status=RunSubmission.Status.RECEIVED).update(
            status=RunSubmission.Status.DECLINED,
            reviewed_at=deactivated_at,
            review_note="Run deactivated by participant.",
        )

    if wants_json:
        return JsonResponse(
            {
                "ok": True,
                "message": "The active run was deactivated. You can now submit this character.",
            }
        )
    messages.success(request, "The run has been permanently deactivated.")
    if return_to_submission:
        return redirect("registry:submit_run")
    return redirect("registry:account")


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
            )
            or (
                provider == StreamingAccount.Provider.YOUTUBE
                and youtube_is_configured()
            ),
            "connect_url": reverse(
                "registry:connect_discord"
                if provider == StreamingAccount.Provider.DISCORD
                else "registry:connect_twitch"
                if provider == StreamingAccount.Provider.TWITCH
                else "registry:connect_youtube"
            ),
            "disconnect_url": reverse(
                "registry:disconnect_discord"
                if provider == StreamingAccount.Provider.DISCORD
                else "registry:disconnect_twitch"
                if provider == StreamingAccount.Provider.TWITCH
                else "registry:disconnect_youtube"
            ),
            "can_be_primary": provider in (
                StreamingAccount.Provider.TWITCH,
                StreamingAccount.Provider.YOUTUBE,
            ),
            "is_primary": bool(
                accounts.get(provider)
                and request.user.primary_streaming_account_id
                == accounts[provider].id
            ),
        }
        for provider, label in StreamingAccount.Provider.choices
    ]
    return render(
        request,
        "registry/account_settings.html",
        {
            "streaming_accounts": streaming_accounts,
            "journey_items": (
                {"label": "Dashboard", "url": reverse("registry:account")},
                {"label": "Settings", "url": ""},
            ),
        },
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
def connect_youtube(request):
    try:
        return redirect(begin_youtube_authorization(request))
    except YouTubeIntegrationError as exc:
        notify(
            request.user,
            title="YouTube connection unavailable",
            message=str(exc),
            destination=reverse("registry:account_settings"),
        )
        return redirect("registry:account_settings")


@login_required
def youtube_callback(request):
    try:
        consume_youtube_state(request, request.GET.get("state"))
        if request.GET.get("error"):
            raise YouTubeIntegrationError("YouTube access was not granted.")
        code = request.GET.get("code")
        if not code:
            raise YouTubeIntegrationError(
                "YouTube did not return an authorization code."
            )
        token_data = exchange_youtube_code(code)
        identity = fetch_google_identity(token_data["access_token"])
        channel = fetch_youtube_channel(token_data["access_token"])
        owner = StreamingAccount.objects.filter(
            Q(provider_identity=identity["sub"])
            | Q(channel_identity=channel["id"]),
            provider=StreamingAccount.Provider.YOUTUBE,
        ).exclude(participant=request.user).first()
        if owner:
            raise YouTubeIntegrationError(
                "That YouTube channel is already connected to another Rat Race account."
            )
        account = StreamingAccount.objects.filter(
            participant=request.user,
            provider=StreamingAccount.Provider.YOUTUBE,
        ).first()
        if account is None:
            account = StreamingAccount(
                participant=request.user,
                provider=StreamingAccount.Provider.YOUTUBE,
                provider_identity=identity["sub"],
                channel_identity=channel["id"],
                display_name=channel["snippet"]["title"],
                channel_url=f"https://www.youtube.com/channel/{channel['id']}",
            )
        with transaction.atomic():
            apply_youtube_credentials(account, token_data, identity, channel)
    except (IntegrityError, KeyError, YouTubeIntegrationError) as exc:
        if not isinstance(exc, YouTubeIntegrationError):
            logger.exception("YouTube callback returned incomplete or conflicting data.")
        message = (
            str(exc)
            if isinstance(exc, YouTubeIntegrationError)
            else "YouTube returned an incomplete or conflicting account response."
        )
        notify(
            request.user,
            title="YouTube was not connected",
            message=message,
            destination=reverse("registry:account_settings"),
        )
    else:
        notify(
            request.user,
            title="YouTube connected",
            message=f"Your YouTube channel, {account.display_name}, is now linked.",
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
def disconnect_youtube(request):
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=StreamingAccount.Provider.YOUTUBE,
    )
    revoke_youtube_account(account)
    account.delete()
    notify(
        request.user,
        title="YouTube disconnected",
        message="Your YouTube channel is no longer linked to your Rat Race account.",
        destination=reverse("registry:account_settings"),
    )
    return redirect("registry:account_settings")


@login_required
@require_http_methods(["POST"])
def set_primary_streaming_channel(request):
    account_id = request.POST.get("account_id", "").strip()
    if not account_id:
        request.user.primary_streaming_account = None
        request.user.save(update_fields=("primary_streaming_account",))
        notify(
            request.user,
            title="Primary channel cleared",
            message="No streaming channel will be shown on public rankings.",
            destination=reverse("registry:account_settings"),
        )
        return redirect("registry:account_settings")
    account = get_object_or_404(
        StreamingAccount,
        id=account_id,
        participant=request.user,
        provider__in=(
            StreamingAccount.Provider.TWITCH,
            StreamingAccount.Provider.YOUTUBE,
        ),
        status=StreamingAccount.Status.CONNECTED,
    )
    request.user.primary_streaming_account = account
    request.user.save(update_fields=("primary_streaming_account",))
    notify(
        request.user,
        title="Primary channel updated",
        message=f"{account.display_name} will be shown on public rankings.",
        destination=reverse("registry:account_settings"),
    )
    return redirect("registry:account_settings")


@login_required
@require_http_methods(["POST"])
def refresh_twitch_media_view(request):
    asynchronous = request.headers.get("x-requested-with") == "XMLHttpRequest"
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=StreamingAccount.Provider.TWITCH,
        status=StreamingAccount.Status.CONNECTED,
    )
    try:
        videos, clips = refresh_twitch_media(account)
    except ImproperlyConfigured:
        message = "The Twitch connection is temporarily unavailable."
        if asynchronous:
            return JsonResponse({"ok": False, "message": message}, status=503)
        notify(
            request.user,
            title="Twitch media could not be refreshed",
            message=message,
            destination=reverse("registry:submit_run"),
        )
    except TwitchIntegrationError as exc:
        if exc.status == 401:
            account.status = StreamingAccount.Status.RECONNECT_REQUIRED
            account.save(update_fields=("status",))
            Participant.objects.filter(
                pk=request.user.pk,
                primary_streaming_account=account,
            ).update(primary_streaming_account=None)
        if asynchronous:
            return JsonResponse({"ok": False, "message": str(exc)}, status=502)
        notify(
            request.user,
            title="Twitch media could not be refreshed",
            message=str(exc),
            destination=reverse("registry:submit_run"),
        )
    else:
        message = f"Found {videos} recent broadcasts and {clips} clips."
        if asynchronous:
            form = RunSubmissionForm(participant=request.user)
            return JsonResponse(
                {
                    "ok": True,
                    "message": message,
                    "videos": [
                        {"value": value, "label": label}
                        for value, label in form.fields["evidence_video"].choices
                    ],
                    "clips": [
                        {"value": value, "label": label}
                        for value, label in form.fields["evidence_clips"].choices
                    ],
                }
            )
        notify(
            request.user,
            title="Twitch media refreshed",
            message=message,
            destination=reverse("registry:submit_run"),
        )
    return redirect("registry:submit_run")


@login_required
@require_http_methods(["POST"])
def refresh_streaming_media_view(request):
    provider = request.POST.get("provider", "")
    if provider not in {
        StreamingAccount.Provider.TWITCH,
        StreamingAccount.Provider.YOUTUBE,
    }:
        return JsonResponse({"ok": False, "message": "Choose a connected streaming channel."}, status=400)
    account = get_object_or_404(
        StreamingAccount,
        participant=request.user,
        provider=provider,
        status=StreamingAccount.Status.CONNECTED,
    )
    try:
        if provider == StreamingAccount.Provider.TWITCH:
            video_count, clip_count = refresh_twitch_media(account)
            label = "Twitch"
        else:
            video_count, clip_count = refresh_youtube_media(account)
            label = "YouTube"
    except (ImproperlyConfigured, TwitchIntegrationError, YouTubeIntegrationError) as exc:
        if getattr(exc, "status", None) == 401:
            account.status = StreamingAccount.Status.RECONNECT_REQUIRED
            account.save(update_fields=("status",))
            Participant.objects.filter(
                pk=request.user.pk,
                primary_streaming_account=account,
            ).update(primary_streaming_account=None)
        message = str(exc) if not isinstance(exc, ImproperlyConfigured) else f"{account.get_provider_display()} is temporarily unavailable."
        return JsonResponse({"ok": False, "message": message}, status=502)

    form = RunSubmissionForm(
        participant=request.user,
        selected_provider=provider,
    )
    clip_suffix = f" and {clip_count} clips" if provider == StreamingAccount.Provider.TWITCH else ""
    return JsonResponse(
        {
            "ok": True,
            "provider": provider,
            "message": f"Found {video_count} recent {label} videos{clip_suffix}.",
            "videos": [
                {"value": "", "title": "Choose a broadcast or video"},
                *submission_media_payload(form, StreamingMedia.Kind.VIDEO),
            ],
            "clips": submission_media_payload(form, StreamingMedia.Kind.CLIP),
        }
    )


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
    notification_filter = request.GET.get("filter", "all")
    if notification_filter not in {"all", "unread"}:
        notification_filter = "all"
    notification_queryset = request.user.notifications.all()
    if notification_filter == "unread":
        notification_queryset = notification_queryset.filter(read_at__isnull=True)
    page = Paginator(notification_queryset, 25).get_page(request.GET.get("page"))
    today = timezone.localdate()
    grouped_notifications = []
    group_lookup = {}
    for notification in page.object_list:
        if notification_filter == "unread":
            group_name = "Unread"
        elif not notification.is_read:
            group_name = "New"
        elif timezone.localdate(notification.created_at) == today:
            group_name = "Today"
        else:
            group_name = "Earlier"
        if group_name not in group_lookup:
            group_lookup[group_name] = {"label": group_name, "notifications": []}
            grouped_notifications.append(group_lookup[group_name])
        group_lookup[group_name]["notifications"].append(notification)
    return render(
        request,
        "registry/notifications.html",
        {
            "notifications": page,
            "notification_page": page,
            "notification_filter": notification_filter,
            "grouped_notifications": grouped_notifications,
        },
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
                  "category": notification.category,
                  "category_label": notification.get_category_display(),
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


class AsyncNotificationEventStream:
    """An explicitly asynchronous SSE iterator for Django's ASGI handler."""

    def __init__(self, user_id):
        self.user_id = user_id

    def __aiter__(self):
        return self._events()

    async def _events(self):
        state = await _notification_stream_state(self.user_id)
        yield b"event: ready\ndata: {}\n\n"
        elapsed = 0
        try:
            while True:
                await asyncio.sleep(3)
                elapsed += 3
                next_state = await _notification_stream_state(self.user_id)
                if next_state != state:
                    state = next_state
                    yield b"event: notifications-changed\ndata: {}\n\n"
                    elapsed = 0
                elif elapsed >= 18:
                    yield b": keep-alive\n\n"
                    elapsed = 0
        except asyncio.CancelledError:
            return


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

    response = StreamingHttpResponse(
        AsyncNotificationEventStream(user_id),
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
