"""Explicit isolated PostgreSQL test profile, never load a host environment file."""
import os

from django.core.exceptions import ImproperlyConfigured

from .settings_test import *  # noqa: F403

if os.environ.get('RR_TEST_POSTGRES_ISOLATED') != 'yes':
    raise ImproperlyConfigured('Explicit isolated PostgreSQL test acknowledgement required.')
port = os.environ.get('RR_TEST_POSTGRES_PORT', '')
if not port.isdigit() or not 1024 <= int(port) <= 65535 or port in {'5432', '5433'}:
    raise ImproperlyConfigured('Tests require a separate high-port cluster, not live/staging ports.')
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': '127.0.0.1',
    'PORT': port,
    'NAME': 'postgres',
    'USER': os.environ['RR_TEST_POSTGRES_USER'],
    'PASSWORD': os.environ['RR_TEST_POSTGRES_PASSWORD'],
    'CONN_MAX_AGE': 0,
    'TEST': {'NAME': 'test_ratrace_launch'},
}}
