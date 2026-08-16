from django import forms
from django.conf import settings
from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from branding.models import SiteBranding
from .models import Participant


def validate_registration_nickname(nickname):
    former_label = (
        SiteBranding.objects.filter(pk=SiteBranding.SINGLETON_PK)
        .values_list("former_participant_label", flat=True)
        .first()
        or settings.SITE_FORMER_PARTICIPANT_LABEL
    )
    if nickname.casefold() == former_label.casefold():
        raise ValidationError("This nickname is reserved by the system.")
    if Participant.objects.filter(normalized_nickname=nickname.casefold()).exists():
        raise ValidationError("This nickname is already reserved.")
    return nickname


def validate_registration_email(email):
    if Participant.objects.filter(normalized_email=email.casefold()).exists():
        raise ValidationError("This email address is already registered.")
    return email


class ModReviewRequestForm(forms.Form):
    workshop_id = forms.RegexField(
        regex=r"^[0-9]{6,20}$",
        max_length=20,
        label="Selected Steam Workshop ID",
        error_messages={
            "invalid": "Enter the numeric ID from the Steam Workshop page."
        },
        widget=forms.HiddenInput(),
    )
    reason = forms.CharField(
        max_length=1000,
        label="Reason for adding this mod",
        widget=forms.Textarea(attrs={"rows": 5}),
    )


class SignInForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "The email or password was not recognised, or this account is not yet active.",
        "inactive": "The email or password was not recognised, or this account is not yet active.",
    }


class AgeEligibilityForm(forms.Form):
    date_of_birth = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "autocomplete": "bday",
                "aria-label": "Date of birth",
            },
            format="%Y-%m-%d",
        ),
        input_formats=("%Y-%m-%d",),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date_of_birth"].widget.attrs["max"] = date.today().isoformat()

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data["date_of_birth"]
        try:
            eligible_from = date_of_birth.replace(
                year=date_of_birth.year + settings.PARTICIPANT_MINIMUM_AGE
            )
        except ValueError:
            eligible_from = date_of_birth.replace(
                year=date_of_birth.year + settings.PARTICIPANT_MINIMUM_AGE,
                day=28,
            )
        if eligible_from > date.today():
            raise forms.ValidationError(
                f"You must be aged {settings.PARTICIPANT_MINIMUM_AGE} or over to create an account."
            )
        return date_of_birth


class RegistrationForm(forms.Form):
    email_already_registered = False

    nickname = forms.CharField(
        min_length=3,
        max_length=40,
        label="Nickname",
        help_text=f"This will be your public {settings.SITE_SHORT_TITLE} name.",
        widget=forms.TextInput(attrs={"autocomplete": "nickname"}),
    )
    email = forms.EmailField(
        label="Email address",
        help_text="Your email will not be displayed publicly.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Use a unique password of at least 8 characters.",
    )
    password_confirmation = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    acknowledge_privacy = forms.BooleanField(
        label="I have read the privacy notice.",
        error_messages={"required": "You must confirm that you have read the privacy notice."},
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        brand = SiteBranding.current()
        participant_label = (
            brand.participant_label if brand else settings.SITE_PARTICIPANT_LABEL
        )
        short_title = brand.short_title if brand else settings.SITE_SHORT_TITLE
        self.fields["nickname"].label = f"{participant_label} nickname"
        self.fields["nickname"].help_text = (
            f"This will be your public {short_title} name."
        )

    def clean_nickname(self):
        nickname = self.cleaned_data["nickname"].strip()
        return validate_registration_nickname(nickname)

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        try:
            return validate_registration_email(email)
        except ValidationError:
            self.email_already_registered = True
            raise

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirmation", "The passwords do not match.")
        if password:
            validate_password(password)
        return cleaned_data


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        help_text="Enter the address used for your registration.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        help_text="Enter the address used for your participant account.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip()


class AccountClosureRequestForm(forms.Form):
    current_password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="This confirms that the request comes from you.",
    )
    note = forms.CharField(
        label="Anything we should know?",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Optional. Do not include passwords or other sensitive information.",
    )
    confirm = forms.BooleanField(
        label="I want to request closure and deletion of my participant account.",
        error_messages={"required": "You must confirm the account-closure request."},
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("The current password is incorrect.")
        return password


class AvatarUploadForm(forms.Form):
    avatar = forms.ImageField(
        label="Choose an avatar",
        help_text="JPEG, PNG or WebP, up to 5 MB. The image will be cropped to a square.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp",
            "class": "avatar-file-input",
            "data-avatar-input": "",
        }),
    )

    def clean_avatar(self):
        avatar = self.cleaned_data["avatar"]
        if avatar.size > settings.AVATAR_UPLOAD_MAX_BYTES:
            raise forms.ValidationError("The avatar must be no larger than 5 MB.")
        if avatar.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise forms.ValidationError("Upload a JPEG, PNG or WebP image.")
        return avatar


