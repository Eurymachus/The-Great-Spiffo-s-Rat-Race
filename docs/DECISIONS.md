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

## 2026-08-01 - Use tgsrr.com as the public domain

The project has purchased `tgsrr.com` through Spaceship.com. Spaceship is the
domain registrar, and its website is the current place to manage DNS records and
other domain settings. This settles the previously pending public-domain choice
and supersedes the earlier assumption that Cloudflare would necessarily provide
authoritative DNS. Hosting, HTTPS, traffic protection and other production
services remain separate deployment decisions.

## 2026-07-13 — Qualify the word “official”

The website and mod are official to The Great Spiffo's Rat Race community
challenge. They are not official Project Zomboid or The Indie Stone products.
Public wording must make that distinction clear and avoid implying endorsement.

## 2026-07-14 — Participants are permanent login accounts

Signup creates a participant with a public nickname, private email login, and
securely hashed password. Verification activates the account. Administrators may
promote that same account to Workshop Mod Approver, Run Submission Approver,
Moderator, or Challenge Administrator and
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

## 2026-08-03 - Limit active runs per participant and challenge mode

Each Challenge Mode owns a configurable maximum number of active runs per
participant, defaulting to one. The limit counts active run identities, whether
their first submission is pending or approved. A later submission for the same
active run is an update and does not consume another slot.

A participant may deactivate their own active run without moderator review.
Deactivation is irreversible: the run becomes Abandoned, any pending submissions
for it are declined, later exports for that run ID are rejected, and its active
slot becomes available immediately. The participant interface must show an
explicit confirmation warning before applying this action.

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
names, typed metadata, icons, aliases and game-version applicability live in a
separate website catalogue and may be corrected without rewriting submissions.
Unknown or ambiguous identifiers remain visible and are never guessed.

The administrator portal exposes this data under **Project Zomboid Catalogue**.
A scoped **Zomboid Integration** role may maintain it without participant or
website-configuration permissions. The catalogue schema is recreated by Django
migrations, while the maintained Build 42.19 baseline is stored as versioned
JSON and imported idempotently with `manage.py import_zomboid_catalogue`.

## 2026-07-28 - Import typed catalogue data from the installed game

The common Catalogue Entry is deliberately a lean versioned identity and
resolver layer. It owns kind, stable ID, display name, version applicability,
activation and shared presentation identity. Kind-specific classification and
gameplay metadata belong to one-to-one detail records; aliases and assets remain
shared relationships. A detail table is added when a kind has meaningful
structured metadata, not merely to mirror every possible kind.

Traits, occupations, skills, animals and Rat Race deliverables currently have
typed detail records. In particular, Project Zomboid's internal skill parent is
stored as the skill's `category` on Skill Details rather than as a generic
Catalogue Entry category or a misleading website `parent_skill_id`.

`manage.py import_pz_catalogue --game-version <version>` reads Project Zomboid's
generated character definitions, English translations and decompiled perk
registration data from an explicitly selected installed build. It updates the
catalogue idempotently and never infers a display identity from an image
filename. Every discovered icon receives a deterministic asset relationship.
Loose source images are copied into managed deployment media; texture-pack-only
art retains its exact PZ texture key until an approved pack-extraction or
supplied-asset workflow exists. Contextual screenshots remain editorial media,
not automatically guessed catalogue icons.

## 2026-07-28 - Keep animal evidence raw and taxonomy website-owned

The mod exports Project Zomboid's authoritative raw animal type without
normalising its species or life stage. The website catalogue maps known raw
identifiers to a display name, stable species identity and optional life stage.
This permits species- and stage-based presentation without changing historical
evidence or the export contract.

Unknown and modded animal identifiers remain valid raw evidence and resolve as
unclassified; the website must not guess a species from an unfamiliar name.
The maintained Build 42.19 catalogue initially includes the known baby-animal
identifiers `rabbitkit`, `chick`, `lamb`, `piglet` and `calf`.

