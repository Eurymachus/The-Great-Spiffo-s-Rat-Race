# Ideas Parking Lot

These are possibilities, not approved current scope. Promote an idea into
the relevant `WEBSITE_NOW.md` or `MOD_NOW.md` only when the user explicitly makes
it part of the active deliverable.

## Participant Platform

### Priority follow-up: encrypted provider configuration in admin (27 November 2026)

Owner requested this as a priority addition after the Discord validation and
Settings-error fix. Capture and scope next; do not expand the current fix.

- Superuser-only management of provider application IDs, callback addresses and
  encrypted secrets in database-backed records.
- Keep the encryption key outside the database and backups of that database;
  define key recovery and rotation before migrating configuration.
- Never reveal saved secrets in admin, logs, audit history or exports. Allow
  replacement with safe configured/unconfigured status instead.
- Validate IDs and environment-specific callbacks before saving. Audit actor,
  provider and changed fields without recording secret values.
- Define environment fallback, migration, rollback, caching/reload behaviour
  and backup/restore verification. Prevent staging settings reaching live.
- Assess superuser compromise and credential replacement risks. This is a
  separate scoped implementation, not authorization to move existing secrets.

- Rework the desktop navigation bar and responsive hamburger navigation as one
  coherent interaction system. Revisit spacing, alignment, hierarchy,
  open/close behaviour and third-level navigation on both layouts rather than
  continuing with isolated cosmetic adjustments.
- Add a signed-in, filterable Run History page.
- Add a concise public Top Ten summary if it provides a useful destination
  beyond the configurable Rankings page.
- Add signed-in participant search as a discovery layer for public profiles.
- Add separately cached provider online status to ranking rows.
- Expand approved run details with useful chronology, comparisons, and charts.
- Aggregate charts such as traits and weapons used

## Challenge Operations

- Rat Race 1.0 maintenance was approved on 10 November 2026 and promoted to
  `docs/MOD_NOW.md`; it is no longer an unapproved release idea.

- Seasons and versioned rules
- Appeals and public integrity policies
- Achievements and shareable result cards
- Discord role synchronisation and challenge announcements. Participants first
  link their immutable Discord identity through the website's minimal
  `identify` OAuth flow. A later phase may use the existing **The Great
  Spiffo** bot from the same Discord application, currently hosted through
  MEE6 Custom Bot, for narrowly scoped and audited role changes. MEE6 may
  continue hosting ordinary bot features while the website uses Discord's REST
  API for role updates. Any bot-token reset must be coordinated between MEE6
  and the website. Define explicit Rat Race status-to-role mappings, preserve
  role hierarchy constraints, and avoid enabling broader permissions or
  gateway intents solely for website synchronisation.

## Rat Race 2 outpost and objective proposals (6 November 2026)

