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

The action permanently removes the participant login identity and writes a
non-personal closure receipt containing a random reference plus request/process
timestamps.

The registry milestone has no run records yet. The future `Run.participant`
relationship must be nullable and use `on_delete=models.SET_NULL`. Deleting a
participant will then detach its runs without deleting or combining them. Each
detached run is displayed publicly as `Former Rat Racer`; run-owned daily data
continues to belong to its independent run. Never use cascading deletion for
historical challenge data.

Promoted participants use their existing participant email and password at
`/admin/`. Adding an Approver, Moderator, or Challenge Administrator group
automatically enables staff login; removing the final staff role disables it.
Promotion does not grant superuser access.

## Manage Website Branding

The Website Configuration section contains one protected Branding record.
It controls the reusable full title, short title, tagline, welcome message,
former-participant label, and affiliation disclaimer. Saving it updates public
pages immediately. It cannot be duplicated or deleted.

Superusers already have access to this section. A participant may instead be
promoted to the `Branding Administrator` group, which grants scoped branding and
theme permissions plus staff login. A branding-only administrator is sent
directly to Branding when opening `/admin/` and cannot view participants.

Website Themes provides three editable presets. From its list, a branding
administrator can preview a selected theme on the real signup page, activate it,
duplicate it as a working copy, or restore the supplied presets. Previewing is
private and does not change the public theme. Theme deletion is disabled.

## Manage Website Pages

The Website Content section contains Pages. The protected Homepage record is the
first backend-managed public page. Its existing wording was copied from Branding
when the page system was introduced, so the public appearance did not reset.
Opening Pages shows the managed page list, even while Homepage is the only
entry. Additional standalone pages will only be enabled when public routing and
navigation management are ready.

Open Homepage to manage the complete page from one editor. Sections are
collapsible, and each section contains its own collapsible cards. Add, remove,
and reorder sections or cards without navigating away from the page. Everything
is saved together using the page's Save controls.

Each section uses an approved, responsive template rather than arbitrary HTML,
CSS, or JavaScript. The first available section types are:

- Introduction and actions, with headings, introductory text, visitor actions,
  a signed-in action, and optional ordered information cards.
- Numbered information cards, for a separate ordered group of explanatory cards.

Use the Move up and Move down controls to change section and card order. Use
Visible publicly to temporarily hide a section without deleting its content.
The homepage record cannot be deleted and its `home` address cannot be changed.

Branding Administrators can manage Branding, Themes, Pages, sections, and
section items. This role still cannot view or manage participant records.
Authentication, signup, account, privacy, and administration screens remain
structured application pages so an editor cannot accidentally damage a security
or legal workflow.

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
