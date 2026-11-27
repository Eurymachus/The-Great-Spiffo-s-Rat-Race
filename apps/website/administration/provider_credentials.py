"""Environment-bound integration credentials. Never log returned values."""
import json
import re
from dataclasses import dataclass, field
from ipaddress import ip_address
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.decorators.debug import sensitive_variables


class ProviderConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class ProviderCredentials:
    client_id: str = ''
    client_secret: str = field(default='', repr=False)
    redirect_uri: str = ''
    tenant_id: str = ''


def public_origin():
    value = settings.SITE_PUBLIC_URL
    try:
        parsed = urlsplit(value)
        hostname, port = parsed.hostname, parsed.port
    except ValueError:
        return ''
    if (not hostname or parsed.username is not None or port == 0
            or any(c.isspace() or ord(c) < 32 for c in value)
            or any(c in parsed.netloc for c in r'\%') or parsed.netloc.endswith(':')
            or value not in (f'{parsed.scheme}://{parsed.netloc}', f'{parsed.scheme}://{parsed.netloc}/')):
        return ''
    try:
        ip_address(hostname)
    except ValueError:
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*', hostname):
            return ''
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and settings.DEBUG
                                       and hostname in {'localhost', '127.0.0.1', '::1'}):
        return ''
    return f'{parsed.scheme}://{parsed.netloc}'


def callback_matches(provider, callback):
    origin = public_origin()
    return bool(origin and callback == origin + reverse(f'registry:{provider}_callback'))


def validate_application(provider, client_id, callback, tenant_id=""):
    oauth = provider in {"discord", "twitch", "youtube"}
    if provider == 'discord':
        valid = bool(re.fullmatch(r'[1-9][0-9]{16,19}', client_id) and int(client_id) < 2**64)
    elif provider == 'twitch':
        valid = bool(re.fullmatch(r'[a-zA-Z0-9]{10,128}', client_id))
    elif provider == 'youtube':
        valid = bool(re.fullmatch(r'[a-zA-Z0-9-]+\.apps\.googleusercontent\.com', client_id))
    elif provider == 'graph':
        try:
            valid = bool(UUID(client_id).int and UUID(tenant_id).int
                         and str(UUID(client_id)) == client_id.lower() and str(UUID(tenant_id)) == tenant_id.lower())
        except (ValueError, AttributeError):
            valid = False
    elif provider == 'turnstile':
        valid = bool(re.fullmatch(r'[a-zA-Z0-9_-]{20,200}', client_id))
        if not settings.DEBUG and not getattr(settings, 'STAGING_ENVIRONMENT', False):
            valid = valid and client_id != '1x00000000000000000000AA'
    elif provider in {'openai', 'steam'}:
        valid = not client_id
    else:
        valid = False
    errors = {}
    if provider != 'graph' and tenant_id:
        errors['tenant_id'] = 'Tenant ID is only used by Microsoft Graph.'
    if provider == 'graph' and not valid:
        errors['tenant_id'] = 'Enter the tenant UUID from your Microsoft application.'
    if not oauth and callback:
        errors['redirect_uri'] = 'This integration does not use an OAuth callback.'
    if not valid:
        errors['client_id'] = 'Enter a valid application client ID for this provider.'
    if oauth and not callback_matches(provider, callback):
        errors['redirect_uri'] = 'Use this site origin and the exact provider callback path.'
    if errors:
        raise ValidationError(errors)


@sensitive_variables()
def cipher():
    try:
        keys = [Fernet(k.strip().encode('ascii')) for k in settings.PROVIDER_CONFIG_ENCRYPTION_KEYS.split(',') if k.strip()]
        if not keys:
            raise ValueError()
        return MultiFernet(keys)
    except (ValueError, UnicodeError, AttributeError):
        raise ProviderConfigurationError('Provider configuration encryption is unavailable.') from None


def validate_secret(provider, secret):
    if (not secret or len(secret) > 4096 or secret != secret.strip()
            or any(ord(c) < 32 for c in secret)):
        raise ProviderConfigurationError('Enter a valid secret without surrounding whitespace or control characters.')
    if (provider == 'turnstile' and secret == '1x0000000000000000000000000000000AA'
            and not settings.DEBUG and not getattr(settings, 'STAGING_ENVIRONMENT', False)):
        raise ProviderConfigurationError('Turnstile test secrets are not allowed on live.')


@sensitive_variables()
def encrypt_secret(provider, origin, secret):
    validate_secret(provider, secret)
    return cipher().encrypt(json.dumps([provider, origin, secret]).encode()).decode('ascii')


@sensitive_variables()
def decrypt_secret(record):
    try:
        provider, origin, secret = json.loads(cipher().decrypt(record.encrypted_secret.encode('ascii')))
        if provider != record.provider or origin != record.site_origin or not isinstance(secret, str) or not secret:
            raise ValueError()
        validate_secret(provider, secret)
        return secret
    except (InvalidToken, ValueError, TypeError, UnicodeError):
        raise ProviderConfigurationError('Stored provider configuration cannot be read.') from None


@sensitive_variables()
def environment_credentials(provider):
    if provider == 'graph':
        return ProviderCredentials(
            getattr(settings, 'MICROSOFT_GRAPH_CLIENT_ID', ''),
            getattr(settings, 'MICROSOFT_GRAPH_CLIENT_SECRET', ''), '',
            getattr(settings, 'MICROSOFT_GRAPH_TENANT_ID', ''),
        )
    if provider == 'turnstile':
        return ProviderCredentials(settings.TURNSTILE_SITE_KEY, settings.TURNSTILE_SECRET_KEY)
    if provider in {'steam', 'openai'}:
        name = 'STEAM_WEB_API_KEY' if provider == 'steam' else 'OPENAI_API_KEY'
        return ProviderCredentials(client_secret=getattr(settings, name, ''))
    prefix = provider.upper()
    return ProviderCredentials(*(getattr(settings, f'{prefix}_{name}', '') for name in ('CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI')))


@sensitive_variables()
def get_provider_credentials(provider):
    from .models import ProviderConfiguration
    record = ProviderConfiguration.objects.filter(provider=provider).first()
    if record is None or record.source == ProviderConfiguration.Source.ENVIRONMENT:
        return environment_credentials(provider)
    if record.source == ProviderConfiguration.Source.DISABLED:
        return ProviderCredentials()
    if not public_origin() or record.site_origin != public_origin():
        raise ProviderConfigurationError('Provider configuration belongs to another site.')
    try:
        validate_application(provider, record.client_id, record.redirect_uri, record.tenant_id)
    except ValidationError:
        raise ProviderConfigurationError('Provider configuration is invalid.') from None
    return ProviderCredentials(record.client_id, decrypt_secret(record), record.redirect_uri, record.tenant_id)
