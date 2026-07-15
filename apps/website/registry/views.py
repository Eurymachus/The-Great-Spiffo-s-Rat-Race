import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    AccountClosureRequestForm,
    PasswordResetRequestForm,
    RegistrationForm,
    ResendVerificationForm,
)
from .models import Participant
from .rate_limit import exceeded, request_ip
from .tokens import create_verification_token, read_verification_token
from .turnstile import validate_turnstile
from .verification_email import send_password_reset_email, send_verification_email


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
    if request.user.is_authenticated:
        return redirect("registry:account")
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
                {"form": form, "turnstile_site_key": settings.TURNSTILE_SITE_KEY},
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
        verification_url = issue_verification(participant, request)
        request.session["registered_nickname"] = participant.nickname
        if settings.DEBUG:
            request.session["development_verification_url"] = verification_url
        return redirect("registry:thanks")
    return render(
        request,
        "registry/register.html",
        {"form": form, "turnstile_site_key": settings.TURNSTILE_SITE_KEY},
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

    return render(
        request,
        "registry/verification_result.html",
        {"result": "verified", "participant": participant},
    )


@login_required
def account(request):
    return render(request, "registry/account.html")


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
