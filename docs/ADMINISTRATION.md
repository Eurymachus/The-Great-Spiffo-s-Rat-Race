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
- Promote participants to Workshop Mod Approver, Run Submission Approver,
  Moderator, or Challenge Administrator
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
`/admin/`. Adding a Workshop Mod Approver, Run Submission Approver, Moderator,
or Challenge Administrator group
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
# Rat Race 1.0 data import

The Rat Race 1.0 Leaderboard and Rat Race 1.0 Hall of Fame use one merged legacy dataset,
stored separately from verified Rat Race runs. The spreadsheet handover date may occur
after production deployment, so the import is an explicit super-admin operation
and is never performed automatically by a migration. Rat Race 1.0 is still
running: this handover date does not close the challenge, and approved claimants
can continue submitting updates to Active runs.

1. Export the handover Rat Race 1.0 Leaderboard and Rat Race 1.0 Hall of Fame worksheets as
   separate CSV files.
2. Open `Participant Registry > Rat Race 1.0 data imports` in administration.
3. Select `Upload Rat Race 1.0 data`, then upload both CSV files.
4. Review detected rows, merged runs, Active and Inactive totals, and warnings.
5. Confirm only when the preview is correct. Confirmation replaces the current
   imported legacy runs in one database transaction.

The importer ignores streaming-channel and source-link columns. It stores the
validated original CSV text, filenames, SHA-256 hashes, preview, uploader and
import time as an audit record. Replacement is refused after claims or
participant-created legacy submissions exist, preventing an established
ownership journey from being silently destroyed.

The same validator is available for controlled command-line operations:

```powershell
.\.venv\Scripts\python.exe .\apps\website\manage.py import_legacy_leaderboard `
  --leaderboard C:\path\legacy-leaderboard.csv `
  --hall-of-fame C:\path\legacy-hall-of-fame.csv
```

That command previews by default. Add `--confirm` only after reviewing its
counts. Do not replace this process with a runtime Google Sheets dependency.

## Repeatable Rat Race 1.0 staging rehearsals

Use `reset_legacy_rehearsal` to return staging's Rat Race 1.0 dataset to empty
after testing imports, claims and participant updates. It requires the effective
Django setting `STAGING_ENVIRONMENT` to be boolean `True`; ordinary development
and production settings are refused, including preview mode. Never enable this
setting on production to bypass the restriction.

The command deletes all Rat Race 1.0 runs and their claims and submissions,
including approved, pending and declined records. It preserves participant
accounts, passwords, roles, primary-channel selections, Twitch/YouTube connections,
encrypted credentials, cached media, and all Rat Race 2.0 runs and evidence.
Import audit records (including uploaded CSVs and previews) remain available.
Existing notifications and administration logs also remain; old rehearsal links
may point to removed records. The reset sends no notifications or provider calls.

1. Deploy the command to staging. Coordinate a quiet rehearsal window: pause
   tester and moderator activity, imports, claims and submissions until the reset
   finishes. Row locking does not prevent every concurrent new import.
2. On the staging host, use its deployed release and virtual environment, with
   its protected `staging.env` loaded using the existing deployment tooling and
   `DJANGO_SETTINGS_MODULE=config.settings_windows_staging`. Verify the database
   target is the staging database. Do not copy production environment settings.
3. From the deployed repository root, preview the counts:

   ```powershell
   python .\apps\website\manage.py reset_legacy_rehearsal
   ```

4. Retain any test results needed for comparison, then explicitly confirm:

   ```powershell
   python .\apps\website\manage.py reset_legacy_rehearsal --confirm
   ```

   Deletion is transactional. A failure rolls it back. An empty dataset can be
   reset again safely. These commands assume `python` resolves to the staging
   virtual environment; they do not load secrets or select a database themselves.
5. Upload fresh Leaderboard and Hall of Fame CSVs using the import process above.
   Review counts and warnings and confirm the import. Previously completed import
   records remain audit history and cannot be confirmed again.
6. Rehearse claim approval and decline, progress submission and review, death
   reporting, and both ranking views. Use the retained accounts and connected
   channels to test Twitch and YouTube evidence again without reconnecting solely
   because of the reset. Provider expiry or revocation may still require reconnecting.
7. Record the result, then repeat from step 1 for another rehearsal. Before and
   after reset, spot-check a retained account, each provider connection and a 2.0 run.

This is a staging rehearsal operation, not the live handover process. Live import
replacement remains blocked after any claim or participant-created 1.0 submission.
