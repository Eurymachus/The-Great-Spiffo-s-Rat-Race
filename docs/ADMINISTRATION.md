# Participant Registry Administration

This guide covers the local development administrator. Production access,
multi-factor authentication, auditing, and backups must be completed before real
participant data is accepted.

## Create a Local Administrator

From the website worktree in PowerShell:

```powershell
.\.venv\Scripts\python .\apps\website\manage.py createsuperuser
```

Choose an email address, public nickname, and a password that is not reused
anywhere else. Django stores a password hash, not the entered password. The local
development database is excluded from Git.

Open `http://127.0.0.1:8000/admin/` and sign in.
The admin root and breadcrumb Home link open the participant list directly. A
separate dashboard will only be introduced when it has useful operational data to
show rather than duplicating the navigation.

## Participant List

The Participant Registry list supports:

- Search by nickname or email address
- Filter by registration status or date
- Review registration, verification, and consent details
- Edit status and private administrator notes
- Select pending or expired registrations and resend verification
- Select registrations and export them as CSV
- Promote participants to Approver, Moderator, or Challenge Administrator

Direct deletion is disabled. Mark a record removed until the formal privacy
deletion procedure is implemented.

Promoted participants use their existing participant email and password at
`/admin/`. Adding an Approver, Moderator, or Challenge Administrator group
automatically enables staff login; removing the final staff role disables it.
Promotion does not grant superuser access.

## Expire Abandoned Registrations

Run the following command manually during development:

```powershell
.\.venv\Scripts\python .\apps\website\manage.py expire_pending_registrations
```

It marks pending registrations expired when their latest verification email was
sent more than seven days ago. Production will run this command on a schedule.

## Current Safety Boundary

This administrator is suitable only for local development. Do not expose it to
the internet or enter real participant data until the production security and
operations checklist is complete.