## 2026-07-28 - Keep Steam authentication outside the web process

The authoritative catalogue source is a full authenticated Project Zomboid
installation maintained by a restricted host service account. SteamCMD's cached
login session remains in its protected `config.vdf`; Steam passwords, Steam
Guard codes and persistent login material are never stored in Django or Git.

The super-admin records source health and auditable update jobs and receives
notifications for build changes, failures and required reauthentication.
An HTTP admin action and the scheduler may only enqueue an auditable update job.
A separately supervised worker claims jobs and runs SteamCMD through fixed
host-side arguments. Duplicate queued/running work is suppressed. Updated game
files produce a reviewable catalogue proposal rather than silently changing
live catalogue presentation.

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

## 2026-07-25 - Map raw challenge evidence on the website

The mod exports the exact Project Zomboid challenge ID and game-mode name as
objective evidence inside the format-3 schema-1 projection. It does not classify
a run as official or unofficial. The website owns editable challenge-mode
display names, aliases, ordering, activation, and grouping.

Every submission preserves the raw challenge evidence and an optional mapping to
a managed Challenge Mode. A run separately preserves its first reported
challenge evidence and the current approved snapshot. Unknown IDs are accepted
and shown as unmapped. When an existing save exposes an empty ID, the website may
map its exact game-mode name while preserving the empty raw ID; exports predating
the entire field remain legacy/unspecified.
Changing challenge ID during a run is a dangerous review finding and prevents
approval. Submission moderation, run eligibility, challenge mode, and lifecycle
remain separate concepts. The existing run approval label is **Verified**, not
**Official**, reserving official/unofficial for a future organiser-owned
eligibility decision.
## 2026-07-25 — Live participant notifications

- Notification rows in the database remain authoritative.
- ASGI Server-Sent Events carry only a `notifications-changed` invalidation;
  browsers then fetch the authenticated JSON summary.
- A visible signed-in page falls back to a 60-second summary poll if SSE is
  unavailable, so missed live delivery does not lose notifications.
- Toasts show the notification title but not its message body. Initial page
  loading does not raise a toast.
- WSGI remains supported for ordinary requests but the live endpoint refuses to
  hold a WSGI worker. Local and live SSE operation uses
  `config.asgi:application`.
- The initial database-checking stream is limited to local/small single-process
  use. Multi-worker production requires a shared event bus such as Redis.
# Website-triggered decompilation uses validated immutable outputs

- The super-admin website queues decompilation; the web process does not run
  Java or Vineflower inline.
- A separately supervised operations worker runs a pinned Vineflower release.
- Every result is written to a new build/job directory and validated before the
  reference source points to it. The previous output remains available for
  rollback.
- The installed Steam build and active decompiled build are tracked separately,
  making a required rebuild explicit after a game update.
- The decompiler JAR is provisioned and checksum-verified on each host rather
  than committed to Git.

## 2026-07-29 - Keep destructive run-data reset explicit and isolated

Pre-launch contract changes may invalidate all development run records. A
superuser-only System Operations danger zone may therefore purge the complete
run-data graph after an exact typed confirmation. The transaction removes
challenge runs, their immutable submissions, and submission-category
notifications together. It must not remove participants, authentication data,
platform integrations, challenge configuration, catalogue data, website
content, or site configuration. This is an explicit maintenance operation, not
a normal run-moderation bulk action.

## 2026-07-29 - Reconcile catalogue artwork after approved imports

- Installed Project Zomboid data remains authoritative for catalogue identity,
  typed details and deterministic texture keys.
- Approving a reviewed catalogue snapshot queues PZwiki artwork reconciliation
  in the existing background operations worker; HTTP requests do not perform
  network downloads.
- PZWiki is the presentation authority for supported catalogue artwork,
  including traits, occupations and item artwork such as weapons, tools, books
  and magazines. Missing artwork is reported rather than guessed.
- Asset records keep the authoritative game texture evidence separate from the
  provenance of the image currently served. A packed texture reference records
  that the game asset exists but does not displace a usable PZwiki image.