**Status: 20,000 calories and player-crafted weapons/tools approved on 19 November 2026, including one forged crowbar and one forged sledgehammer per outpost. Remaining equipment and other proposals are undecided.**
The approved decisions are promoted to [MOD_NOW.md](MOD_NOW.md) and
[DECISIONS.md](DECISIONS.md). Implementation remains pending.
Source: [Objectives and Outpost Goals, Discord discussion, 5-6 November 2026](https://discord.com/channels/1355647558227333231/1567990200779411617).
Badger proposed expanded supplies and new locations; Shivas supported expanded
supplies and additional objectives, with a different preference on retaining
churches. Eury raised the implementation/testing cost and release-delay risk.
Eury and Badger agreed that any adopted changes should be a release surprise.
That preference does not approve any particular requirement below.

The purpose is to make outposts feel equipped for hypothetical survivors and
give returning players and viewers new goals. Decide the supply package first,
then select locations and their objective type separately. Do not promote this
section into current-focus documents until decisions are made.

### Proposed supplies and open decisions

| Proposal | Discussion detail | Decision needed | Relative implementation effort |
| --- | --- | --- | --- |
| Increase food, approved 19 November | Require 20,000 calories per outpost, retaining existing non-spoilable-food and storage rules. Owner selected the higher target to add challenge and stocking work. | Target settled; existing-run transition still needs definition during implementation. | Low for the threshold; implementation and validation pending. |
| Weapons and ammunition | Player-crafted weapons approved on 19 November. One forged crowbar is mandatory per outpost. Earlier loaded-firearm proposal remains undecided. | Remaining counts, minimum condition, eligible types, crafting provenance, and whether firearms/ammo form a separate requirement. | New inventory checks, crafting provenance and deliverables. |
| Repair/construction tools | Player-crafted tools approved on 19 November. One forged sledgehammer is mandatory per outpost. | Remaining tool roles, quantities, substitutes, condition, provenance and whether one item may also count as a weapon. | Shared inventory inspection plus crafting provenance. |
| Workstation | Possibly one crafted workbench or simple forge per outpost. | Either/or versus both; eligible stations; installed versus usable; whether player-crafted origin must be proven. | Medium to high. Separate world-object/entity inspection. |
| Emergency bag | One bag with a day's supplies, a weapon and small tools such as pliers, hacksaw or screwdriver. | Exact food/water quantities, tool list, bag eligibility, storage location, and whether its contents also count toward general stocks. | Medium. A complete kit must exist within one qualifying bag. |

The selected food target is a gameplay decision. The discussion's human-survival calorie
argument is not adopted as a nutritional standard. Claims about livestock
survival and sunflower oil were balancing arguments, not verified guarantees
that these sources satisfy the existing food checker.

### Additional crafted equipment shortlist (19 November 2026, unapproved)

Consider one each of a forged wood axe, forged ball-peen hammer, crafted saw,
forged hunting knife and forged machete, in addition to the two approved items.
This would make seven distinct items per outpost, covering wood gathering,
hammering, sawing, cutting and combat. These five additions and their quantities
are proposals only.

Installed 42.22.2 scripts confirm forging recipes for the relevant heads/blades
and assembly mappings to `Base.WoodAxeForged`, `Base.BallPeenHammerForged`,
`Base.HuntingKnifeForged` and `Base.MacheteForged` in
`media/scripts/generated/recipes/recipes_assembly.txt`. `Forge_Saw` produces
`Base.CrudeSaw` in `generated/entities/blacksmith/craftRecipes/recipes_blacksmith_tools.txt`.
The saw requires Blacksmithing 4 and auto-learns at 6. Full acquisition costs,
unlock requirements for the other items, and individual-item provenance still
need implementation research. Finished equipment, rather than loose heads or
blades, is the proposed deliverable.

### How supply requirements could be added

Investigation baseline: current `codex/rat-race-dev`, active mod `42.22`,
installed reference recorded as 42.22.1 / Steam build `26409601`.
Paths below are relative to `Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/`
unless explicitly identified as website paths. This is source-level feasibility
research, not an in-game certification or an implementation.

1. **Food:** `client/TGSRR/Outposts/Checks/Fixtures.lua` defines
   `FOOD_REQUIRED_CALORIES = 5000`. Its `foodResult` already reports current,
   required, availability and pass status. Change the agreed threshold there,
   or introduce a shared rules definition if requirements need explicit
   versioning. Preserve the current restriction to world-object containers in
   registered ground-floor rooms, including nested bags. Player inventory,
   vehicles, corpses and loose floor items do not qualify. The recursive
   traversal counts non-spoilable `Food`; `Checks/BoxedFood.lua` separately
   handles listed six-item boxes. Do not assume oil/fluid contents or live
   animals count. Audit descriptions and tests for the old 5,000 value.
2. **Weapons and tools:** extend the existing cached container traversal with
   a reusable stock inspection result, rather than independently scanning
   every square for each new requirement every second. Use explicit roles and
   verified item identifiers/tags, not translated display names. Count distinct
   items and define whether one item can fill several roles. Check weapon
   condition and the chosen ammunition semantics live so removing supplies,
   unloading or breaking equipment can regress completion. Exact current-build
   weapon/ammo APIs and tool tags still require vanilla-call-site or Kahlua
   exposure verification before implementation; no new Java method is certified
   by this investigation. Following the 19 November decision, qualifying weapons
   and tools must have been crafted by the player. Item type alone cannot prove
   that provenance: investigate existing crafting evidence and whether individual
   output items retain usable creator evidence. If not, record provenance at
   craft completion and preserve it through storage and reload. Define how
   pre-tracking crafts are handled without inventing retrospective proof.
3. **Emergency bag:** the existing recursion already recognizes
   `InventoryContainer` and reads `getItemContainer()`. Preserve each candidate
   bag's boundary and evaluate its entire kit separately; do not combine food
   from one bag with tools from another. Decide whether nested bags are allowed
   and whether a bag must itself be inside an eligible world container. If the
   team wants loose floor bags, add that storage mode explicitly. Decide shared
   credit with general food/tools before coding, because the current food scan
   already counts nested bag contents.
4. **Workstation:** inspect installed station objects through a dedicated
   check using the existing fixture cache/event architecture as a starting
   point. Verify actual 42.22.1 entity/sprite identity, placement/removal events,
   multi-tile deduplication and Lua exposure first. Do not equate an inventory
   item with an installed station, or a decorative sprite with a usable forge.
   Existing bed/generator fixture records demonstrate installation tracking,
   but do not prove how crafting stations behave. Proving that the player
   crafted a station requires separate provenance evidence; finding an existing
   station cannot establish origin. Requiring fuel, recipes or auxiliary
   equipment would be additional rules, not implied by installation.

All new mandatory supply checks need the complete integration path:

- Emit normalized results through `client/TGSRR/Outposts/Runtime.lua` and
  `shared/TGSRR/Outposts/ProgressStore.lua`, preserving unavailable observations
  when rooms stream out instead of treating missing data as a failed check.
- Add stable deliverable IDs to the required list, fractions and weights in
  `shared/TGSRR/Outposts/Completion.lua`. Current weights total 100; rebalance
  them explicitly. Strict completion must still require every selected check.
- Update Outpost Overview rows/tooltips, notifications, translations and
  aggregate presentation. Check the fixed tracker layout with the extra rows.
- Trace the new IDs through `shared/TGSRR/Run/OutpostSnapshot.lua`, lifecycle
  collection and first-completion milestones. Its snapshot iterates the
  completion ID list, but that alone does not update all presentation/contracts.
- Update website `apps/website/registry/run_exports.py`, which explicitly
  allowlists outpost and deliverable IDs, and `registry/run_public.py`, which
  explicitly orders deliverables and currently sets a requirement total of 14.
  Extend catalogue/authority normalization and relevant validation tests as
  needed; unsupported IDs would currently be rejected.

### Proposed locations and differences of opinion

| Candidate | Proposal and current evidence | Required investigation before selection |
| --- | --- | --- |
| Crossroads Mall, Valley Station | Badger suggested replacing Valley Station church with the mall or cinema. Shivas instead keeps the church and makes the mall a separate mandatory clear. Not registered in the current location definitions. | Survey buildings, complete footprint, floors, basements and streaming; choose clearing-only or full outpost. |
| Grand Ohio Mall, Louisville | Both support it as a new objective; Shivas explicitly proposes a mandatory clear and endgame goal. Already optional landmark `grand_ohio_mall`, anchor `(13623, 1365, 0)`, BuildingDef `1126123245142018`. | Revalidate current-build membership and full footprint. Visiting this landmark is not clearing it. |
| Louisville Cathedral | Badger suggested a possible 14th outpost. The nearby skyscraper was raised as a complication within the proposed 150x150 area. | Identify the intended building, survey bounds and decide whether surrounding buildings/floors must activate too. Do not assume the current Louisville church entry is this cathedral. |
| Louisville General Hospital | Alternative deep-Louisville objective, proposed to avoid the cathedral's skyscraper complication. | Confirm exact hospital, bounds, all accessible floors and whether a full habitation package is appropriate. |
| StarEplex Cinema, Valley Station | Alternative to replacing the church with Crossroads Mall. Already optional landmark `star_eplex_cinema`, anchor `(13637, 5887, 0)`, BuildingDef `6192677120901126`. | Revalidate the intended cinema and survey clearing bounds; settle retain-versus-replace policy. |
| Sanatorium | Previously suggested by Badger and mentioned again, without a detailed specification. | Identify the exact site before estimating scope or promising suitability. |
| Dark Wallow guest house | Tentative later idea from Badger: remote, four-floor interior clear. Population was explicitly uncertain. | Confirm site/name, actual floors, accessible rooms, population and travel burden. Do not confuse this with existing Hog Wallow Military Base. |

Badger suggested 15-16 outposts overall, with a few harder new locations.
Shivas also supports 15-16 but retaining the churches. These are not yet one
consistent list: decide whether the two mall clears count toward that total
or sit alongside 15-16 fully equipped outposts. Darkness, trapped zombies,
remoteness and vertical layouts are intended challenge characteristics, not
tested difficulty ratings.

### How locations could be added

**Full outposts:** use `client/TGSRR/Outposts/Debug/SurveyWindow.lua`,
`SurveyIO.lua` and `ZoneEditor.lua` to establish the intended current-build
anchor, core bounds, clearance center, BuildingDef IDs and room exclusions.
Add a unique definition to `shared/TGSRR/Outposts/Definitions.lua`, plus name
translations and appropriate map presentation. The helper currently fixes
clearance to 150x150 and support radius defaults to 15. Explicitly decide any
departure from those rules. All existing security, habitation, supplies,
utilities and car requirements apply unless a new requirement-profile design
is approved. Adding a mall this way would otherwise require equipping and
securing it as an outpost, not just killing its zombies.

**Separate clearing objectives:** recommended design direction for malls if
the team adopts Shivas's clearing-only proposal. Add a distinct objective
definition and evaluator with required activation, surveyed clearance bounds,
completion evidence, UI and export support. The generic challenge deliverable
registry in `shared/TGSRR/Challenge/Deliverables.lua` provides an extension
point; its overall progress weights also need an explicit decision. Reuse
appropriate room-resolution/activation logic without silently inheriting bed,
food, sink, car or barricade requirements. Preserve optional visit history as
separate evidence. `Locations/Definitions.lua` marks landmarks optional, and
`client/TGSRR/Tracker/Landmarks/Module.lua` summarizes visits. Merely changing
`optional = true` does not implement clearing.

**Large-site blocker to validate:** `Fixtures.lua` explicitly assumes all
registered outposts fit within the loaded-cell radius. A populated `IsoRoom`
is its streaming gate, not proof that a mall is fully loaded.
`Outposts/Runtime.lua` counts the current cell's live zombie list inside X/Y
bounds and permanently latches clearance after required activation and a
zero count. It does not prove the absence of unloaded zombies across an
arbitrarily large site. Its activation list is derived from registered
buildings, not automatically every building intersecting the clearance square.
Therefore neither enlarging the rectangle nor walking every room once is
sufficient proof of a simultaneous whole-mall clear. Survey actual loaded
coverage and design an authoritative certification rule before claiming
large-site support. A staged/sector clear is a possible different rule to
decide on, not an equivalent implementation of simultaneous clearance.

New outpost IDs also require website allowlist/catalogue updates. Existing
geography is seeded in
`apps/website/zomboid_catalogue/migrations/0009_seed_tgsrr_geography.py`;
add a new migration or supported catalogue update rather than editing an
already-applied migration. Audit denominators, rankings, completion badges,
map markers and export tests for assumptions about 13 outposts. Replacing an
existing location must not reuse its ID for a different building and silently
reinterpret earlier completion evidence.

### Rule compatibility and verification before release

- Decide whether changed rules apply only to new runs or how existing runs
  transition. Higher thresholds and new requirements can regress current
  completion, while earlier first-completion evidence remains immutable.
  Version the relevant rules/catalogues and explicitly define old-export
  handling. Do not assume a landmark registry-version bump also versions
  supply requirements. Preserve approved-history semantics in
  [DECISIONS.md](DECISIONS.md) and the
  [export authority contract](RUN_EXPORT_AUTHORITY_CONTRACT.md).
- Desktop checks: threshold edges, existing boxed-food behavior, nested
  containers without duplicate counting, incomplete versus complete bags,
  qualifying versus broken/unloaded weapons, allowed tool substitutes,
  weight totals, strict completion, regression, save/reload snapshots and
  website acceptance/presentation of every new ID. Existing starting points
  include `tests/lua/boxed_food_test.lua`, `outpost_snapshot_test.lua`,
  `outpost_lifecycle_snapshot_test.lua` and
  `outpost_lifecycle_event_bridge_test.lua`.
- In-game checks on the target build: all selected locations and accessible
  floors, spawn activation, streaming boundaries, unloaded zombies, inaccessible
  rooms, fixture placement/removal, bag transfers, performance and reloads.
  Confirm difficulty and supplies are achievable with actual Rat Race settings.
- Verify every newly used Java API through vanilla usage or LuaManager.Exposer;
  keep the repository's prohibited-global scans and fail-fast Lua rules.
- Release surprise is a coordination preference. Keep public rules, Workshop
  material and website copy synchronized for release; repository documentation
  or shipped assets alone cannot enforce secrecy.

**Investigation conclusion:** raising calories is supported by an existing
check; inventory-based supplies have a clear reusable inspection path;
workstations need specific entity/API research; compact new outposts fit the
existing registration model after survey. Large mandatory clears require
additional streaming/certification design. Exact new-site surveys, station
identity, weapon API verification and runtime testing remain outstanding.
This capture changes documentation only.

## Report Data

### PZCommunityRank reference ideas (17 November 2026, unapproved)

Read-only inspection of Workshop `3746228308`, mod `PZCommunityRank`:

- Their companion-fed leaderboard is reference material only. TGSRR will not
  use a companion application; see the snapshot-mod idea below.
- Coarse kill/death heatmaps and exploration summaries, with explicit location
  semantics and coverage. Their kill grid uses player position, not corpse
  position; their "base" sample is simply the current player location.
- Optional survival statistics such as distinct sleeping areas, explored
  basements and a streak without canned food. First compare existing collectors;
  define precise counting rules before adding any new collection.
- Evidence-based death classification with an unknown category, rather than
  adopting their first-matching-condition heuristics.

These are reference concepts only, not approved implementation scope. The
initial Lua-only inspection was extended on 19 November 2026 to readable
Companion and backend source. The backend does support moderator approval of
objectives; missing Lua checks do not mean those objectives are unverified.
See [Companion and backend findings](MOD_REFERENCE_DATA_COLLECTORS.md#pzcommunityrank-companion-and-backend-19-november-2026).

### TGSRR Daily Leaderboard (17 November 2026, idea only)

- Proposed separate, optional Workshop mod displaying a packaged leaderboard
  snapshot in-game, without a companion application. Keep updates independent
  of main-mod releases and unfinished development changes.
- The website could generate a small Lua data file from approved run data on
  a daily schedule. Publish only when standings change, with a clearly visible
  snapshot timestamp in-game.
- A publishing worker could package and upload the Workshop update. Unattended
  Steam authentication, supported upload tooling and release controls still
  need investigation; automated publishing has not been proven.
- Daily publication does not imply live updates within a running game. Players
  need the Workshop update downloaded and loaded by the game to see it.
- Suggested first experiment: website-generated snapshots with manual uploads,
  followed by automated publishing if feasible. No implementation, scheduling
  or publishing is authorized by this idea capture.

#### Upload feasibility investigation (19 November 2026)

Initial investigation found SteamCMD technically suitable. The subsequent
authorized two-upload local test below now proves creation and update using
cached authentication. Website-host deployment and daily scheduling remain
untested.

- Valve documents `workshop_build_item <vdf>` for creation and updates. An
  update supplies app ID `108600`, the existing item ID, a content directory
  and optionally a changenote. Omit unchanged metadata. Valve describes this
  integration as testing-only because it requires user credentials; treat it
  as a candidate owner-operated publishing tool, not a guaranteed production
  service or a login requirement for participants.
  Source: https://partner.steamgames.com/doc/features/workshop/implementation
- A first-hand PZ 42.21 macOS report says SteamCMD uploaded successfully when
  the in-game uploader failed, with a reported tag-setting limitation. This
  supports PZ compatibility but does not prove our Windows host or metadata
  preservation: https://theindiestone.com/forums/topic/102225-4221-macos-in-game-workshop-upload-fails-with-error-requesting-steam-to-update-the-item/
- Installed 42.22.2 Java confirms that the normal uploader submits `Contents/`
  as the content root (`SteamWorkshopItem.getContentFolder` and
  `SteamWorkshop.SubmitWorkshopItem`). Use an isolated leaderboard package,
  never the main workspace Contents tree.
- Reusable website foundations: `registry/leaderboard.py:build_ranking_table`
  selects official runs with approved submissions; `operations/queue.py` and
  the reference worker demonstrate auditable jobs; `operations/steam_auth.py`
  verifies cached SteamCMD login. These are foundations, not an existing
  Workshop publishing feature or daily leaderboard scheduler.
- Proposed job: capture the chosen public ranking consistently, serialize
  escaped data into a fixed reviewed mod template, validate, compare its data
  hash with the last successful publication (exclude generation timestamps),
  then upload to one fixed nonzero Workshop ID. Retain package hashes and
  previous packages; serialize uploads and reconcile uncertain results before
  retrying. Empty results must be distinguished from query/build failures.
- Follow the existing host-side authentication decision. Use the item's owner
  account and a protected persistent SteamCMD session. Do not assume the
  reference-download account can publish the item. Keep credentials out of
  packages, Django records and logs. Reauthentication should stop the job and
  notify an administrator. If sharing a SteamCMD installation, coordinate its
  use with reference updates and authentication; an isolated publisher is
  preferable. Do not promise permanently unattended authentication.
- Recommended proof: create/configure a separate private test item, establish
  owner authentication, upload two distinguishable snapshots in separate
  SteamCMD runs, download and compare them, confirm metadata remains intact,
  and open the result in PZ. Test no-change skips and expired-auth handling
  before enabling a daily schedule. Creation, authentication and publication
  remain a future implementation/test step.

#### Successful two-upload probe (19 November 2026)

- Authorized separate item: [TGSRR Daily Leaderboard - Upload Test](https://steamcommunity.com/sharedfiles/filedetails/?id=3842654789),
  Workshop ID `3842654789`, mod ID `TGSRRDailyLeaderboardProbe`.
- Both VDF submissions specified visibility `3`. The authenticated Workshop
  page independently confirmed **Current visibility: Unlisted**, the intended
  title/description, and two change notes. Steam's automated content check was
  still pending at verification; unauthenticated item metadata returned result
  `9`. Do not interpret that response as proof the upload failed.
- SteamCMD at `C:/Games/SteamCMD/steamcmd.exe`, using the existing owner account
  `Eurymachus`, created snapshot 1 then updated the same item to snapshot 2 in
  separate processes. Both logged cached-credential authentication and a
  successful commit, with exit code 0 and no interactive authentication.
- Snapshot 1 contains synthetic Test Racer score 100 and mod version 0.0.1;
  snapshot 2 contains score 200 and version 0.0.2. No real standings were sent.
  Each was downloaded through SteamCMD immediately after publishing, and both
  files matched their respective SHA-256 manifests. Snapshot 2 replaced the
  first. Upload manifests: `6737392487789476819` then `8491074521213358037`.
- Reproducible package builder: `tools/workshop_leaderboard_probe.py`. Artifacts
  and per-revision hashes: `outputs/daily-leaderboard-workshop-probe/`.
  The VDF now retains the item ID; never reset it to zero for another update.
  Content is isolated from the main and Team Test Workshop packages.
- Commands used: `steamcmd.exe +login Eurymachus +workshop_build_item <absolute-upload.vdf> +quit`,
  then `steamcmd.exe +login Eurymachus +workshop_download_item 108600 3842654789 validate +quit`.
  Run from the SteamCMD installation directory with access to its cache.
- This proves local command-line publication and replacement, not a running
  website publishing pipeline, long-term authentication reliability, or an
  in-game leaderboard UI. The probe only loads synthetic data and prints its
  revision. No daily schedule, website changes or in-game smoke test was made.

- Per-day aggregate deltas
- Public presentation of lifetime kills by weapon, literature, and collectible
  evidence already present in approved exports.
- Revisit the fixed-size outpost lifecycle envelopes. Consider reducing
  `firstCompletion`, `latestCompletion`, and `latestRegression` to only
  `gameDay` and `utc` when the omitted state, sequence, requirement, and world
  age values are already authoritative elsewhere or can be derived without
  weakening validation or immutable evidence.
- Additional versioned report-schema and synthetic long-run size tests when the
  export contract changes.

## Special items at selected locations (20 November 2026)

- Idea for Rat Race 2.0: place custom collectibles or relics at deliberately
  chosen landmarks, in specific containers or as objects on display. Collecting
  them could become optional objectives with recorded challenge evidence.
- A fixed item at a fixed landmark is a possible first version. Alternatives
  include choosing from a curated list of locations per run or distributing
  several collectibles across Kentucky. Item identities, locations, rewards
  and any points contribution remain undecided.
- The owner confirmed that this feature only needs to support new challenge
  runs because the challenge has not launched. Existing-save migration is
  explicitly outside the scope of this idea.
- Placement should happen once per world when the relevant location loads,
  persist across saves/reloads, and never respawn an item after collection.
  Verify the placement and collection APIs before implementation.
- Parked proposal only; capturing this note does not authorize implementation.

## Hourly community statistics aggregation (20 November 2026)

- Parked approach: a supervised website worker job prepares community
  statistics approximately hourly from eligible, approved, normalized run
  records. The statistics page reads prepared results and displays their
  last successful update time instead of recalculating on every request.
- Approval updates run authority and marks aggregates as needing refresh.
  Start with a full rebuild, counting each run once from its current approved
  state. Repeated submissions must not add duplicate contributions. Approval
  corrections, eligibility changes and exclusions must remove obsolete
  contributions on the next refresh.
- Publish a complete snapshot atomically only after successful calculation;
  retain the previous successful snapshot if a job fails. Prevent overlapping
  refreshes. Skip unchanged work where possible, while refreshing any
  time-dependent measures even without new submissions.
- Candidate results include totals, distributions, character builds, weapon
  breakdowns, milestone timings and records. Define supported mode, rules/build
  and other filters before choosing snapshot dimensions. Store sample sizes
  and tracking coverage with results; missing evidence must not become zero.
- Prefer normalized database authority over repeatedly decoding exports.
  Reusable compressed export blocks reduce repeated encoding and verification,
  but do not eliminate collector, storage or aggregation costs. Continue using
  compact cumulative and daily data rather than unnecessary per-action logs.
- Consider incremental/category-specific rebuilds only if measured workload
  warrants them. No scheduler, aggregate schema or page is approved by this note.
- Refined implementation preference: persist versioned snapshots in ordinary
  database summary tables, shared by all web processes and retained across
  restarts. Aggregate counts, sums and grouped distributions in the database;
  avoid loading all run records into application memory. Measure query cost
  before choosing indexes or incremental maintenance.
- Maintain a monotonically increasing source revision per affected scope,
  updated transactionally with approvals, corrections, exclusions or deletions.
  Build from a consistent source view and record its revision. Changes arriving
  during a build must remain pending rather than being cleared by publication.
  Initially rebuild each affected challenge/season in full, preserving exact
  distinct counts, medians and records when old contributions change.
- Filter delivery: precompute a small defined set of common scopes, not every
  possible combination. The browser requests the selected filtered summary;
  serve a prepared result where available. Less common supported combinations
  may use bounded server-side aggregation with a cache keyed by canonical
  filters, source revision and calculation version. Define whether these read
  the published generation or current approved authority, and expose matching
  freshness information rather than silently mixing generations.
- Browser-only filtering is appropriate for presentation or for complete
  downloaded summaries that can answer the question exactly. Do not send every
  run to the browser or combine marginal summaries to invent intersections.
  Medians, distinct participants and overlapping groups cannot generally be
  combined from simple totals or averages. Reuse cached responses for repeated
  selections; changing a filter need not trigger a new calculation every time.
- Next focus: review and fill selected gaps in per-run gathered data first,
  using the statistics readiness audit in `MOD_EXPORT_CHECKLIST.md`. Individual
  collectors and counting rules still need selection and verification; this
  does not approve every candidate in the audit.

## Leisure reading and media feasibility (21 November 2026)

Status: literature counts approved and implemented on 21 November; see
`MOD_NOW.md` and `DECISIONS.md`. Store exact item-type counts under
`entertainment.literature`, including rereads, without titles. This preserves
subtypes for later aggregation, including paperbacks separately from books.
TV/VHS and title history remain outside implementation scope. Count a successful
game reading action, not an item acquired, action started or human attention.

### Original product recommendation (superseded by the decision above)

- Lead with simple counts such as books, comics and magazines read for fun.
  Repeated completed readings count again; interrupted actions do not.
- Titles are useful only for an explicit feature such as unique titles read,
  first reads versus rereads, or a personal reading history. They are not needed
  for ordinary category totals or community comparisons of reading activity.
- If unique/repeat statistics are wanted, retain raw content identity internally
  and a bounded per-content summary. Do not export every reading as a ledger
  event or build a public title catalogue merely because identifiers exist.
  Otherwise category counters alone are the smaller first slice.
- Completion counts do not measure equal effort: item durations differ. Avoid
  presenting them as pages read, reading time or challenge points.

### Evidence and build provenance

Static inspection used installed Build 42.22.2, Steam build `26486631`, and
matching marker in `tgsrr_decompiled/build-26486631-job-17`. Paths below are
relative to the Project Zomboid installation, with Java paths relative to that
decompile. Static evidence does not certify runtime callback ordering or effects.

- Existing `42.22/media/lua/client/TGSRR/Run/LiteratureTracker.lua` admits only
  skill books and recipe literature. Its successful `ISReadABook.complete()`
  wrapper and full-item-type summaries cannot simply be extended unchanged to
  leisure titles. `LiteratureSnapshot.lua` exports that filtered state.
- `media/lua/shared/TimedActions/ISReadABook.lua`: start/update/stop/perform/complete
  expose action lifecycle. `perform()` already mutates title-read state; capture
  pre-action state before it and validate completion deduplication/order. Positive
  page progress uses character state keyed by full item type. Other items use a
  nominal five-page duration. Neither establishes universal per-title resumability.
- `zombie/scripting/logic/ItemCodeOnCreate.java`: entertainment books use a book
  translation key in `modData.literatureTitle`; comics use a series key with an
  optional issue suffix; dated magazines use publication/month/year. Preserve full
  item type separately. `modData.printMedia.id` identifies separate print content.
  Localized names are labels, not identity. Untitled content supports action
  counts without invented unique titles. Explicit classification must exclude
  photographs and other unrelated literature-like items.
- `zombie/characters/IsoGameCharacter.java`: `isLiteratureRead()` tests the
  sandbox literature cooldown, not lifetime uniqueness. The persisted title map
  records a day and updates on eligible rereading, not every action or the original
  completion. Existing-state baselines cannot recover first times or repeat counts.
- `zombie/radio/media/MediaData.java` and `RecordedMedia.java`: use stable media
  IDs and line GUIDs rather than numeric indexes or translated titles.
  `hasListenedToAll(player, media)` requires every line known and nonzero lines.
  Vanilla `media/lua/client/ISUI/ISLiteratureUI.lua` uses this check. Player known
  lines persist, but have no first-learning timestamps or repeat counts. All lines
  learned can accumulate across playbacks; it does not prove one full viewing.
- `zombie/radio/devices/DeviceData.java`: playback starts at line zero. Save/load
  retains inserted media, but does not serialize playback position. Device
  playback/stop alone cannot prove character exposure or completion.
- `media/lua/shared/RadioCom/ISRadioInteractions.lua`: eligible world-device
  interaction checks living/awake player, same floor, axis-aligned +/-5-tile
  range and matching indoor/outdoor status. New GUIDs become known before effect
  application; already-known GUIDs return early. Per-player/per-code effect
  cooldown is 30 multiplier-decremented units. Media XP cutoff may prevent XP
  while a line becomes known. XP/mood changes are not reliable exposure counters.
- `zombie/iso/objects/IsoWaveSignal.java`: powered, positive-volume devices emit
  `OnDeviceText` when codes are non-null. Deaf/visibility checks occur in text
  rendering, not in the above interaction eligibility function. Rendering volume
  range and fixed interaction range differ. Do not assume hearing, walls or line
  of sight have identical learning and display semantics; probe them in-game.
- `zombie/radio/scripting/RadioChannel.java`: live transmissions have null line
  GUIDs. Channel GUID and airing broadcast ID are available, but correlating them
  to received text is inference, complicated by adverts, boundaries, duplicate
  devices and channel changes. No per-character completed-live-program history
  was established. Keep live-TV completion outside the initial scope.
- `zombie/Lua/LuaManager.java`, `Exposer`: relevant character, literature,
  device, recorded-media and radio-script classes are registered. Proposed
  getters are public; reading, literature UI and radio debug UI supply vanilla
  call sites. Protected playback fields are not a proposed Lua API.
- Prior originating investigation of PZCommunityRank Workshop `3746228308`
  found a generic `ISReadABook.perform` books counter without category, title or
  completion checks in its wrapper, and no TV/VHS collector. It is not proof of
  the richer semantics above; external sources remain read-only.

### Contract, cost and validation implications

- Independently maintain cumulative counts and sparse daily deltas. If retaining
  content detail, keep first observed completion evidence once and bounded
  counts/latest state per content, not per-page or per-tick exported logs.
- Baseline-known content has unknown original times. Record collector start,
  schema/build and partial coverage; never turn missing history into zero or
  invent daily completions from baseline state. Active action references do not
  survive reload; define interrupted/recovered sessions explicitly.
- Collection, export validation, approved-run normalization and presentation
  must evolve together. The November 20 audit in `MOD_EXPORT_CHECKLIST.md`
  identifies missing dedicated literature authority. Pending submissions must
  not affect statistics; preserve raw IDs and immutable submission evidence.
- Reading hooks have low event-driven cost. Title state scales with distinct
  content, so custom/generated identities need bounds and overflow disclosure.
  A later VHS learning collector could cache GUID-to-media mappings and inspect
  affected media on events instead of scanning every tape every tick. Repeat
  viewing and live-program completion remain unproven features.
- Focused runtime plan: complete/cancel/reload reading; duplicate title copies;
  different comic issues; cooldown rereads; instant actions; positive-page and
  non-page items. Verify action order, exactly-once counting and daily rollover.
- Later media probes: partial tape/restart/reload; known content; muted/off
  devices; range/floor/indoor boundaries; sleep; Deaf/visibility; XP cutoff;
  duplicate TVs and channel changes. Compare event observations, persisted
  character state and actual benefits. No in-game validation was performed in
  this feasibility investigation.
