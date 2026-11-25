# OSWALD read-only inventory, 25 November 2026

Clarification after inspecting the counted row: live has zero participant
Workshop submissions, pending requests or votes. The one `registry_workshopmod`
row is the required challenge mod, Workshop ID `3554864233`, seeded by migration
`0024_workshop_mods`, with no submitter/reviewer. Its creation timestamp aligns
with that migration. It is setup catalogue data, not evidence of live intake.
Live has zero Participant accounts, including staff/superusers. Participant is
the authentication model; there is no separate `auth_user` table.

Source: OSWALD chat `01a2139d-010f-7bf2-8277-5ac2e96d3fc8`,
"Audit staging and live rollout", completed inventory report. The coordinating
local chat received this report through the connected Codex host. Database
queries used read-only transactions. No host files, configuration, data,
services or deployments were changed. This is a point-in-time inventory,
not candidate acceptance or proof of recovery.

| Check | Staging | Live |
| --- | --- | --- |
| Running release | `f079ead` | `6582cc4` |
| Release path | `G:\RatRace_Staging\releases\f079ead` | `G:\RatRace\releases\6582cc4` |
| Public homepage | `dev.tgsrr.com`: HTTP 200 | `tgsrr.com`: HTTP 503, maintenance enabled |
| Liveness/readiness | Passed, matching-release worker heartbeat | Passed, matching-release worker heartbeat |
| Web listener | `127.0.0.1:8002` | `127.0.0.1:8000` |
| Database | PostgreSQL 18.4, `ratrace`, `127.0.0.1:5433` | PostgreSQL 18.4, `ratrace`, `127.0.0.1:5432` |
| Latest recorded Registry migration | `0068` | `0036` |
| Latest recorded Operations migration | `0016` | `0011` |
| Latest recorded Pages migration | `0043` | `0042` |
| Latest recorded Catalogue migration | `0011` | `0007` |
| Accounts | 5 | 0 |
| RR 1 runs / claims / submissions | 211 / 2 / 211 | 0 / 0 / 0 |
| RR 2 submissions / Workshop records | 31 / 2 | 0 / 1 |
| Media | `G:\RatRace_Staging\media` | `G:\RatRace\media` |
| Protected configuration | `G:\RatRace_Staging\config\staging.env` | `G:\RatRace\config\acceptance.env` |
| Visible backup evidence | PostgreSQL dump dated 20 November | Backup directory dated 13 August containing configuration/template material; live PostgreSQL dump unverified |

Migration numbers above describe the reported differing apps, not a complete
migration-graph comparison. Counts must be rechecked before any future change.
The single live Workshop record must survive the upgrade. Staging has populated
data and is not implicitly disposable. The current staging release supersedes
the historical October deployment note.

## Outstanding gates

Update after the owner-approved direct app launch with `--do-not-de-elevate`:
desktop, backend and approved unsandboxed PowerShell verified High integrity
and elevated tokens. Sandboxed PowerShell remained Medium and non-administrator.
All four expected web/worker tasks were readable, enabled and running as SYSTEM.
Each has an enabled boot trigger delayed 30 seconds and 999 restart attempts at
one-minute intervals. Live tasks target `6582cc4` and also have an enabled time
trigger; staging tasks target `f079ead`. Targets match public health responses.
This supersedes the task-visibility limitation below. It verifies configuration,
not an actual restart/reboot recovery test. No task or service was changed.

Follow-up: [BACKUP_RESTORE_REHEARSAL.md](BACKUP_RESTORE_REHEARSAL.md) records
verified tools, capacity, ACL findings and unused rehearsal targets. Direct task
queries returned Access denied, clarifying the earlier visibility limitation.

- Neither deployed release has definitions/configuration for the new independent
  account, Workshop, RR 1 and RR 2 switches. Only site-wide maintenance is
  available: true on live, unset/default off on staging. Local candidate tests
  do not establish hosted phased-launch behavior.
- No Rat Race startup, backup or retention task appeared in the auditing
  account's Task Scheduler view. Running web and worker processes were verified.
  This does not prove tasks are absent under other accounts or supervision
  mechanisms; restart supervision and scheduling remain unverified.
- A live PostgreSQL backup and tested matching database/media/configuration
  restore remain unverified. A visible backup directory is not recovery proof.
- Candidate-specific PostgreSQL migration/preservation and concurrency checks,
  provider acceptance, retention scheduling and RR 1 handover remain open.

Recommended next preparation: define a fresh live database/media/protected
configuration backup and isolated restore rehearsal, preserving the existing
Workshop record. Record exact destinations, database identities, encryption-key
handling and verification criteria before execution. This inventory does not
authorize a reset, deployment, service restart or restore over existing data.