- Project Zomboid updater runs record unpacked or packed game provenance but do
  not replace PZWiki presentation artwork. The PZWiki reconciliation may replace
  provisional game-sourced presentation files. Manual overrides remain
  protected and require an explicit administrator decision to replace.
- The reconciliation may be queued automatically after catalogue approval or
  manually from the Project Zomboid reference source admin page. Shared Wiki
  filenames are downloaded once per run and reused across matching entries.
- Catalogue approval and artwork enrichment use separate records. Catalogue
  import reviews record only the reviewed game-data decision. Each PZWiki
  reconciliation is a dedicated background job with its own trigger, requester,
  lifecycle timestamps, status and summary. A wiki failure is visible and
  retryable without changing or rolling back the approved catalogue review.

## 2026-07-29 - Model Project Zomboid items by evidence and capabilities

- Every Project Zomboid item is one `item` catalogue entry identified by its
  exact full item type, such as `Base.BoneClub`.
- `ItemDetails` owns item-specific data; the shared catalogue entry remains the
  lean identity, version, alias and asset lookup layer.
- Exact Project Zomboid `DisplayCategory` identifiers resolve through the
  dedicated `ItemDisplayCategory` table, which owns their translated display
  names. Items reference those records rather than copying category strings.
- A deterministically identified weapon skill references the existing
  `SkillDetails` record. Unknown or insufficient weapon evidence leaves the
  relationship empty; it is never guessed from a display label.
- Exact generated item fields are retained as raw evidence. Website
  capabilities are deterministic interpretations of that evidence and may
  overlap: an item can simultaneously be a tool and weapon, and literature can
  additionally be a book or magazine.
- Separate weapon, tool, literature or collectible catalogue entries are not
  created for the same item. Future presentation and statistics query item
  capabilities and detailed fields instead.
- Better Item Info is a useful behavioural reference, but the website derives
  its catalogue from the installed Project Zomboid definitions rather than
  importing another mod's authored output.

## 2026-07-30 - Keep public navigation available on long pages

- The desktop navigation and account controls form a sticky full-width bar at
  the top of the viewport once the page header scrolls away.
- On compact layouts the hamburger, account, and notification controls remain
  together in a sticky bar.
- On compact guest layouts, labelled Sign In and Sign Up actions sit directly
  beside the hamburger. The expandable navigation contains only managed site
  links.
- The compact bar hides when the reader scrolls down and returns when they
  scroll up, reducing obstruction without making navigation hard to recover.
- An open navigation, account, or notification panel keeps the compact bar
  visible so active interaction is never dismissed by incidental scrolling.
- Reduced-motion preferences disable the bar transition.

## 2026-07-30 - Separate public event visibility from participant analysis

- The landing page, a top-ten summary, the current leaderboard, and the Mods
  catalogue are publicly visible. These views help
  spectators follow the event and prospective participants understand it
  before creating an account.
- The public leaderboard shows each participant's active personal best. Runs
  that are inactive are not valid for the current leaderboard, and the website
  does not maintain separate current leaderboards for active and inactive runs.
- Signed-in participants may browse a filterable historical view containing all
  runs, including inactive runs.
- Individual run data, detailed statistics, and analytical charts are available
  only to signed-in participants.
- Future record notifications are opt-in website notifications, not email. A
  participant may be notified when someone exceeds a previous Rat Race record.
- Live Rat Race stream or channel embeds remain a possible public feature, not
  a settled requirement.

## 2026-07-31 - Register code-managed pages alongside editorial pages

- The Website Content administration area distinguishes editorial Pages from
  Code-managed Pages.
- A Code-managed Page represents a stable application route whose templates,
  queries, access control and behaviour remain implemented in version-controlled
  code. Administrators do not recreate or edit that functionality as page
  content.
- Each registered route has a stable code key, display identity, description,
  availability state and code-enforced audience such as public, signed-in
  participant or staff. Administration may not weaken its security boundary.
