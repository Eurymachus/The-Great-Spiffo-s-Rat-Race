# Website: Current Focus

## Branch and worktree

- Canonical development branch: `codex/rat-race-dev`
- Canonical local worktree: `The Great Spiffo's Rat Race`
- Website and Project Zomboid mod contracts evolve together on the unified
  development branch.
- The canonical local development runtime now lives here too. Its ignored
  `.env`, SQLite database, and media library were migrated from the obsolete
  `The Great Spiffo's Rat Race - Website` worktree on 2026-08-15. Do not start
  or update the obsolete worktree as the local website deployment.

## Goal

Prepare the public Rat Race platform for deployment. Participants can create a
verified account, submit evidence-backed runs, follow rankings, inspect approved
records, and read the managed rules, mod policy, and exploit rulings.

The Project Zomboid catalogue remains a lean lookup and resolver layer.
Kind-specific classifications and gameplay fields belong to typed detail
records, while aliases and assets remain shared catalogue relationships.

## Done When

- The production environment, database, persistent media, web process, and
  reference worker are deployed and recoverable.
- Required secrets and provider integrations pass deployment health checks.
- Registration, account, submission, moderation, ranking, Rules, Mods, and
  Exploits journeys pass a representative production-shaped acceptance test.
- Retention automation and the final pre-launch privacy review are complete.
- The final Unstable legacy dataset is imported only after the team selects its
  cutoff date.

## Implemented

- The first normalized run-authority slice now stores the approved export
  contract version, one character, selected starting traits, spawned starting
  traits, mutable current traits, and starting-location evidence on the run.
  Trait and occupation rows retain raw Project Zomboid IDs and link directly to
  catalogue entries when resolved. Starting-location rows can also link to the
  versioned geography catalogue.
- Run-submission approval now locks the submission and run, refreshes the first
  authority slice, updates the approved snapshot, and sends its notification in
  one database transaction. A forced importer failure is covered by a rollback
  test and leaves the submission received and the run pending.
- The signed-in player run page presents `Spawn choice` and `Starting location`
  from run-owned authority. Starting location is an icon-only link using the
  newest active `Base.Map` catalogue artwork, with `View map` alternative text;
  coordinates remain hidden in the presentation but preserved in the canonical
  `https://map.projectzomboid.com?{x}x{y}x{z}` destination. A random choice remains
  labelled `Random Spawn, KY` without revealing its resolved region.
- Projection schema 2 outpost imports preserve sparse current-state evidence and
  validate first completions against their sole permanent ledger events. Approval
  rebuilds only observed `RunOutpost` and `RunOutpostDeliverable` records with
  bounded lifecycle summaries, raw IDs, and nullable catalogue links. Missing
  catalogue-backed records mean unexplored or incomplete. Public run cards,
  rankings, and community outpost counts now prefer run-owned authority.
- Approved sparse skill and kill evidence now rebuilds normalized `RunSkill`,
  `RunKillSummary`, and `RunWeaponKill` authority. Missing catalogue skills and
  kill-source rows resolve to zero for presentation, while partial baselines and
  raw Project Zomboid source IDs remain stored evidence.
- A persistent production-shaped staging environment is live at
  `https://dev.tgsrr.com` from the isolated `G:\RatRace_Staging` root. It uses
  its own PostgreSQL cluster, protected configuration, filesystem state, empty
  application data and repository-controlled
  presentation. `[DEV]` titles, a persistent development/test banner,
  anti-indexing headers and a full-disallow `robots.txt` distinguish it from
  production. Only the working Graph mail integration is currently shared;
  all other external providers remain deliberately unconfigured. Release
  `1676dba` is running; its web and worker scheduled-task actions still need to
  be updated from an actual elevated Windows PowerShell session before restart
  recovery can be accepted for this release.
- Permanent participant accounts using nickname, email, and password.
- Self-declared 18+ participation eligibility with versioned confirmation and no
  collection of dates of birth or identity documents.
