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

## 2026-07-18 - Keep brand images optional and deployment-specific

Branding provides separate managed slots for a header logo, favicon, social
sharing image, homepage feature image, and decorative background image. Every
slot has its own enable switch, so an uploaded asset can be hidden without being
deleted and the public website always retains a text or theme fallback.

Uploaded files live in deployment media storage and are not committed to Git or
silently reused by another website. This keeps the reusable website framework
generic and makes the Rat Race operator responsible for supplying only assets it
is entitled to use. Media storage must be persistent and included in deployment
backups.

The Rat Race footer includes configurable acknowledgement text and an external
link to The Indie Stone's terms. This is distinct from the non-affiliation
disclaimer and may be disabled or changed through Branding if the applicable
terms or attribution wording change.

## 2026-07-18 - Manage uploaded images through a reusable media library

Uploaded website images are reusable records with a friendly editable name and
their original filename retained as metadata. Administrators choose existing
images for Branding rather than uploading a separate copy into every image slot.
The Branding image picker supports immediate validated multi-file upload with
per-file previews and feedback. Assigning a selected image to Branding remains a
normal saved form change. Images that are currently in use cannot be deleted.

## 2026-07-18 - Keep operational website settings superuser-only

Deployment-wide safety limits belong in a singleton Website Settings record
rather than being duplicated in templates or JavaScript. These settings are
available only to superusers under Website Administration because changing them
affects every editor and may alter storage, performance, or security exposure.

The maximum individual image upload size is the first managed setting. Browser
feedback and server-side validation both use the same stored value, with a safe
5 MB fallback while the database is unavailable during initial setup.
## Branding image presentation controls

- Uploaded images remain reusable source assets. Visual adjustments are stored as branding configuration and do not modify the original files.
- Background images support opacity, theme overlay, saturation, brightness, contrast, position, scale and fixed or scrolling placement.
- Homepage feature images support crop or contain fitting, standard, natural, short, tall or custom heights, and a selectable focal position.
- Existing sites retain the previous presentation by default: a covering fixed background, 28% theme overlay, neutral filters, and a feature image constrained to a maximum height of 24rem.

## 2026-07-19 - Compose pages from responsive sections and approved blocks

The public page system uses a constrained hierarchy: a Page owns publishing,
navigation and its default content width; ordered Sections may override that
width and select an approved responsive column layout and background treatment;
Blocks provide content inside those sections. Application features such as
signup, accounts, submissions and leaderboards remain code-controlled components
that may be placed by approved section types rather than recreated by editors.

Pages support narrow, standard, wide and full-width content. Sections may inherit
that setting or override it, and may extend their background to the viewport
edges while keeping their content constrained. Column layouts automatically
collapse to one column on small screens. This gives editors meaningful layout
control without exposing arbitrary HTML, CSS, absolute positioning or a fragile
freeform canvas.

The existing Section Item records are the first reusable block type and remain
compatible with the seeded homepage. Future block types should be added only
when a real content need is identified and must provide safe validation,
responsive rendering and accessible markup in version-controlled templates.

## 2026-07-21 - Pages own managed public navigation

Public editorial navigation is configured with the Page records it represents:
each published page may supply a navigation label, visibility, and order. Managed
pages use `/pages/<slug>/`, protecting code-controlled application routes from
editable slug collisions. Home remains at `/` and cannot be deleted or renamed.
Sign-up, authentication, and participant-account controls remain code-controlled.

Superseded by the hierarchical navigation decision below.

## 2026-07-21 - Separate page addresses from hierarchical navigation

Page content, canonical public addresses, and menu placement are separate
concerns. Pages use editable root or nested paths, while Navigation Items form
an ordered tree of links and non-clickable headings with a maximum depth of
three. The public menu provides desktop dropdowns and explicit mobile expansion.
Application routes are reserved and always take precedence over managed paths.
Legacy `/pages/<slug>/` links permanently redirect to canonical Page addresses.

## 2026-07-24 - Separate website identity from streaming connections

A Participant is the enduring Rat Race account. Twitch and YouTube are optional
connected streaming identities owned by that account, and a participant may
connect either or both. Provider email matches must never silently merge local
accounts.

The first integration milestone is channel linking and selection of recent
stream evidence for submissions. Twitch or Google alternative sign-in may follow
after linking, unlinking, collision handling and recovery behaviour are proven.
Google is the authentication provider for YouTube, so public wording distinguishes
**Continue with Google** from **Connect YouTube**. Full requirements and the
intended implementation order are recorded in `docs/STREAMING_INTEGRATIONS.md`.

## 2026-07-24 - Versioned Project Zomboid catalogue

Stable identifiers in run exports remain immutable evidence. Human-readable
names, categories, icons, aliases and game-version applicability live in a
separate website catalogue and may be corrected without rewriting submissions.
Unknown or ambiguous identifiers remain visible and are never guessed.

The administrator portal exposes this data under **Project Zomboid Catalogue**.
A scoped **Zomboid Integration** role may maintain it without participant or
website-configuration permissions. The catalogue schema is recreated by Django
migrations, while the maintained Build 42.19 baseline is stored as versioned
JSON and imported idempotently with `manage.py import_zomboid_catalogue`.

## 2026-07-24 - Use official streaming-provider brand assets

Streaming-channel rows and provider-specific actions use the supplied official
Twitch Glitch and YouTube icon PNGs rather than approximate glyphs. Both assets
retain their original transparent source canvases. CSS presents them through
fixed-width icon slots and crops the YouTube canvas at display time, keeping row
labels and actions aligned without modifying the source artwork.

## 2026-07-25 - Link Discord as an optional identity

Discord is an optional connected identity, not an alternative Rat Race account
or a streaming-evidence provider. The first milestone requests only Discord's
`identify` OAuth scope and stores the immutable Discord user ID, current display
metadata, and encrypted OAuth credentials. It does not install a bot, inspect
servers, request email access, or silently merge participant accounts.

## 2026-07-25 - Use one persistent Save action in administration

Backend editing forms expose one action labelled **Save**. Its contract is to
save the current record and continue editing it, including when the record is
first created. The alternative Django admin actions **Save and add another**,
**Save and continue editing**, and the redirecting plain **Save** are not shown.
Save is disabled when the displayed state matches the saved state, activates
when a change is made, and returns to disabled after a successful save.
Purpose-specific workflow actions such as approving or declining a submission
remain distinct from ordinary form saving.