- Navigation placement remains separate from page availability. A Navigation
  Item may target either an editorial Page or a registered Code-managed Page,
  while address-driven destinations such as an individual run need not appear
  in navigation.
- Known application routes are installed deterministically so their registry
  records cannot drift from the routes implemented by the website.
- This registry is the foundation for replacing the current test navigation
  with the launch information architecture.

## 2026-07-31 - Use permanent team voting for mod policy

- Mod review is a permanent team workflow used for both the historical mod list
  and future participant requests submitted with a Steam Workshop link.
- The active official policy uses the concise states `Allowed`, `Disallowed`
  and `Pending review`. The active game is implied, so these states are not
  labelled Stable in ordinary administration or public presentation.
- Every imported historical mod separately records its `Previous Unstable
  ruling` as `Allowed`, `Disallowed`, `Not reviewed` or `Unknown`. This is
  provenance for reviewers, not the current official ruling.
- An optional `Unstable ruling notes` field may preserve a known historical
  reason without changing the active ruling.
- Eligible team members vote `Allow`, `Disallow` or `Discuss`. Not voting is
  sufficient when a team member does not wish to take a position, so there is
  no separate Abstain vote.
  Individual votes and reasons remain attributable. Rejections and requests for
  discussion should include a concise reason.
- Voting produces a recommendation and disagreement queue. It does not directly
  change public policy. An authorised reviewer records the final ruling,
  reviewer, timestamp and rationale after considering the team result.
- The final reviewer may start from a reusable Allowed or Disallowed public
  rationale template. Its text is copied into the ordinary rationale field for
  review and editing, and the confirmed wording is stored rather than a template
  identifier. Public wording references policy and does not expose individual
  votes or internal discussion.
- The public Mods page exposes only the active official ruling and appropriate
  public rationale. It is one searchable catalogue with ruling filters for
  Allowed and Disallowed rather than separate pages. Individual votes, internal
  discussion and historical Unstable provenance remain team-facing.
- Only mods explicitly listed as `Allowed` or `Required` may be used in a Rat
  Race run. `Disallowed` and unlisted mods cannot be used. Cosmetic or
  quality-of-life characteristics guide review decisions but do not exempt an
  unlisted mod from review and publication in the catalogue.
- A `More Info` action opens an in-page rules modal. It explains that an eligible
  mod must be purely cosmetic and must not provide information unavailable in
  the unmodded game, using generalised examples without linking to individual
  Workshop items.
- The official TGSRR mod is a distinguished `Required` entry. It remains pinned
  above the ordinary mod results and is visually highlighted so participants do
  not mistake it for an optional Allowed mod.
- Selected `Allowed` mods may also carry a separate `Recommended` flag. They
  appear in a curated section above ordinary mod rulings and are not duplicated
  in the results below. Recommended is presentation guidance, not an additional
  official ruling, and a Disallowed mod cannot remain recommended.
- The Mods page has a `Submit for review` action at the top right. It opens an
  in-page modal where a participant enters a Steam Workshop item ID and a
  required `Reason for adding this mod`.
- Before submission, the website validates the Workshop ID format, confirms the
  item exists through Steam, and checks the local catalogue for an existing
  Allowed, Disallowed or pending record. Existing rulings are shown instead of
  creating a duplicate request.
- A valid new request enters `Pending review` and the permanent team voting and
  authorised final-review workflow. Participant submissions never publish an
  Allowed or Disallowed ruling directly.
- The modal has a clear Submit action and reports field, Steam-validation and
  duplicate errors without discarding the participant's entered reason.
- Existing mods should be imported with their historical provenance before
  ratification. The voting interface was subsequently reprioritised and
  implemented on 1 August 2026.
- On 1 August 2026 the approval journey was reprioritised. The existing mod table
  remains temporary development and import data and will be wiped before the
  completed workflow is tested from a clean state.