class RunSubmissionForm(forms.Form):
    evidence_provider = forms.ChoiceField(
        label="Evidence channel",
        required=False,
        choices=(),
        widget=forms.HiddenInput,
    )
    run_export = forms.CharField(
        label="Run export",
        max_length=24 * 1024 * 1024,
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "spellcheck": "false",
                "autocomplete": "off",
                "placeholder": "Paste the TGSRR1.BLK1... export here",
            }
        ),
        help_text="Paste the complete value generated by the Rat Race tracker.",
    )
    evidence_video = forms.ChoiceField(
        label="Broadcast or video",
        required=False,
        choices=(),
        help_text="Choose recent media from your selected streaming channel.",
    )
    evidence_start_seconds = forms.IntegerField(
        label="Run starts at (seconds)", required=False, min_value=0
    )
    evidence_end_seconds = forms.IntegerField(
        label="Run ends at (seconds)", required=False, min_value=1
    )
    evidence_clips = forms.MultipleChoiceField(
        label="Supporting clips",
        required=False,
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )
    manual_evidence_url = forms.URLField(
        label="Or enter a broadcast URL",
        required=False,
        max_length=1000,
        help_text="Use this when the broadcast is not available in the recent list.",
    )

    def __init__(self, *args, participant=None, selected_provider=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.media_by_id = {}
        if participant is None:
            return
        from .models import StreamingMedia

        accounts = participant.streaming_accounts.filter(status="connected").exclude(
            provider="discord"
        )
        providers = list(accounts.values_list("provider", flat=True))
        self.fields["evidence_provider"].choices = [(value, value) for value in providers]
        requested_provider = (
            self.data.get("evidence_provider") if self.is_bound else selected_provider
        )
        if requested_provider not in providers:
            primary = getattr(participant, "primary_streaming_account", None)
            requested_provider = (
                primary.provider if primary and primary.provider in providers else providers[0] if providers else ""
            )
        self.selected_provider = requested_provider
        self.initial["evidence_provider"] = requested_provider
        media = StreamingMedia.objects.filter(
            account__participant=participant,
            account__status="connected",
            account__provider=requested_provider,
        )
        self.media_by_id = {str(item.id): item for item in media}
        self.fields["evidence_video"].choices = [("", "Choose a broadcast")] + [
            (str(item.id), f"{item.published_at:%d %b %Y}: {item.title}")
            for item in media
            if item.kind == StreamingMedia.Kind.VIDEO and item.published_at
        ]
        if "evidence_clips" in self.fields:
            self.fields["evidence_clips"].choices = [
                (str(item.id), item.title or item.provider_media_id)
                for item in media
                if item.kind == StreamingMedia.Kind.CLIP
            ]

    def clean(self):
        cleaned = super().clean()
        selected = cleaned.get("evidence_video")
        provider = cleaned.get("evidence_provider")
        manual = cleaned.get("manual_evidence_url")
        if selected and selected not in self.media_by_id:
            self.add_error("evidence_video", "Choose a broadcast from your connected channel.")
        elif selected and self.media_by_id[selected].account.provider != provider:
            self.add_error("evidence_video", "Choose media from the selected channel.")
        if "evidence_clips" in self.fields:
            invalid_clips = [
                value
                for value in cleaned.get("evidence_clips", [])
                if value not in self.media_by_id
            ]
            if invalid_clips:
                self.add_error("evidence_clips", "Choose clips from your connected channel.")
        if selected and manual:
            self.add_error(
                "manual_evidence_url",
                "Choose a recent broadcast or enter a URL, not both.",
            )
        start = cleaned.get("evidence_start_seconds")
        end = cleaned.get("evidence_end_seconds")
        if start is not None and end is not None and end <= start:
            self.add_error(
                "evidence_end_seconds", "The end must be later than the start."
            )
        return cleaned


class LegacyRunSubmissionForm(RunSubmissionForm):
    run_export = None
    evidence_clips = None
    character_name = forms.CharField(label="Character name", max_length=160)
    zombie_kills = forms.IntegerField(label="Zombie kills", min_value=0)
    survival_time = forms.CharField(
        label="Time survived",
        max_length=255,
        help_text="Enter YY:MM:DD:HH or use words, such as 1 year 5 months 20 days 6 hours.",
        widget=forms.TextInput(attrs={
            "placeholder": "01:05:20:06",
            "autocomplete": "off",
            "data-survival-time": "",
        }),
    )
    maxed_skills = forms.IntegerField(
        label="Skills at Level 10", min_value=0, max_value=35
    )
    outposts_cleared = forms.IntegerField(
        label="Outposts completed", min_value=0, max_value=13
    )
    run_state = forms.ChoiceField(
        label="Run status",
        choices=(("alive", "Alive"), ("dead", "Dead")),
        widget=forms.RadioSelect,
    )

    def clean_survival_time(self):
        from .legacy_submissions import parse_survival_time

        original, full, days = parse_survival_time(self.cleaned_data["survival_time"])
        self.normalized_survival_time = full
        self.survival_days = days
        return original

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("evidence_video") and not cleaned.get("manual_evidence_url"):
            self.add_error(
                "manual_evidence_url",
                "Choose a recent broadcast or enter the VOD URL.",
            )
        return cleaned
