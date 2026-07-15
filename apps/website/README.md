# Rat Race Website

This Django application will provide participant registration and, in later
milestones, run updates, moderation, leaderboards, and analysis.

## Current State

The Django project skeleton exists. Participant Registry features are the current
work; it is not ready for production or real participant data.

## Local Setup

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r .\apps\website\requirements.txt
.\.venv\Scripts\python .\apps\website\manage.py migrate
.\.venv\Scripts\python .\apps\website\manage.py runserver
```

Open `http://127.0.0.1:8000/`. The initial local configuration uses SQLite only
to make development easy; production will use PostgreSQL.

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

## Safety

- Never commit `.env`, credentials, participant data, or production backups.
- Do not use the development server in production.
- Production deployment instructions will be written before deployment.
