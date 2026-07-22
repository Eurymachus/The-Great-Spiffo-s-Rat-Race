import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme

from pages.models import Page

from .forms import (
    AccountClosureRequestForm,
    AgeEligibilityForm,
    PasswordResetRequestForm,
    RegistrationForm,
    ResendVerificationForm,
    SignInForm,
)
from .models import Notification, Participant
from .notifications import notify
from .rate_limit import exceeded, request_ip
from .tokens import create_verification_token, read_verification_token
from .turnstile import validate_turnstile
from .verification_email import send_password_reset_email, send_verification_email


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


@login_required
def account(request):
    return render(request, "registry/account.html")


@login_required
def notifications(request):
    page = Paginator(request.user.notifications.all(), 25).get_page(request.GET.get("page"))
    return render(
        request,
        "registry/notifications.html",
        {"notifications": page, "notification_page": page},
    )


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
