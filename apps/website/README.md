# Rat Race Website

This Django application provides the public and administrative platform for The
Great Spiffo's Rat Race, including registration, submissions, moderation,
rankings, managed pages, mod policy, exploit rulings, and reference updates.

## Current State

The product surface is feature-complete for its current launch scope and is being
prepared for production deployment. Remaining launch work is tracked in
`docs/WEBSITE_NOW.md`.

## Local Setup

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r .\apps\website\requirements.txt
.\.venv\Scripts\python .\apps\website\manage.py migrate
.\.venv\Scripts\python .\apps\website\manage.py bootstrap_roles
.\.venv\Scripts\python .\apps\website\manage.py import_zomboid_catalogue
.\scripts\start_website_dev.ps1 -Port 8001 -Background
```

Open `http://127.0.0.1:8001/`. Local development uses SQLite and an in-process
cache. The canonical launcher loads `.env`, starts the ASGI application and the
reference-update worker, and verifies both before reporting the site ready.

The launcher binds to loopback by default. On the original development computer,
explicitly opt into LAN access when it is required:

```powershell
.\scripts\start_website_dev.ps1 -Port 8001 -BindAddress 0.0.0.0 -LanAddress 192.168.4.100 -Background
```

Do not use that LAN form on an internet-facing host. Production and host-side
acceptance testing must keep the application on loopback and use the documented
proxy or tunnel boundary.

Do not replace the canonical launcher with a bare `manage.py runserver` or
Uvicorn command. Doing so omits the environment and required worker process.

Signup and resend pages use Cloudflare's official localhost test credentials.
The widget therefore passes without a real Cloudflare account. Production must
set `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` to live credentials and use
a shared cache for the request limits.

Public operator details remain central Django settings sourced from environment
variables. Reusable brand details are editable in the singleton Branding
admin record and fall back to the corresponding environment-backed settings if
that record is unavailable. Development defaults identify Sentinel Tech Ltd,
company number 10998950, and the approved Rat Race vocabulary. See `.env.example`
for the supported `SITE_*` names. Django reads the process environment directly;
the example file is a deployment reference and is not automatically loaded by
the local development server.

Local administrator setup and operation are documented in
`docs/ADMINISTRATION.md`.
The participant navigation and local journey baseline are recorded in
`docs/LOCAL_WEBSITE_EXPERIENCE.md`.

## Production

Production must set `DJANGO_SETTINGS_MODULE=config.settings_production`. That
settings module fails closed unless the complete environment contract is
present, including PostgreSQL, Redis, SMTP email, live Turnstile credentials,
avatar moderation, connected providers, persistent storage, and the Steam
reference and decompilation toolchain.

Use `.env.example` as the non-secret configuration inventory. The complete
runtime, release, health, backup, and rollback contract is documented in
`docs/PRODUCTION_DEPLOYMENT.md`.

## Safety

- Never commit `.env`, credentials, participant data, or production backups.
- Do not use development settings or the local launcher in production.
- Do not accept traffic until `/health/ready/` reports ready for the intended
  release.
