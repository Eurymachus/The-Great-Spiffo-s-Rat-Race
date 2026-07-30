# Website: Current Focus

## Branch and worktree

- Development branch: `codex/website-dev`
- Website worktree: `The Great Spiffo's Rat Race - Website`
- Project Zomboid mod development is isolated in its own worktree and branch.

## Goal

Launch a small public website where prospective Rat Race participants can reserve
a nickname using a verified email address.

The Project Zomboid catalogue remains a lean lookup and resolver layer.
Kind-specific classifications and gameplay fields belong to typed detail
records, while aliases and assets remain shared catalogue relationships.

## Done When

- The registration page is publicly available.
- Participant nicknames are unique.
- Email addresses are verified.
- A human-verification check protects registration.
- Registrations can be viewed and administered securely.
- Basic privacy, deletion, and unsubscribe needs are covered.

## Implemented

- Permanent participant accounts using nickname, email, and password.
- Self-declared 18+ participation eligibility with versioned confirmation and no
  collection of dates of birth or identity documents.
- Email verification with pending, verified, expired, disabled, and removed states.
- Participant login and secure password recovery.
- Participant account summary, password change, staff administration link, and
  secure logout controls.
- Draft privacy notice, participant JSON data download, and authenticated
  account-closure requests visible to administrators.
- Central environment-backed `SITE_*` configuration for public operator identity,
  company details, privacy contact, eventual public URL, and brand fallbacks.
- Singleton Branding backend with safe environment defaults, immediate
  public rendering, and a scoped Branding Administrator role.
- Optional backend-managed header logo, favicon, social sharing image, homepage
  feature image, and decorative background image. Each slot has an independent
  enable switch and retains its text or theme fallback when disabled.
- Reusable image library with thumbnails, friendly names, original-file metadata,
  immediate validated multi-file uploads, and image selection from Branding.
- Configurable public attribution to The Indie Stone's terms, kept separate from
  the ordinary non-affiliation disclaimer.
- Managed visual themes with three editable presets, private signup-page preview,
  duplication, restoration, activation, and validated design controls.
- A protected backend-managed Homepage assembled from ordered, reusable,
  responsive sections without administrator-authored HTML or JavaScript.
- Flat backend-managed public pages at protected `/pages/<slug>/` addresses,
  with page-owned navigation labels, visibility, and ordering.
- Consistent primary navigation, authenticated-route redirects, accessible form
  metadata, keyboard focus treatment, and responsive local journey checks.
- Administration editing forms use one **Save** action that saves in place and
  continues editing. It activates only when the form has unsaved changes;
  workflow actions such as submission review remain separate.
- Registry-backed administration is presented by concern without moving its
  database models: Participant administration, Challenge configuration, Run
  moderation, and Platform integrations.
- A superuser-only System Operations danger zone previews and atomically purges
  every challenge run, run submission, and submission notification after exact
  typed confirmation. Participant accounts, platform integrations, challenge
  modes, catalogue data, managed content, and site configuration are preserved.
- Privileged, confirmation-protected closure processing with non-personal
  closure receipts and a documented nullable owner for future independent runs.
- Cloudflare Turnstile integration using official test credentials locally.
- Cache-backed request limits for signup, resend, and password recovery.
- Administrator roles, participant promotion, status management, and CSV export.
- Local development documentation and automated test coverage.
- Mod-export ingestion into immutable, individually reviewed submissions, with
  integrity verification and explicit administrator approval or reasoned
  decline. The first approved submission officiates its run; each later approval
  alone advances the run's canonical snapshot. A later generated snapshot may
  advance with an unchanged verified ledger so current-state changes are not
  discarded merely because no new semantic event occurred.
- Current format-3 mod-export ingestion, including the signed ledger and complete
  character/trait projection, preserved on both the run and immutable submission.
  Current event-schema 2 ledgers are accepted; legacy and unknown event schemas
  are rejected. The run-snapshot projection remains schema 1. Decoder parity
  covers the mod's canonical number, map, event-metadata, framing, integrity and
  size rules, with a real current-contract mod export retained as a golden test.
- Optional raw `challenge.id` and `challenge.gameMode` evidence within the
  schema-1 projection. Exact IDs map to managed Challenge Modes; unknown IDs are
  accepted as unmapped, empty IDs may map by the exact game-mode name, and legacy
  exports remain unspecified. Starting evidence and the current approved
  snapshot are preserved separately.
- Independent run lifecycle tracking for active, deceased, abandoned, completed,
  and invalidated runs, presented as Active Runs and Past Runs on the participant
  dashboard. Lifecycle is moderator-managed until the tracker emits a terminal
  run signal.
- Public, shareable verified-run pages at UUID-based addresses. The initial
  player-facing view presents challenge progress, character traits, current
  skills in a grouped Project Zomboid-style panel using the mod's complete
  35-icon skill set, outposts, town visits, activity totals and clearly
  distinguished in-game export and website receipt timestamps without exposing
  raw run IDs, checksums or ledger hashes. Charts remain a later presentation
  layer.
- Participant notifications for submission receipt and moderation decisions,
  with ASGI/SSE live invalidation, immediate bell/dropdown refresh, unobtrusive
  title toasts, a visible-tab polling fallback, and in-place refresh of
  participant dashboard run and moderation panels.
- A dedicated Project Zomboid Catalogue administration section with stable IDs,
  display metadata, version ranges, aliases, a reusable resolver, and a scoped
  Zomboid Integration staff role.
- Super-admin Project Zomboid reference operations with short-lived Steam
  authentication, a separately supervised queue worker, installed-build checks,
  and website-triggered Vineflower decompilation. Decompiled output is generated
  into immutable build/job directories, validated before activation, and tracked
  against the installed Steam build so stale Java reference data is visible.