- Email verification with pending, verified, expired, disabled, and removed states.
- Participant login and secure password recovery.
- Participant account summary, password change, staff administration link, and
  secure logout controls.
- A versioned participant privacy notice, participant JSON data download, and
  authenticated account-closure requests visible to administrators. The notice
  identifies the configured providers and purposes, international processing,
  essential storage, automated checks, retention schedule, rights and the
  `support@tgsrr.com` contact. Staging adds a test-data warning.
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
- Managed Pages include dedicated Separator sections for intentional spacing.
  Editors may choose space only, a subtle line or an accent line, with small,
  standard or large spacing and the usual managed section widths.
- Managed sections can also contain Separator blocks for the same spacing and
  rule treatments within an individual section column.
- Existing content blocks can be dragged between sections and columns. Moves,
  removals and their resulting parent changes are saved atomically with the
  page, preventing an emptied source section from cascade-deleting blocks that
  have been moved elsewhere in the editor.
- A public managed Rules page at `/rules/` provides the Stable challenge's
  concise fair-play contract, objectives, mod policy, evidence requirements,
  bug-recovery boundary, run endings and moderation expectations. Its seeded
  sections remain fully editable through the existing page builder, and a
  top-level Rules navigation item exposes it to everyone.
- Managed Pages support Tabbed Content sections containing two, three or four
  tab panels. Each panel reuses the ordinary column block editor, so blocks can
  be added, reordered and dragged between tabs without introducing a separate
  content system. Editors manage each tab's label, short description and
  default selection, plus a horizontal or vertical section orientation. Vertical
  tabs use a left-hand rail on wider layouts and the established horizontal
  scroller on narrow layouts. Public tabs use accessible keyboard controls,
  direct-link URL fragments and a reduced-motion-aware content fade. The Rules
  page presents its detailed material through Getting
  Started, Fair Play, Evidence, and Endings & Rulings tabs.
- A public managed Exploits page at `/exploits/` sits beneath Mods in the Rules
  navigation branch. Exploit rulings are server-managed catalogue records with
  a classification, concise ruling, optional guidance, publishing state, and
  display order. The public vertical tabs contain one entry per published
  exploit, including the settled Spiffo's Council rulings on zombie
  force-spawning, trapped-animal Nimble farming, and combat-built fence or
  window grids. Each ruling can include ordered example images selected from
  the managed image library, with required alternative text and optional
  captions. Accidental-discovery and evidence guidance avoids treating
  unpublished edge cases as
  approved behaviour.
- Managed Pages include dedicated Community Statistics and Card Group blocks.
  Standard and linked action cards can be mixed within one group. The homepage
  uses three destination-led linked cards and replaces
  its embedded leaderboard with an edge-to-edge alternate-surface statistics
  bar, framed by full-width top and bottom rules only, calculated exclusively
  from verified runs with approved canonical submissions. Editors choose and
  order supported metrics without controlling database queries. The initial
  metrics are Rats in the Race, Zombies Eliminated, Days Endured, Outposts
  Claimed, Fallen Survivors, Average Kills per Day and Real Hours Raced. Real
  Hours Raced sums cumulative active-gameplay milliseconds from each run's
  approved canonical projection rather than estimating from in-game time.
  Each action card is itself a keyboard-accessible link with managed alt text,
  a validated destination, an optional manually authored number or short label,
  and a restrained hover or focus lift. Cards size to their content rather than
  reserving space for a separate footer action. Every card inherits its card
  group's audience by default, or can independently target everyone, signed-out
  visitors, signed-in participants, or remain hidden. Editors add either card
  type from a split Add card control, and linked-only destination fields remain
  contextual to linked cards.
- The reusable `Ranking Table` block and editorial `/leaderboard/` Page share
  one official-run query implementation. Editors can configure additive mode,
  build, lifecycle, and participant filters; result selection; ordering; row
  limits; visible columns; and supporting presentation without controlling
  eligibility or canonical values. Public rendering preserves signed-in detail
  gates and uses a horizontally scrollable compact table on narrow screens.