- Approval authority is split into two named roles. `Workshop Mod Approver`
  grants access to the mod queue and team voting but not final publication.
  `Run Submission Approver` grants access to review, approve and decline run
  submissions but does not grant mod-voting authority. The former generic
  `Approver` role is retired and receives no permissions after role bootstrap;
  its members must be deliberately assigned to the appropriate scoped role.

## 2026-08-04 - Import the final Unstable legacy datasets after deployment

- The Legacy Leaderboard and Legacy Hall of Fame are separate public views of
  one legacy run per historical participant. The Leaderboard shows the current
  approved submission for active runs. The Hall of Fame shows the best approved
  submission across all legacy runs.
- The final cutoff date has not yet been selected. Production may therefore be
  deployed with an empty legacy dataset and populated later through a protected
  super-admin import screen.
- The importer accepts two CSV exports, validates both without changing public
  data, presents row counts, merged-run counts and warnings, then requires an
  explicit confirmation before replacing the imported dataset.
- Rows are merged by a normalized historical participant name. A participant
  present in the Legacy Leaderboard begins Active. A Hall-of-Fame-only record
  begins Inactive. Team-controlled lifecycle changes remain separate from the
  imported results.
- Imported streaming-channel or source-link columns are ignored and never
  stored. Until a future claim is approved, the historical participant name is
  displayed. After approval, the current participant nickname and their chosen
  primary streaming channel provide public identity and channel linking.
- Each imported result is retained as an approved legacy submission. The
  import record preserves the original CSV texts, filenames, hashes, preview,
  uploader and import time for auditability.
- Historical Unstable data remains separate from verified website
  `ChallengeRun` and `RunSubmission` records. Missing exports, character names,
  event ledgers and review timestamps must not be invented.
- The future claim and participant legacy-submission journeys remain approved
  design work separate from the importer implementation.
- An authenticated participant may submit one legacy run claim for team review.
  Claim details are immutable in administration and reviewed through explicit
  Approve or Decline actions rather than a generic edit form. Decline requires a
  retained reason; both decisions record the reviewer and time and notify the
  participant. Approval links the historical run to the current participant,
  after collision checks prevent either side from being linked elsewhere.
- Participants with a pending or declined claim see that state on their
  dashboard. An approved claimant instead sees a dedicated Legacy Rat Race
  panel below a clear archive divider. It shows one result: the current
  Leaderboard submission when the legacy run is Active, or the Hall of Fame
  best when it is Inactive or Deceased. A lifecycle tag identifies that state.
  These Unstable results remain visually and logically separate from verified
  Stable runs.
- Legacy ranking tables show the Claim column only while the signed-in
  participant may still need the claim journey. Once an approved claim or linked
  legacy run exists for that participant, the entire Claim column and its
  controls are hidden.
- Legacy ranking tables label approval provenance as `Last approved`, not
  `Last verified`. Imported results use the confirmed import approval time;
  later participant submissions use their own approval time. Missing approval
  provenance is shown as `Not recorded` rather than left blank. Stable ranking
  tables continue to use `Last verified` for approved signed run exports. The
  legacy column shows only the short approval date; Stable verification may
  continue to show both date and time.
- Only the participant linked through an approved claim may submit an update to
  an Active legacy run. The required result fields are character name, zombie
  kills, Time Survived, Level 10 skill count, completed outposts and whether the
  run remains Alive or is Dead. Evidence is a connected Twitch or YouTube VOD,
  or a manually entered VOD URL, with optional start and end offsets.
- Time Survived accepts either `YY:MM:DD:HH` or a word form such as `1 year 5
  months 20 days 6 hours`. The website retains the participant's original text,
  normalizes the full value and calculates decimal days. The interface provides
  a concise tooltip and live interpretation; moderators verify the evidence and
  do not perform the conversion.
- Participant legacy progress is calculated automatically using the same public
  weighting as Stable rankings: progress toward one million kills supplies 50%,
  progress through 13 outposts supplies 25%, and progress through 35 Level 10
  skills supplies 25%. Each category is capped at completion.
