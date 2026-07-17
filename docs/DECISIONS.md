# Decisions

This file records settled project decisions so they do not need to be repeatedly
reconstructed. Add new entries briefly, with the date and reason.

## 2026-07-13 — The repository covers the whole challenge

The existing Workshop repository will encompass the Project Zomboid mod and the
wider Rat Race platform. Project-level website and documentation files will live
outside `Contents/`.

## 2026-07-13 — Preserve the Workshop boundary

Only Project Zomboid Workshop deliverables belong under `Contents/`. The PZ
publisher uploads `Contents/` as item content and handles the root `preview.png`
and `workshop.txt` separately.

## 2026-07-13 — Updates are cumulative snapshots

Participants will paste an encoded update code into the website. Each update is a
self-contained snapshot containing the run's data from its beginning through the
current point, including per-in-game-day aggregate deltas and relevant current or
lifetime tables. Updates are not declarations that a run has finished.

## 2026-07-13 — Start with a Participant Registry

The first website milestone is verified participant registration and nickname
reservation. Report ingestion, moderation, leaderboards, and analytics are later
milestones.

## 2026-07-13 — Use a documented, self-hosted web stack

The website will be a single Django application backed by PostgreSQL and packaged
with Docker Compose. Production will run in an isolated Ubuntu Hyper-V virtual
machine on the existing OVH dedicated server. Microsoft 365 will provide ordinary
transactional email. Cloudflare's free DNS, Tunnel, HTTPS, and Turnstile services
are planned once the final domain is chosen.

Documentation, reproducible setup, backup and recovery instructions, and a
plain-language operator guide are completion requirements rather than later work.

## 2026-07-13 — Qualify the word “official”

The website and mod are official to The Great Spiffo's Rat Race community
challenge. They are not official Project Zomboid or The Indie Stone products.
Public wording must make that distinction clear and avoid implying endorsement.

## 2026-07-14 — Participants are permanent login accounts

Signup creates a participant with a public nickname, private email login, and
securely hashed password. Verification activates the account. Administrators may
promote that same account to Approver, Moderator, or Challenge Administrator and
thereby grant scoped `/admin/` access. Signup never grants staff or superuser
privileges automatically.

## 2026-07-15 — Closed accounts retain anonymous challenge history

Processing an approved account-closure request removes the participant login and
personal identity. Future `Run.participant` relationships are nullable and use
`SET_NULL`, preserving each run independently without combining former
participants. Detached runs display as `Former Rat Racer`, have no participant
profile link, and may remain in anonymous aggregate statistics. A closure receipt
retains only a random reference and request/process timestamps. This supersedes
the briefly considered shared Redacted-account design.

## 2026-07-15 — Sentinel Tech Ltd operates the challenge website

Sentinel Tech Ltd is the data controller for The Great Spiffo's Rat Race
challenge website and its participant data. Privacy and account-data enquiries
use `thegreatspiffo@machus.co.uk` provisionally until a final Rat Race domain
address is selected.

## 2026-07-15 — Use a documented participant-data retention schedule

Sentinel Tech Ltd will apply the retention schedule in `docs/RETENTION.md`.
Identifiable information has finite, purpose-based periods; genuinely anonymised
challenge history and non-personal closure receipts may be retained indefinitely.
The schedule is reviewed at least annually and when the platform's purpose or
processing changes.

## 2026-07-15 — Use contract, legitimate interests, and legal obligation

Core participant-account and challenge services use contract as their lawful
basis. Security, abuse prevention, moderation, validation, challenge integrity,
essential logs, and anonymisation use legitimate interests subject to the
assessment in `docs/LAWFUL_BASES.md`. Applicable compliance processing uses
legal obligation. Consent is reserved for genuinely optional future processing.
Privacy-notice acknowledgement is recorded as acknowledgement, not consent.

## 2026-07-15 — Keep operator identity in environment-backed settings