- Flat backend-managed public pages at protected `/pages/<slug>/` addresses,
  with page-owned navigation labels, visibility, and ordering.
- An immutable Code-managed Pages registry in Website Content administration.
  Version-controlled definitions install stable keys, display identities,
  descriptions, fixed audiences, availability and route metadata. Navigation
  Items may target available fixed application routes alongside editorial
  Pages, while planned and address-driven routes remain non-selectable. The
  editorial Homepage remains solely in Pages and is not duplicated in the
  Code-managed Pages catalogue. Run Django migrations after changing the
  version-controlled registry definitions so the deployment reconciles their
  availability and route metadata into the database.
- A public Mods catalogue at `/mods/` with search, Allowed and Disallowed ruling
  filters, illustrated and compact list views, a pinned Required TGSRR Workshop
  entry, a curated Recommended section for selected Allowed mods, and responsive
  rules and submission modals. Recommended is a separate feature flag rather
  than a ruling, and recommended entries are not duplicated in ordinary
  results. The page states that only
  mods explicitly listed as Allowed or Required may be used; Disallowed and
  unlisted mods cannot be used. Its More Info modal explains the cosmetic and
  vanilla-information rules with generalised examples. Signed-in participants
  can find a mod by Workshop name, numeric ID or full Steam URL and provide a
  required reason. Name search uses Steam's supported `QueryFiles` API with a
  protected `STEAM_WEB_API_KEY`. Exact ID and URL resolution remain available
  without that key. The website does not parse Steam's rendered Workshop pages
  as an integration fallback. Steam confirms that the item exists for Project Zomboid, duplicates
  report their existing Required, Allowed, Disallowed or Pending review state,
  and valid new items enter Pending review without becoming public rulings.
  The Discord mod-policy record supplied on 1 August 2026 has been normalised
  into 59 unique historical entries and resolved against Steam: 54 retain a
  Previous Unstable ruling of Allowed and 5 retain Disallowed. All 59 current
  rulings remain Pending review until the permanent Stable voting workflow
  produces an authorised final decision.
- The permanent mod-approval journey is implemented in administration. Its
  Mod approval queue sorts Pending review records first, exposes a dedicated
  Pending shortcut and opens a focused review page containing the participant
  reason, Steam destination, previous Unstable provenance and editable final
  decision fields. Eligible Workshop Mod Approvers, Challenge Administrators and super
  administrators cast one attributable `Allow`, `Disallow` or `Discuss` vote
  per Pending mod and may revise it while voting remains open. Disallow and
  Discuss require a reason. Vote totals produce an advisory recommendation or
  discussion-needed state but never publish a ruling automatically. Moving a
  Pending record to Allowed or Disallowed requires a public rationale and
  records the authorised reviewer and timestamp. The final reviewer can insert
  a consistent Allowed or Disallowed rationale template, then edit and confirm
  the public wording before publication. Workshop Mod Approvers may
  vote in the queue; Challenge Administrators may edit final decisions. Run
  Submission Approvers are separately scoped to run reviews. Participant decision
  notifications remain the next slice.
- The current Workshop Mod records are development fixtures and imported
  preparation data. The project owner intends to wipe this table before the
  completed approval journey is tested from a clean state.
- Consistent primary navigation, authenticated-route redirects, accessible form
  metadata, keyboard focus treatment, and responsive local journey checks.
- Signup validates nickname and email availability, password policy and password
  confirmation when each control loses focus. Availability checks remain
  age-gated and rate-limited, while ordinary server-side validation remains the
  final authority on submission.
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
- Format-4 event blocks are retained as content-addressed verified records.
  Matching checksum, sequence range, starting hash and terminal hash allow later
  submissions and review pages to reuse decoded events while every manifest and
  complete ledger chain is still verified. Approval detects an exact approved
  event prefix, retains sealed daily authority, processes only appended events,
  and replaces the current active-day record. Any discontinuity uses the full
  rebuild path inside the same atomic approval transaction.