- Only one participant update may be pending for a legacy run. Approval makes
  the submission current, makes it the Hall of Fame best only when its progress,
  kills, outposts, skills and survival time outrank the existing best, and marks
  the run Deceased when death is reported. Decline requires a retained reason.
  Both decisions record the reviewer and time and notify the participant.

## 2026-07-31 - Keep the public leaderboard concise and gate survivor details

- The public current leaderboard is sorted by weighted challenge completion
  using the approved snapshot's partial category progress. Zombie kills provide
  50% of the score; outposts and skills provide 25% each.
- Its main presentation begins with a compact primary-stream icon and includes
  rank, racer and survivor identity, total zombie kills, outposts completed,
  maxed skills, in-game day and the last verified update time.
- Participant and survivor identity are separate leaderboard columns. The
  participant name will link to a public participant profile once that page's
  public-data contract is settled. The survivor link retains the signed-in
  detail gate. The Build column uses the PZWiki Ball-peen Hammer artwork as its
  heading and each row uses that survivor's starting occupation icon as the
  control that opens the starting-build modal. Custom occupations use the
  website-owned Custom Occupation icon.
- A participant may select one connected account as their `Primary streaming
  channel`. The setting is provider-neutral so Twitch, YouTube and later
  supported streaming providers use the same relationship.
- The leaderboard icon uses the selected provider's official mark, has an
  accessible channel label, and opens the participant's public channel in a new
  tab. A participant without an eligible primary channel has no linked icon.
- Only a currently connected streaming account owned by that participant may be
  selected. Disconnecting or invalidating the selected account clears or
  disables the primary relationship safely; the website never guesses a
  replacement channel.
- The provider icon may present cached `Live`, `Offline`, `Unknown` or `Stale`
  status. A provider failure becomes Unknown rather than falsely reporting
  Offline, and streaming status never affects challenge ranking.
- Twitch live status uses verified `stream.online` and `stream.offline` EventSub
  notifications for prompt changes, backed by periodic batched reconciliation,
  startup reconciliation and a stale threshold. Other providers implement the
  same contract through their own adapters when supported.
- Live-status changes emit only a public-safe leaderboard invalidation marker.
  Open leaderboard pages fetch refreshed public data through the same SSE and
  visible-tab polling pattern used elsewhere; browsers never query providers
  directly.
- Outposts and maxed skills should be presented as progress counts, such as
  `8 / 13` and `12 / 35`, where the total improves comprehension.
- Participant and survivor remain separate columns. The survivor identity links
  to the individual survivor record.
- Detailed character and run information remains visible only to signed-in
  participants. It does not expand the public leaderboard table.
- Selecting a survivor while signed out opens an access prompt rather than
  navigating away immediately. The prompt heading is `Sign in to view survivor
  details` and explains that a Rat Race account is required to view detailed
  character and run information.
- The prompt offers `Sign Up`, `Sign In` and `Close`. Sign-up and sign-in preserve
  the selected survivor URL as the return destination after authentication.
- Each leaderboard entry also offers a compact `Show Build` control beside the
  survivor identity. It does not add trait columns to the main leaderboard.
- For signed-in participants, `Show Build` opens an in-page modal showing the
  survivor name, starting profession, starting positive and negative traits,
  and starting skill boosts when included. The modal also links to the full
  survivor record.
- The build is sourced only from the canonical approved run snapshot. Starting
  choices remain distinct from currently effective traits so acquired or
  removed traits never rewrite the original build.
- Desktop and compact layouts use the same accessible modal content rather than
  relying on hover-only behaviour.
- Desktop and mobile use the same compact columnar leaderboard. Narrow screens
  scroll the leaderboard panel horizontally, following the survivor skills-list
  pattern, rather than transforming each entry into a card.
- For signed-out visitors, `Show Build` opens the access prompt with the heading
  `Sign in to view survivor builds`. It explains that an account is required to
  view the starting profession and traits, and offers `Sign Up`, `Sign In` and
  `Close` while preserving the intended survivor destination.

