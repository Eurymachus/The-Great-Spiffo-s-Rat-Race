from django import forms
from django.views.decorators.debug import sensitive_variables
from django.core.exceptions import ValidationError
from .models import ProviderConfiguration
from .provider_credentials import (
    ProviderConfigurationError, cipher, decrypt_secret, encrypt_secret,
    public_origin, validate_application, validate_secret,
)


class ProviderConfigurationForm(forms.ModelForm):
    replacement_secret = forms.CharField(
        label='Replace secret or API key', required=False, strip=False, max_length=4096,
        widget=forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'}),
        help_text='Leave blank to keep the saved secret. Saved secrets are never displayed.',
    )

    class Meta:
        model = ProviderConfiguration
        fields = ('provider', 'source', 'client_id', 'tenant_id', 'redirect_uri')
        labels = {'client_id': 'Client ID or site key'}
        help_texts = {
            'client_id': 'Application client ID, or the public Turnstile site key. Not used for OpenAI or Steam Web API.',
            'tenant_id': 'Microsoft Graph tenant UUID only.',
            'redirect_uri': 'Discord, Twitch and YouTube only. Must match this site and the registered callback.',
        }

    @sensitive_variables()
    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get('provider') or self.instance.provider
        secret = cleaned.get('replacement_secret', '')
        if secret:
            try:
                validate_secret(provider, secret)
            except ProviderConfigurationError as exc:
                self.add_error('replacement_secret', str(exc))
        if cleaned.get('source') != ProviderConfiguration.Source.DATABASE:
            if secret:
                self.add_error('replacement_secret', 'Select encrypted database storage before replacing the secret.')
            return cleaned
        try:
            validate_application(provider, cleaned.get('client_id', ''), cleaned.get('redirect_uri', ''), cleaned.get('tenant_id', ''))
        except ValidationError as exc:
            self.add_error(None, exc)
        if self.instance.pk and self.instance.site_origin != public_origin():
            self.add_error(None, 'This record belongs to another site. Use server environment configuration and have the host operator provision a record for this site.')
        try:
            cipher()
            if not secret:
                if not self.instance.encrypted_secret:
                    self.add_error('replacement_secret', 'Enter the secret or API key for database storage.')
                else:
                    decrypt_secret(self.instance)
                    if cleaned.get('client_id', '') != self.instance.client_id or cleaned.get('tenant_id', '') != self.instance.tenant_id:
                        self.add_error('replacement_secret', 'Replace the secret when changing the client or tenant ID.')
        except ProviderConfigurationError as exc:
            self.add_error(None, str(exc))
        return cleaned

    @sensitive_variables()
    def save(self, commit=True):
        record = super().save(commit=False)
        if not record.site_origin:
            record.site_origin = public_origin()
        secret = self.cleaned_data.get('replacement_secret')
        if secret:
            record.encrypted_secret = encrypt_secret(record.provider, record.site_origin, secret)
        if commit:
            record.save()
        return record