- The participant submission form accepts the tracker-generated `.txt` file by
  file picker or drag and drop, with direct export-text paste retained as a
  secondary fallback. All three paths use the same authoritative validation and
  immutable submission workflow. Pasting a Windows `.txt` path is detected and
  presents a focused file-chooser action with instructions to paste that path
  into the operating system's File name field.
- The canonical local background launcher performs a controlled restart on
  every invocation. It records both the Windows virtual-environment wrapper PID
  and the actual Python socket-owner PID, stops both, and discovers listeners
  with `netstat` because CIM process and TCP queries may be unavailable. It
  refuses unrelated port owners, then requires exactly one listener before
  reporting success. Route-specific changes must also be verified through the
  running HTTP server, using an authenticated request when the route is gated.
  In-process Django rendering is not proof of what port 8001 is serving.
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
  dashboard. A validated, hash-chained `run.ended` event and matching projection
  evidence now mark an approved death export as Deceased automatically. Other
  lifecycle decisions remain moderator-managed. Each Challenge Mode also has a
  configurable per-participant active-run limit, defaulting to one. Updates to
  an existing active run do not consume another slot. Participants can
  irreversibly deactivate their own active run without review; this marks it
  Abandoned, declines its pending submissions, prevents future updates to the
  same run ID, and immediately releases the mode slot.
- The protected two-file Legacy Leaderboard and Legacy Hall of Fame importer,
  merged Unstable run records, public legacy ranking sources and participant
  claim journey are implemented. Signed-in participants can claim one legacy
  run for team review. A focused approval screen records the reviewer and
  decision, links approved historical identity to the participant and sends an
  account notification. The participant dashboard shows pending and declined
  claim states or, after approval, a dedicated Legacy Rat Race panel containing
  one imported historical result. Active legacy runs use their current
  Leaderboard result; Inactive and Deceased runs use their Hall of Fame best.
  A separate archive divider and lifecycle tag keep legacy results explicitly
  separate from verified Stable runs.
- Approved claimants with an Active legacy run can submit participant-authored
  updates containing character name, kills, Time Survived, Level 10 skill count,
  completed outposts, Alive or Dead state and Twitch or YouTube VOD evidence.
  Time Survived accepts `YY:MM:DD:HH` or plain words and is normalized into the
  full display plus decimal days without moderator arithmetic. The website
  calculates weighted progress from the established one-million-kill, 13-outpost
  and 35-skill targets. Only one update may await review per legacy run. A
  focused moderation screen approves or declines the immutable submission with
  a retained reason
  and notifies the participant. Approval advances the current result,
  advances the historical best only when stronger, and marks the run Deceased
  when the submission reports death. Pending and declined submissions never
  affect public rankings.
- Signed-in Rat Racers can open another participant's profile from their linked
  name in Stable or claimed Legacy ranking tables. The profile presents only
  approved participant-facing records: Personal Best, Active Runs, Past Runs
  and the claimed Legacy Rat Race result when available. It does not expose
  submission history, pending or declined submissions, or moderation details.
