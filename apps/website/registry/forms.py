from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Participant


class RegistrationForm(forms.Form):
    email_already_registered = False

    nickname = forms.CharField(
        min_length=3,
        max_length=40,
        label="Participant nickname",
        help_text="This will be your public Rat Race name.",
    )
    email = forms.EmailField(
        label="Email address",
        help_text="Your email will not be displayed publicly.",
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput,
        help_text="Use a unique password of at least 8 characters.",
    )
    password_confirmation = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput,
    )
    accept_privacy = forms.BooleanField(
        label="I accept the draft privacy notice.",
        error_messages={"required": "You must accept the privacy notice."},
    )

    def clean_nickname(self):
        nickname = self.cleaned_data["nickname"].strip()
        if Participant.objects.filter(
            normalized_nickname=nickname.casefold()
        ).exists():
            raise forms.ValidationError("This nickname is already reserved.")
        return nickname

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if Participant.objects.filter(normalized_email=email.casefold()).exists():
            self.email_already_registered = True
            raise forms.ValidationError(
                "This email address is already registered."
            )
        return email

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
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        help_text="Enter the address used for your participant account.",
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip()


class AccountClosureRequestForm(forms.Form):
    current_password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput,
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
