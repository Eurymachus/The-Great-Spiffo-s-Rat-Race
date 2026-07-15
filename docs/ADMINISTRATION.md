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
- Filter and review participant account-closure requests

Direct ad hoc deletion is disabled. Use Removed status for moderation removals;
use the confirmed closure-processing procedure below only for authenticated
participant deletion requests.

Account-closure requests record the request time and an optional participant
note. They do not automatically deactivate or erase the account. Before public
launch, finalise handling for database backups and confirmation to the
participant. Until that policy is approved, administrators must not promise an
immediate purge from every backup.

## Process an Account-Closure Request

Only a superuser or member of the Challenge Administrator group can see and run
the closure-processing action.

1. Open Participants.
2. Filter `Deletion requested at` by `Has date`.
3. Confirm the participant has no staff access. Staff accounts are deliberately
   refused until their privileged groups and staff status are removed.
4. Select the participant and choose `Process closure and redact selected
   participants`.
5. Review the dedicated confirmation page and confirm the destructive action.

The action permanently removes the participant login identity, ensures the
protected `Redacted` system participant exists, and writes a non-personal closure
receipt containing a random reference plus request/process timestamps. The
system participant is inactive and has no usable password.

The registry milestone has no run records to transfer. Every future model that
owns participant run or report data must use protected deletion and be added to
this action's reassignment transaction before launch. Never allow a cascading
delete to discard historical challenge data accidentally.

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