- Signed-in verified-run page presentation at UUID-based addresses. Challenge
  progress is the first section and uses four short, responsive cards for
  kills, skills, outposts and landmarks. The Outposts card opens a dialog with
  all 13 catalogue-backed outposts, expanding the sparse authoritative run data
  for presentation only. Missing run records appear as collapsed Undiscovered
  entries without invented deliverable evidence. Discovered entries provide
  compact deliverable status details. Public rows
  mirror the mod's requirement, current-value and Passed/Pending columns and
  omit backend lifecycle counts. Each outpost is a bordered disclosure card
  with visible hover and focus feedback linking its rows to their owning outpost.
  The former summary grid and standalone World Progress section are removed.
  The character header has a compact build control that opens the starting
  occupation, selected starting traits and currently effective traits. The run
  page and leaderboard use one shared build-dialog template; the run page adds
  accessible Starting Traits and Current Traits tabs when both sets exist.
  Starting traits are ordered by catalogue point cost, zero-cost traits are
  presented as Passive, and the occupation shows its catalogue point value.
  When Project Zomboid omits a trait description, the tooltip derives a factual
  fallback from the trait's structured starting skill boosts.
  Current traits omit build costs and distinguish gained traits from traits that
  are no longer effective. A small
  state row exposes current weight and the favourite weapon from approved
  cumulative weapon-kill evidence through accessible hover text; their future
  history graphs remain pending authoritative history tables. Spawn choice and
  map-linked starting coordinates remain concise evidence in the header. Broken
  Weapons remains in Recorded Totals and can become interactive when its
  authoritative breakdown exists. Current skills follow in a grouped
  Project Zomboid-style panel using the complete version-controlled 35-icon
  in-game artwork pack from `deployment/assets/skill-icons`, installed into the
  catalogue as the preferred manual presentation with PZwiki artwork retained
  as a fallback. The Skills progress card opens that panel in a dedicated
  details dialog, matching the Outposts interaction and keeping the main run
  page concise. Town visits expand the sparse export against the 12 canonical
  town definitions, presenting omitted towns as unvisited. Activity totals and
  clearly distinguished in-game
  export and website receipt timestamps without exposing raw run IDs, checksums
  or ledger hashes. Charts remain a later signed-in presentation layer.
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
  guessed. Transient PZWiki download failures are retried per asset and, if still
  unavailable, are recorded in the structured report without aborting the
  catalogue-wide job. The latest reconciliation completed successfully on
  31 July 2026: 16 images were imported, 4,483 were unchanged, 748 unavailable
  results were recorded for review, and no manual assets were overwritten.
  Local and production deployments must run `run_reference_update_worker` as a
  separately supervised process alongside the web server. The web server does
  not consume queued reference or artwork jobs by itself. Avoid concurrent
  database polling during long write-heavy jobs when developing with SQLite;
  production uses PostgreSQL and must supervise and restart the worker.
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
- Google-authorised YouTube channel linking using the read-only YouTube scope,
  stable Google and channel identities, encrypted credentials, ownership
  collision protection, reconnection and participant-controlled disconnect.
- Provider-selectable run evidence using connected Twitch or YouTube channels.
  Switching providers and refreshing recent media updates only the evidence
  controls, preserving the pasted run export and the rest of the submission
  form. Twitch supplies broadcasts and clips; YouTube supplies recent public or
  unlisted uploads and archived livestreams through the official Data API.
- A participant may explicitly select one owned, connected Twitch or YouTube
  account as their primary streaming channel. That provider-neutral selection
  supplies the linked provider icon in live ranking tables. Clearing,
  disconnecting or invalidating the selected account safely removes the icon.

Uploaded brand images live in deployment media storage rather than Git. A live
deployment must persist and back up that media directory alongside the database.

Approval now rebuilds sealed and active daily authority into run-owned
`RunDailyRecord` rows. Fixed scalar deltas live on the daily record, while
non-zero keyed deltas use sparse `RunDailyMetric` rows. Missing deltas are
interpreted as zero, and active-day partial provenance is retained.

## Not Now

- Expanded analytical charts and detailed statistics beyond the launch views
- Full mod integration
- Participant notifications when an authorised reviewer records the final mod
  ruling. The submission, team voting and final-ruling administration journey
  is implemented.
- Expanded public weapon-kill, literature, and collectible presentation using
  the item catalogue. The implemented run export already supplies the underlying
  `weaponKills` and `literature` evidence; this is parked while launch-critical
  public pages are completed.

## Confirmed domain infrastructure

- The project owns `tgsrr.com`, purchased through Spaceship.com on 1 August
  2026. The Spaceship website is the current control surface for the domain's
  DNS records and related registrar settings.