## 2026-08-02 - Build rankings as a configurable managed-page block

- Managed Pages may include a reusable `Ranking Table` block backed by canonical
  run and challenge data. It is not limited to hard-coded Current Leaderboard,
  Hall of Fame or Legacy Hall of Fame presets.
- The block exposes a bounded, validated query configuration. Administrators may
  filter by challenge mode, game or challenge build, run lifecycle and selected
  participants. Appropriate filters support multiple selected values through an
  add-and-remove control rather than a browser-native multi-select box.
- Values selected within one filter use OR semantics. Different filters use AND
  semantics. For example, Standard mode AND (Active OR Completed) is valid. The
  editor displays a human-readable summary of the effective query.
- Result selection may choose every eligible run, the best eligible run per
  participant or the latest eligible run per participant. The block also
  controls the primary ordering, deterministic tie-breaking, maximum row count,
  visible column set and column order.
- Display controls may enable the heading, introductory copy, score-weighting
  note, starting-build action and detailed-run links. Presentation choices never
  alter ranking eligibility or canonical values.
- Django owns all query construction, scoring, eligibility, privacy and link
  gating. Editors cannot enter arbitrary database queries, expose pending or
  declined submissions, include unapproved snapshots or bypass signed-in run
  detail restrictions.
- The intended initial configurations are: Current Leaderboard for active runs,
  Hall of Fame for each participant's strongest eligible Stable terminal run,
  and Legacy Hall of Fame for imported Unstable-build personal bests. Legacy
  results remain visibly and logically separate from Stable rankings.

## 2026-08-05 - Treat participant history as a focused signed-in profile

- A signed-in Rat Racer may open another participant's profile by selecting
  their linked name in a Stable or claimed Legacy ranking table.
- The profile shows the participant's nickname, approved avatar, join date,
  Personal Best, Active Runs, Past Runs and claimed Legacy Rat Race record when
  available. Individual Stable runs link to their approved detail pages.
- The profile does not expose submission history, pending or declined
  submissions, evidence review, or moderation details.
- Navbar participant search is a later nice-to-have discovery layer. Ranking
  links are sufficient for the initial profile journey.

## 2026-08-06 - Lead the homepage with community scale and clear destinations

- The homepage does not embed a ranking table. Rankings remain available as
  dedicated managed pages and navigation destinations.
- An Alternate surface - full width section treatment gives the Community
  Statistics block an edge-to-edge fill with top and bottom rules only. It
  communicates the current scale of the challenge using only verified runs with
  approved canonical submissions.
- Statistics are selected and ordered from a code-owned metric catalogue.
  Editors may control presentation but cannot author database queries or include
  pending, declined or unverified submissions.
- `Rats in the Race` is the public label for currently active verified runs. It
  is not repeated as a separate Active Runs or Survivors Still Running metric.
- Homepage journey prompts use the dedicated Call-to-Action Cards block. Each
  card is one complete accessible link with a heading, concise explanation,
  alt text and validated destination rather than presenting passive numbered
  registration steps or a separate button.
# 2026-08-09 - Publish exploit guidance beneath Rules

- Exploit guidance is a dedicated managed public page at `/exploits/`, not a
  hard-coded template or an extension of the Mods catalogue.
- The Exploits navigation item sits under Rules immediately after Mods.
- The page publishes the general fair-play boundary, evidence expectations for
  accidental discovery and a managed area for specific rulings.
- An exploit or edge case is not approved merely because no specific ruling has
  been published. Rat Racers should ask publicly before relying on uncertain
  behaviour in an official run.
# 2026-08-09 - Managed tab sections support horizontal and vertical orientation

- Tab orientation is configured at section level, independently of tab count and content.
- Existing and newly created tab sections default to horizontal orientation.
- Vertical tabs use a left-hand rail on wider layouts and return to the horizontal mobile scroller on narrow layouts.
- Both orientations retain the existing card styling, fade transition, URL fragments, and accessible tab semantics.
