# Mod: Current Focus

## Build 42.22 reference transition (27 October 2026)

- Steam desktop now uses `pre-release`, build `26221929` (42.22).
- Validated reference: `tgsrr_decompiled/build-26221929-job-15`. Local catalogue
  review 10 is approved. Artwork job 8 completed with 4,810 imported images;
  the 532 unsupported or placeholder icons remain recorded as unavailable.
- Website reference updating supports that branch. Follow
  [the release checklist](STEAM_REFERENCE_SOURCE.md#new-game-release-checklist)
  for decompilation and a separately approved versioned catalogue review.
- Editable mod content is under `42.22`, with the RR Official save-routing
  fix. `42.21` retains its original implementation. Full 42.22 compatibility
  remains a separate audit.

### Existing RR Official save loading blocker (27 October 2026)

- Twist's read-only log at
  `S:/Downloads/Games/Project Zomboid/Modding/Save Logs/console.txt` identifies
  42.22.0 and loads `TGSRR-test` and `TGSRROptimized`. It reports a null
  `toString` call in vanilla `MainScreen.checkSaveFile` at line 1051, including
  after those mods load. Disabling mods alone does not explain the report.
- Current local `42.21/media/lua/client/LastStand/TGSRR.lua` uses the legacy mode
  string `The Great Spiffo's Rat Race`. Its OnChallengeQuery handler calls
  `addChallenge`; vanilla `addChallenge` only populates the challenge list.
  TGSRR's SelectedChallenge registration is an internal Lua lookup, not Java
  GameMode registration.
- In build `26221929`, `IsoWorld.setGameMode(String)` resolves a registered
  GameMode; Core and IsoWorld getters return that object. An unknown legacy
  mode resolves to null. Vanilla getSaveInfo prefixes bare save names with that
  mode, and MainScreen's missing-info branch dereferences it. This matches the
  observed failure, but Twist's exact mod package and save folder have not been
  compared or reproduced in-game.
- `GameMode` and `ResourceLocation` are exposed through LuaManager.Exposer.
  Public `GameMode.register(String, boolean)` rejects the default `base`
  namespace, which unnamespaced legacy strings imply. Direct Registry.register
  is marked `@HiddenFromLua`, so it is not a valid Lua alias workaround.
- The owner chose Lua-only compatibility and permits relocating test copies.
  No Java patch or automatic save migration is part of this change. No save
  corruption or general relocation of saves has been established.

### Lua-only RR Official save routing (27 October 2026)

- On 42.22, RR Official uses the built-in `Challenges` GameMode for storage and
  creates `Saves/Challenges/TGSRR_<generated name>`. No custom registry entry or
  Windows-invalid colon is needed. Keep the `TGSRR_` prefix when renaming test
  saves; it distinguishes official saves from unrelated challenge saves.
- The original challenge definition, ID `TGSRR`, and exported mode name
  `The Great Spiffo's Rat Race` remain unchanged. A narrow doChallenge adapter
  supplies the storage mode, and createWorld adds the prefix. Continue and Load
  resolve prefixed saves back to the original definition. Unrelated modes and
  unprefixed saves retain vanilla routing.
- SelectedChallenge resolves runtime GameMode objects using the save prefix;
  Identity and milestone filters retain canonical challenge names. MapSpawnSelect
  uses the returned GameMode object directly in the `42.22` implementation.
  Dead-save blocking covers the new folder convention. The adapter exists only
  in `42.22`. Unofficial CDDA/Sprinters compatibility is not included.
- Six focused Lua scripts pass: official_mode_42_22, challenge_context,
  challenge_evidence, dead_save_ui, milestone_snapshot and starting_location.
  The new test executes the installed vanilla Continue function. Prohibited
  global scans pass. Desktop tests alone are not the runtime acceptance proof.
- Actual 42.22.0 build `26221929` smoke test used the isolated profile
  `outputs/pz422-official-test`, with only TGSRR enabled. Created world
  `TGSRR_2020417414175672035`, entered gameplay, saved and quit to menu, then
  successfully used Continue to restore it. Console records the same run
  `rr-1793141551-1793141551967-529870-810837` as session 1 then session 2.
  Run metadata preserves `startingChallengeId=TGSRR` and the original mode name.
- The test character subsequently died; the final export and no-respawn UI ran.
  A separate vanilla IsoDoor.ToggleDoorActual null-player exception occurred
  during zombie activity. The original MainScreen null-mode error did not recur.
  This smoke test does not certify unrelated gameplay APIs.
- A copied legacy official save also passed an actual 42.22 load and save test
  (details below). Original saves remain untouched. No Workshop upload was performed.

### Existing-save copy test (27 October 2026)

- Repeatable setup and test steps: [isolated testing environment](MOD_TEST_ENVIRONMENT.md).

- Copied `Saves/The Great Spiffo's Rat Race/2026-10-03_20-39-43` into the
  isolated profile as `Saves/Challenges/TGSRR_2026-10-03_20-39-43_copytest`.
  Also copied its matching `Lua/TGSRR/Runs/<run ID>` directory into that profile.
  When relocating within the same profile, that run-history directory stays put.
- Selected the copy through Load, accepted vanilla's version-conversion warning
  for the copy, and entered gameplay as Eury Fightus. Console confirms
  `Loaded run rr-1791056531-1791056531266-363709-651386, session 2`.
  Saved and returned to the menu; the saved global mod data retains that same ID.
- The original session-1 log remains an exact prefix of the copied session log.
  Session 2 retains `challengeId=TGSRR`, the original game-mode name and character,
  with no added, removed or changed mod references. No tracker reset or exception
  was logged during this test.
- SHA-256 verification after testing confirms all 2,212 original save files and
  all four original run-history files are unchanged. Baseline hashes are in
  `outputs/legacy-save-copy-baseline.json`; test console is in
  `outputs/pz422-official-test/console.txt`.
- The save declares TGSRR and TGSRROptimized. Both mod folders were present, but
  the test ran the stock installed 42.22 executable, without an optimized JAR.
  This verifies identity continuity for this copy, not all older saves or full
  gameplay compatibility. Keep originals backed up when trying other saves.

### Dedicated 42.22 source (28 October 2026)

- Corrected the initial placement of the fix: the complete implementation now
  lives in `42.22`, with `versionMin=42.22`. Restored all `42.21` Lua files to
  their state before commit `19c0745b`. Shared `common` assets stay shared.
- Removed the runtime version gate from the 42.22-only adapter. Spawn selection
  consumes `getCore():getGameMode()` directly instead of converting it to text
  and looking the same object up again.
- The 27 October runtime results above were obtained before this folder split.
  They remain evidence for the routing logic, not a new runtime test of the
  reorganized package.

## Branch and worktree

- Canonical development branch: `codex/rat-race-dev`.
- Canonical local worktree: `The Great Spiffo's Rat Race`.
- Live challenge branch: `master`.
- Website and Project Zomboid mod contracts evolve together on the unified
  development branch. The separate historical development worktrees are no
  longer authoring workspaces.
- The modular tracker baseline is committed at `737331b`.

## Outdoor weather extremes (14 October 2026)

- Daily and independent run-wide minimum/maximum temperatures now sample
  `ClimateManager:getTemperature()` at initialization and `EveryOneMinute`,
  regardless of the player's location. Each extreme retains Celsius, UTC,
  world age, in-game time of day and a one-based calendar date. Equal readings
  retain their first occurrence. Collection stops with the active run.
- Completed days seal their observations in `day.started.completedDay`;
  exports also carry the unfinished day and run-wide `outdoorTemperature`.
  Existing saves disclose partial temperature history. Old ledger entries are
  not changed and missing observations remain unknown.
- Desktop collection/export checks cover rollover, resume, ties, signed
  temperatures, partial history and terminal runs. In-game sleep/fast-forward
  verification remains outstanding. Website approval now normalizes daily and
  run-wide observations and presents the temperature history modal.

## Daily weight observations (14 October 2026)

- New completed and active days include measured `weightKilograms` alongside
  the existing signed delta. Both use the same Nutrition sample. Zero-change
  days still retain their weight; old immutable ledger entries stay unchanged.
- Website approval stores nullable daily weights. Historical omissions remain
  unknown, without reconstruction. See the export contract and checklist.
- Focused desktop Lua collection and benchmark checks pass. In-game export
  verification remains outstanding.
- On 14 October the generated Team Test package and local Team Test authoring
  folder were updated, including these weight changes and the current export
  updates. All packaged Lua hashes match; Workshop upload remains outstanding.

## Build 42.21 baseline (24 September 2026)

- Created from the current 42.20 implementation, preserving 42.20 as a prior version.
- Steam Unstable build: `25485521`.
- Fixed the logged `ExteriorEnvelope.lua` door lookup failure using the exposed
  `GridSquareEdgeFacingDirection` enum, verified against build `25485521`,
  decompile job 13, and vanilla `Tutorial1.lua`. North maps to `NORTH_SOUTH`,
  west to `EAST_WEST`; the wall lookup still accepts a Boolean.
- Desktop regression coverage verifies both door orientations, open/closed
  states, walls, gaps, missing squares, and shared scan reuse. An in-game church
  regression check remains necessary; full 42.21 compatibility is not yet claimed.

## Current deliverable

Build a modular, player-facing Rat Race Challenge Tracker with:

- An **Overview** tab for aggregate challenge deliverables.
- Dedicated system tabs, beginning with **Outposts**.
- A stable boundary between provisional diagnostics and final deliverables.
- A player-facing Outpost Overview distinct from the debug Inspector.

See [MOD_CHALLENGE.md](MOD_CHALLENGE.md), [MOD_TRACKER.md](MOD_TRACKER.md), [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md), [MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md](MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md), and [MOD_DECISION_015_SOURCE_LAYOUT.md](MOD_DECISION_015_SOURCE_LAYOUT.md).

The active implementation and all current tracker work target Project Zomboid
Build 42.21 under `Contents/mods/Great Spiffo's Rat Race/42.21`. Earlier
version directories are retained only as historical mod versions.

Run-history and TGSRR-owned collection design is documented in [MOD_RUN_DATA.md](MOD_RUN_DATA.md), with implementation status maintained in [MOD_EXPORT_CHECKLIST.md](MOD_EXPORT_CHECKLIST.md). Techniques audited from unrelated mods are retained strictly as implementation research in [MOD_REFERENCE_DATA_COLLECTORS.md](MOD_REFERENCE_DATA_COLLECTORS.md).

Custom helicopter scheduling and ranch mortality are gameplay systems outside
the export contract; their policy and test surfaces are documented in
[MOD_GAMEPLAY_SYSTEMS.md](MOD_GAMEPLAY_SYSTEMS.md).

## Implemented on the development branch

- Persistent, sandbox-configurable custom helicopter scheduling across nine
  challenge years, retaining the vanilla helicopter event while replacing its
  recurrence and exposing a debug schedule/jump window.
- Server-authoritative, sandbox-controlled ranch-zone interception and one-time
  population with configurable vanilla-shaped sex-specific mortality,
  adjacent-zone grouping, persistent spawn results, and clean vanilla fallback.
  Existing and connected livestock designations are adopted without duplicate
  population, TGSRR-owned designations use a visible `[TGSRR]` prefix, and the
  standalone Better Ranch Spawns mod is declared incompatible.
- Generic `TGSRR.ChallengeTracker.registerModule()` registry.
- Overview, Kills, Skills, Outposts, and Landmarks modules in a fixed-size
  `800x650` tabbed window.
- Generic `ChallengeDeliverables` provider registry and normalized Overview record boundary.
- Overview summaries for Outposts, Skills, and Kills.
- Event-driven Kills deliverable and detail tab using `OnZombieDead` and the persisted Character Info zombie-kill counter with a `1,000,000` target.
- Cumulative player-credited zombie kill classification for standing, face-down,
  face-up, fence-assisted, and window-assisted deaths. Fence/window traversal is
  tagged on zombie ModData through prone/get-up recovery and produces a
  debug-console classification at death.
- Generic challenge event bus, persistent milestone ledger, registry-driven awards, and localized halo notification presenter.
- Kill milestones at 1,000, 10,000, 25,000, 50,000, 100,000, 250,000, 500,000, 750,000, and 1,000,000, shown on the Kills tab and emitted only when thresholds are crossed.
- Dynamic all-skills level-10 deliverable grouped by vanilla skill category, with ten-segment per-skill progress, aggregate fractional progress, and event-driven refresh.
- World-scoped Rat Race run identity foundation with immutable `runId`,
  starting-character metadata, versioned `run.meta.txt`, and timestamped
  session/mod-list history. The `.txt` suffix is required by Build 42.20's
  Lua file-writer extension allowlist.
- Immutable starting-location evidence captured with XYZ, optional BuildingDef
  ID, UTC, world age, and explicit partial status for existing saves.
- Pre-world spawn-region evidence captures explicit or blind-random selection,
  the resolved raw Project Zomboid region ID, and UTC. The Random option remains
  unresolved and hidden until the final Start action.
- Canonical schema-2 event codec, SHA-256 hash-chained ledger, append-safe
  segmented storage, and lifecycle verification. Unsupported development run
  schemas are rejected rather than migrated.
- Development run-state schema 23 establishes the expanded authoritative daily
  record state, bounded outpost lifecycle state, and first-completion-only
  outpost ledger evidence. Earlier development runs are deliberately reset
  rather than migrated.
- Interrupted session commits are recovered automatically when the external
  ledger and session log are ahead of the save by session-boundary records
  only. The full tail is hash-verified, adopted without rewriting it, and a
  `run.recovery.decided` evidence event records the saved and adopted cursors,
  plus `decider = { type = "system", id = "tgsrr" }` so exports identify the
  automatic decision authority without website-side inference.
  Ahead gameplay events open a paused recovery decision. Continuing freezes the
  verified ahead tail as immutable superseded evidence, advances to a new epoch,
  and resumes from the restored save checkpoint; declining leaves tracking
  stopped. Recovery-epoch creation is idempotent across another crash.
- Current projections expose neutral recovery status, the active epoch, all
  recovery decisions, immutable recovery metadata, and the complete superseded
  event bodies. Accepted totals follow only the active branch; the website owns
  moderator approval or denial.
- Run-wide initialization, integrity, event-recording, and asynchronous
  collector failures display an always-on-top in-game warning explaining that
  tracking stopped, the exact machine-readable reason, and the risk to progress.
  The warning pauses gameplay and reasserts the pause after dismissal so
  vanilla modal cleanup cannot silently resume an unrecorded session.
- Power-cut clock reconciliation uses two alternating checksummed files written
  after successful save attempts. A checkpoint binds the saved ledger cursor to
  calendar, world age, time of day, nights survived, and character survival
  hours. Matching clocks do nothing; independently provable disagreement pauses
  for an explicit repair decision and records `run.clock.repaired` evidence.
- TGSRR-owned daily history with UTC/world-age day boundaries, daily kill deltas, and non-zero per-skill XP deltas.
- TGSRR-owned weapon-kill attribution keyed by full item type or explicit
  non-item pseudo ID, with cumulative totals, completed-day deltas, active-day
  deltas, and partial-baseline disclosure for existing runs.
- Projection schema 2 now emits only non-zero skill rows and omits empty,
  complete weapon-kill, fire-death, and zombie-kill-type sections. True partial
  flags and attribution baselines remain explicit evidence.
- Separate cumulative, completed-day, and active-day zombie fire-death counts
  that never contribute to vanilla or weapon-kill totals.
- Permanent first-visit tracking for 12 canonical towns using stable TGSRR IDs,
  map-reviewed multi-point coverage with per-point radii, hash-chained
  `town.visited` events, and partial-history disclosure for runs bootstrapped
  on an existing game save.
- Immutable skill-book and recipe-magazine read-state baseline plus hash-chained
  successful-reading deltas from PZ's authoritative `ISReadABook.complete()`
  edge. Leisure and generic print media are excluded.
- Versioned 21-landmark registry, lightweight first-visit collector, optional
  tracker deliverable, and exported location projection. Registered
  multi-building sites reconcile to one permanent discovery.
- Persistent internal first-entry history for every physically occupied
  BuildingDef, including real/game timestamps and XYZ. It is available for
  future registry reconciliation, marks incomplete historical coverage as
  partial, and is intentionally excluded from ledger and export.
- Compact loaded-mod history: a complete initial Mod ID/Workshop ID baseline followed by timestamped added, removed, and changed-association session deltas.
- Versioned, deterministic LZSS/Base64URL run exports containing the complete verified event history, integrity metadata, and a live current-kills projection.
- Format-4 exports split history into independently compressed 64-event
  blocks. A disposable local cache reuses exact unchanged blocks while the
  website still verifies every submitted block and the complete hash chain.
- Pre-spawn capture of the raw namespaced trait IDs selected on the character-creation screen, persisted across the loading transition and consumed only by the matching new character.
- Format-4 current-state projection containing challenge evidence; character and
  trait state; current skills; sparse non-default outpost state; ordered first outpost
  completions; kill and outpost-deliverable milestones with elapsed days; all 12
  town-visit states; versioned non-town location state; filtered skill-book and
  recipe-magazine baseline/current/completion state; rules-versioned Tracker summaries; current
  active mods; cumulative filtered distance travelled; and a non-mutating
  active-day snapshot with live kill, per-skill XP, and distance deltas.
- Cooperative pause-menu export flow with progress presentation, read-back
  verification, and absolute file-path copy. Only the current development
  export format is accepted.
- Export progress and result dialogs preserve the paused state when closed.
  Death is recorded immediately, with automatic export delayed by ten real-time
  seconds to allow the death animation to play before the export pauses gameplay.
  A manual export cancels the pending automatic export.
  TGSRR overrides vanilla modal cleanup for these dialogs because vanilla
  otherwise resumes gameplay after OK or Close.
- Debug-only synthetic export window offering one, two, five, and ten-year
  benchmarks. Each builds the corresponding deterministic daily records in
  memory, sends them through the real event codec and exporter, and writes a
  separately named export without changing the saved run ledger. Benchmark
  history is isolated from mutable live-session events, so its block identities
  remain stable across game restarts and repeated tests measure cache reuse.
- Export progress overlays show a live hours, minutes, and seconds elapsed
  timer for ordinary and synthetic exports.
- Every export remains saved under `Zomboid/Lua/TGSRR/Runs`. The result window
  copies the absolute file path for website upload and never sends the export
  payload through Project Zomboid's fixed native clipboard stack.
- Export benchmarks report encode, manifest-decode, ledger, reused-block and
  rebuilt-block stage results. New blocks are decoded and compared with their
  source records before caching. Repeat exports verify the manifest and exact
  block boundaries without decompressing unchanged local cache blocks.
  SHA-256 uses cached byte-operation tables while retaining the existing
  standard test vectors and hash format.
- Generic `skill.level.reached` events contain the skill, parent category, and
  reached level. The first level-10 event per skill is exported as its milestone
  with completion order and elapsed days; levels 1-9 remain ordinary history.
- Rising-edge events for individual outpost deliverable completion and whole-outpost completion; initial observations do not retroactively award milestones.
- Local-player broken weapons captured through Build 42 `OnBreak` callbacks plus
  post-swing condition verification, with full item IDs, cumulative totals, and
  daily deltas. Individual breaks are not ledger events.
- Deliberate local-player animal slaughter captured from Build 42's two
  successful `Kill Animal` action completions, with a cumulative total,
  cumulative raw animal-type totals, and per-type daily deltas. Ordinary animal
  deaths, carcass butchering, and individual ledger events are excluded.
- Successful local-player `Check Trap` claims aggregated cumulatively by raw
  trap-animal category, full trap item ID, and their pairing, with paired daily
  deltas. Unclaimed hourly catches and individual ledger events are excluded.
- Conservative domestic-birth reconciliation across loaded world, connected
  hutch, and trailer animals. Persistent TGSRR animal identities prevent
  recounts; exports contain only cumulative and daily raw newborn-type totals,
  not animal identities or individual birth events.
- Saved window position, selected tab, open state, and movable launcher position.
- Default-enabled danger auto-close for the Challenge Tracker and Outpost
  Overview. It uses vanilla Search Mode's zombie-danger thresholds: any very-close
  zombie, or at least three visible zombies while at least three are chasing.
- Incremental local-player milk collection captured at Build 42.20's
  authoritative `ISMilkAnimal:milk()` transfer edge, including partial fluid
  increments, with cumulative raw milk-type totals and daily deltas.
- Successful `Base.churn_butter` production observed through Build 42.20's
  `ISWidgetHandCraftControl` action start/completion/cancellation callbacks,
  after `ISHandcraftAction:performRecipe()` creates and awards `Base.Butter`,
  with cumulative totals and daily deltas.
- Local-player fishing catches captured from the landed-fish pickup action,
  excluding trash and fishing nets, with cumulative full-item-ID totals and
  daily deltas.
- Completed local-player animal pets aggregated cumulatively and daily by raw
  animal type, separately from cooldown-limited petting benefits.
- Actual manually and automatically consumed fluid litres aggregated
  cumulatively and daily by raw fluid type, with mixtures explicitly classified.
- Applied food/fluid calories accumulated independently of the continuously
  changing, clamped Nutrition balance, with independently recorded daily deltas.
- Successful generator repair actions and authoritative condition restored
  accumulated without per-repair ledger events, with daily deltas sealed at
  day boundaries.
- Movable `Item_DeadRat.png` launcher with runtime outline and no button chrome.
- One-second refresh that updates stable list entries in place.
- Weighted Outposts percentage derived from the arithmetic mean of the 14 weighted individual percentages.
- Overall Overview progress derived from available required category
  percentages, excluding optional Landmarks.
- Duplicate-safe vanilla world-map annotations for landmarks and outposts,
  with map navigation routed through vanilla's map-opening timed action.
- Outpost registration API, 13 definitions, configured core zones, `150x150` clearance bounds, registered BuildingDefs, and manual inaccessible-room exclusions.
- Room activation via `RoomDef:isExplored()` and loaded-square diagnostics.
- Persistent outpost discovery when the player enters a configured `150x150` clearance area.
- Weighted per-outpost progress across all 14 deliverables, strict Complete derivation, Completed / 13 Overview count, and arithmetic-mean aggregate progress.
- Persisted per-deliverable discovery baselines and a monotonic `In Progress` stage triggered by non-zombie improvement.
- Live outpost evaluation on area entry/load, room changes, zombie deaths, and a one-second in-area fallback.
- Disposable-schema `shared/TGSRR/Outposts/ProgressStore` with normalized, change-only persistent deliverable snapshots.
- Cached exterior-envelope geometry followed by lightweight one-second window/barricade checks.
- Persistent room activation, floor activation, zombie clearance, window-barricade, enclosure, fitted-door, closed-door, and good-bed records.
- Registered-room reverse lookup routes good-bed object additions/removals to one outpost and maintains a persistent fixture ledger without scanning for challenge fixtures.
- Deliverable-ledger changes notify open tracker views immediately; their one-second refresh remains a presentation fallback.
- Debug survey, zone editor, teleport controls, and activation Inspector.
- Debug survey of loaded ground-floor exterior windows, frames, player-built windows, and barricades.
- Respawn removal for all Rat Race challenge variants.

## Provisional implementation

- Tracker dimensions have an `800x650` minimum. Tracker tabs and Outpost
  Overview columns measure their actual localized text and grow only when that
  content needs more width. Width and height are never restored from saved state.
- Outposts columns are passed `Requirements`, strict `Stage`, and weighted `Progress`; room and floor detail remains available in the tooltip.
- Tracker-owned player-facing strings and all 13 title-case outpost names use TGSRR `getTextOrNull` translation keys.
- Outpost rows use vanilla's tintable `Cross` world-map symbol as a consistent church marker.
- Hog Wallow Military Base uses vanilla's tintable `CrossedSwords` map marker.
- Double-clicking an outpost opens the localized player-facing Outpost Overview with the full persisted deliverable set.
- The player-facing Outpost Overview displays all current completion checks and last-known persisted values.
- Outpost Overview rows provide localized requirement tooltips, and the window remembers its screen position, open/closed state, and selected outpost.
- Tracker launches for Standard, CDDA, and Sprinters variants. Exports preserve
  the current raw Project Zomboid challenge ID and game-mode name; the website
  maps those values for presentation and determines submission eligibility.

## Not implemented

- Zombie totals and last-observed populations are intentionally excluded from tracker snapshots. Zombie clearance is exposed only as a permanently latched binary status.
- Hunger fulfilled remains explicitly deferred because it overlaps calories
  consumed without a current scoring or presentation use.
- Skill milestone award selection (individual skills, categories, or selected levels).

## Recommended next action

Run a fresh in-game schema-2 export smoke test, including repeated engine-start
completion and range regression, then approve it locally and inspect the
expanded 13-outpost and 169-deliverable authority.

## Related decisions

- [MOD_DECISION_001_TRACKER_ARCHITECTURE.md](MOD_DECISION_001_TRACKER_ARCHITECTURE.md)
- [MOD_DECISION_002_OVERVIEW_DELIVERABLES.md](MOD_DECISION_002_OVERVIEW_DELIVERABLES.md)
- [MOD_DECISION_003_CHALLENGE_CONTRACT.md](MOD_DECISION_003_CHALLENGE_CONTRACT.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
- [MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md](MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
- [MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md](MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
- [MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md](MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md)
- [MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md](MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md)
- [MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md](MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md)
- [MOD_DECISION_015_SOURCE_LAYOUT.md](MOD_DECISION_015_SOURCE_LAYOUT.md)
- [MOD_DECISION_016_SKILL_TRACKING.md](MOD_DECISION_016_SKILL_TRACKING.md)
- [MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md](MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md)
- [MOD_DECISION_018_BUILDING_VISIT_HISTORY.md](MOD_DECISION_018_BUILDING_VISIT_HISTORY.md)
- [MOD_DECISION_019_STARTING_LOCATION.md](MOD_DECISION_019_STARTING_LOCATION.md)

## Character sex export (14 October 2026)

- Character identity exports `sex` as `male` or `female`, sampled using
  `player:isFemale()`, also used by vanilla ISBodyPartPanel. New runs retain
  the starting value; existing runs capture the current value on their next
  export without rewriting missing historical starting data.