## Hierarchical managed navigation

Pages now own canonical root or nested public addresses such as `/gallery/` and
`/media/gallery/`. Navigation placement is managed separately through ordered
Navigation Item records. An item may link to a Page or act as a non-clickable
heading, and may be nested to three visible levels. Each item has an enforced
audience of Everyone, Signed-out visitors, Signed-in participants or Staff.
Hiding a menu group by audience hides its nested branch, while code-managed
destinations retain their own stricter audience checks. Editorial managed Pages
use the same audience choices, enforced for both direct addresses and navigation
visibility. The public navigation bar
sits at the top of the page before the branded masthead. Desktop renders
dropdowns in a navigation bar that remains visible at the top while scrolling.
Mobile renders expandable submenus in a compact control bar that hides while
scrolling down and returns when scrolling up. Open navigation,
account, and notification panels keep the mobile bar visible. Guest Sign In
and Sign Up actions remain directly available beside the hamburger instead of
being hidden inside the expandable navigation. Code-controlled
routes remain reserved, and provisional `/pages/<slug>/` addresses permanently
redirect to a Page's canonical address. The admin tree uses visual drag-and-drop
insertion between items: vertical movement selects the position, while moving
right nests under the nearest preceding item and moving left moves the item
outward.

## Recommended next action

Prepare and test the production deployment path, including persistent database
and media storage, independent web and worker supervision, secret validation,
health checks, backup, restore, restart, and rollback procedures.

The customized public presentation now has a checksum-validated, transactional,
idempotent export and import path through `deployment/site-presentation`. Use it
to transfer approved local editing work without moving users, participants,
runs, submissions, credentials, notifications, or operational state.

## Remaining work

### Before launch

- Complete retention automation and the final privacy review.
- Run a production-shaped acceptance test across registration, account,
  submission, moderation, rankings, Rules, Mods, and Exploits.
- Test the full legacy import, claim, and participant-update journey with a
  representative export. Keep production legacy data empty until the team
  chooses its final cutoff date.
- Replace any remaining development-only navigation or gallery records before
  launch.

### Approved later work

- Notify participants when an authorised reviewer publishes a final mod ruling.
- Add separately cached provider online status to the leaderboard.
- Add signed-in participant search.
- Build the planned Top Ten summary and signed-in Run History pages when their
  product requirements are agreed.

## Launch-critical operational safeguards

Local development uses the canonical environment-aware
`scripts/start_website_dev.ps1` launcher. It loads the repository's uncommitted
`.env`, starts and verifies the web server and independently running reference
worker, avoids duplicate processes, and reports the local and LAN addresses.
The Django management entry point rejects a bare `manage.py runserver` so local
startup cannot silently omit the environment or reference worker.
Production must receive secrets from its deployment environment, never from the
repository, and supervise its web and worker processes independently.

Startup validation must fail before accepting traffic when a configured Twitch
or Discord integration has a missing or malformed Fernet encryption key. The
deployment health check must also identify the running build and verify that
required integration configuration is present without revealing secret values.
Restart procedures must stop the complete previous process tree and confirm that
only one listener owns the intended port before announcing the site as ready.

Do not rotate `STREAMING_TOKEN_ENCRYPTION_KEY` without an explicit credential
migration. Existing encrypted provider tokens must remain decryptable across
deployments, restarts and rollbacks. A pre-deployment check should verify this
against stored credentials without printing decrypted tokens.

The repository now includes a strict `config.settings_production` boundary and
the non-secret environment contract in `.env.example`. Production startup
requires PostgreSQL, Redis, SMTP email, live Turnstile, avatar moderation, all
supported connected providers, and the complete Steam reference and
decompilation toolchain. `/health/live/` identifies the running release, while
`/health/ready/` verifies the database, shared cache, persistent storage, and a
recent reference-worker heartbeat from that same release. The full audited
contract and remaining host-specific work live in
`docs/PRODUCTION_DEPLOYMENT.md`.