- Catalogue imports use a two-stage super-admin workflow. A background review
  stores the exact interpreted snapshot and clearly separates additions,
  changes, and deactivations without mutating live catalogue data. Explicit
  approval applies only that reviewed snapshot; changed build IDs or source
  paths make the review stale and require a new comparison.
- Automated Catalogue v2 ingestion from an installed Project Zomboid build for
  traits, occupations, skills and items. Generated game definitions and English
  translations populate typed detail records (costs, descriptions, XP boosts,
  exclusions, granted traits and recipes) without manual transcription.
  Items retain their exact full type (for example `Base.BoneClub`), raw item
  definition, tags, weight and texture key. Exact display-category identifiers
  and translated names live in a dedicated table, and deterministically
  resolved weapon skills reference the existing Skill Details records rather
  than duplicating strings. A deterministic
  analysis layer records overlapping capabilities rather than forcing items
  into one category: the same item may be a weapon and a tool, while literature
  may additionally be a book or magazine. Weapon categories resolve to their
  governing skill where Project Zomboid exposes enough evidence.
  Deterministic texture relationships are retained for every available icon,
  including shared item texture keys used by weapons, tools, books and magazines.
  Approval queues a background PZWiki reconciliation which uses those keys to
  import matching catalogue PNGs into managed media. PZWiki is the presentation
  authority for supported catalogue artwork; installed Project Zomboid files
  remain authoritative evidence for identity, details, texture availability and
  checksums but do not replace a served PZWiki image. Manual overrides remain
  protected. A super administrator can also queue the same reconciliation from
  the Project Zomboid reference source page. Catalogue approval and PZWiki
  reconciliation are separate operational concerns: every reconciliation has
  its own job record, trigger, lifecycle timestamps, status and final summary.
  Completed jobs also retain a structured unavailable-artwork report, grouped
  by catalogue kind and failure reason in administration, so unsupported icon
  keys and expected PZWiki files that do not exist remain directly inspectable.
  The approved catalogue review remains immutable and records only the reviewed
  game-data decision. Shared filenames are fetched once per job and reruns do
  not duplicate unchanged assets. Missing Wiki artwork is reported rather than
  guessed.
- Website-owned animal taxonomy maps known raw Project Zomboid animal
  identifiers to display names, species and life stages while preserving unknown
  or modded identifiers as unclassified evidence.
- A host-managed full Project Zomboid reference source records installed Steam
  build state and auditable update jobs. Admin and scheduler requests enqueue
  work without blocking HTTP; a separately supervised worker runs the fixed
  SteamCMD update using the host's protected cached login. Jobs record their
  trigger, requester, queue/start/finish times and result, suppress duplicate
  active work, and notify super-admins when a build changes, an update fails, or
  authentication must be renewed. Catalogue diff, review and promotion
  automation remains next.
- A provider-neutral connected streaming-account foundation for Twitch and
  YouTube, including immutable provider/channel identities, connection state,
  audit timestamps, administration and participant-facing account status.
- Production-shaped Twitch linking with encrypted rotating credentials,
  ownership proof, hourly-on-use validation, reactive refresh, explicitly
  cached recent broadcasts and clips, and immutable run-evidence snapshots for
  moderation.
- Real Twitch OAuth, channel linking, VOD/clip refresh, evidence selection,
  submission review and moderator approval verified end to end against a live
  Twitch channel on 24 July 2026.
- Twitch-side credential revocation is detected on the next validation or media
  refresh and changes the website account to Reconnect required.
- Official Twitch and YouTube brand marks shared across connected-channel rows
  and the run-submission journey.
- Optional Discord identity linking using the minimal `identify` permission,
  with encrypted credentials and participant-controlled disconnect.

Uploaded brand images live in deployment media storage rather than Git. A live
deployment must persist and back up that media directory alongside the database.

## Not Now

- Leaderboards and statistics
- Full mod integration
- YouTube OAuth linking and media retrieval.

## Future Core Deliverable: Moderated Run Updates

Run-update ingestion is deferred, but its integrity workflow is a settled
requirement:

- Every upload is a complete cumulative snapshot of one mod-generated run ID.
- Uploading creates an immutable pending submission and never changes approved
  run data automatically.
- A new submission is compared with the latest approved snapshot for that run.
- Previously approved daily data that differs in the pending snapshot must be
  highlighted clearly for moderator review.
- Automated validators, including debug-mode detection and future
  challenge-integrity checks, produce visible findings but never approve a
  submission.
- Only an authorised moderator's explicit approval may add to or replace the
  canonical approved run data.
- Denied or invalid submissions remain available as an auditable record and
  never become the comparison baseline for later submissions.

## Pending Team Decision

- Final public domain name. `spiffosratrace.com` is available and has been
  suggested, but registration is on hold until the team agrees.

## Hierarchical managed navigation

Pages now own canonical root or nested public addresses such as `/gallery/` and
`/media/gallery/`. Navigation placement is managed separately through ordered
Navigation Item records. An item may link to a Page or act as a non-clickable
heading, and may be nested to three visible levels. The public header renders
desktop dropdowns and expandable mobile submenus. Code-controlled routes remain
reserved, and provisional `/pages/<slug>/` addresses permanently redirect to a
Page's canonical address. The admin tree uses visual drag-and-drop insertion
between items: vertical movement selects the position, while moving right nests
under the nearest preceding item and moving left moves the item outward.

## Recommended next action

Run and review the catalogue-wide PZWiki artwork reconciliation, then extend
item analysis with the gameplay fields needed by kill and collectible views.

Retention automation and a final pre-launch privacy review remain required.