Public legal/operator details are deployment configuration, not participant
data or routinely editable site content. Django exposes central `SITE_*`
settings to templates, with version-controlled development defaults and
environment-variable overrides for production. Sentinel Tech Ltd's verified
Companies House number is `10998950`.

Reusable approved brand vocabulary follows the same configuration path: full
and short titles, tagline, welcome message, former-participant label, and Indie
Stone disclaimer. Longer editorial and policy content remains version-controlled
or becomes deliberately administrator-managed content in a future data model.

## 2026-07-15 — Manage reusable branding through a singleton backend record

Reusable presentation vocabulary is editable through one non-deletable Site
Branding record. Environment-backed values remain safe defaults, while database
values update rendered pages immediately. Superusers inherit access normally;
the Branding Administrator group grants scoped view/change permissions and no
participant-management access.

## 2026-07-15 — Complete UK rights and complaint information before visual branding

The participant privacy notice describes access, correction, erasure,
restriction, portability, objection, the normal one-calendar-month response
period, and the UK ICO complaint route. The operator procedure is documented in
`docs/PRIVACY_REQUESTS.md`.

The next product milestone is the front-end visual brand and signup-launch
experience. Run/report ingestion is deliberately deferred until Project Zomboid
B42 Stable and the challenge rules are finalised.

## 2026-07-15 — Use self-declared 18+ participation eligibility

Participation is limited to people aged 18 or over. Signup requires a clear
self-declaration and records its timestamp and policy version. This is an
eligibility acknowledgement, not age verification. The website does not collect
dates of birth or identity documents; accounts reasonably believed to belong to
an under-18 participant may be disabled and investigated or removed.

## 2026-07-15 — Use structured, backend-managed visual themes

Visual styling is managed as reusable Website Theme records, with one active
theme selected by Branding. Authorised branding administrators can edit
validated design tokens, privately preview a theme on the real signup page,
duplicate it, restore supplied presets, and activate an approved result. The
system does not accept arbitrary administrator-authored CSS. This supports safe
experimentation now and a clean hand-off to professional designers later.

## 2026-07-16 — Keep brand and editorial wording out of public templates

Reusable challenge identity, homepage introduction, joining steps, calls to
action, and participant terminology are managed through the singleton Branding
record with environment-backed defaults. Themes control presentation only.
Generic interface instructions, validation messages, accessibility labels, and
administrative controls remain version-controlled application text.

## 2026-07-16 — Run updates require explicit human approval

Each encoded upload is an immutable, complete cumulative snapshot identified by
the mod-generated run ID. Uploading and decoding a snapshot must not add to,
replace, or otherwise alter canonical approved run data.

The review system compares a pending submission with the latest approved
snapshot for the same run. Previously approved daily data that has changed must
be prominently highlighted alongside other validator findings, including
whether the run was opened in debug mode. Validators classify and explain
findings for moderators; they never approve submissions automatically.

Only an authorised moderator's explicit approval applies a submission to the
canonical run data. Denied, invalid, older, duplicate, and superseded
submissions remain immutable audit records and do not become comparison
baselines. Approval and denial record the moderator, timestamp, and decision
reason, and applying an approval must be transactional.

## 2026-07-17 - Use a constrained, reusable page system

Public editorial content will evolve through backend-managed Pages assembled
from ordered, approved section types. Editors may change content, order sections,
and hide sections, but cannot enter arbitrary HTML, CSS, or JavaScript. Responsive
layout and accessibility remain responsibilities of the version-controlled
section templates.

The existing homepage is the first managed page and is seeded automatically from
the previous Branding content without changing its public presentation. Branding
retains global identity, theme selection, and shared terminology. Page-specific
copy belongs to Pages. The old homepage fields remain temporarily as migration
and startup fallbacks, but are no longer presented in the Branding editor.

Signup, authentication, participant accounts, privacy, and administration remain
structured application screens rather than editable page-builder content. The
architecture should favour reuse by future Sentinel Tech websites, while new
components are added only for proven Rat Race requirements rather than attempting
to build a general-purpose WordPress replacement now.
