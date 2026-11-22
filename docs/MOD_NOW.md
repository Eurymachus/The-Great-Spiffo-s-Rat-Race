# Mod: Current Focus

## Farming statistics (21 November 2026)

- Implemented in 42.22: verified ploughed-to-seeded sowings and successful
  harvests by raw crop key, plus actual harvested produce by full item type.
  Credit follows the local harvester, regardless of vanilla plant owner.
- Successful completion and authoritative plant-state changes are required;
  cancelled/foreign/stopped-run actions and duplicate callbacks do not count.
  Regrowth harvests count again. Seed consumption alone does not prove sowing.
- Harvest-only before/after output counts are capped by the observed vanilla
  yield roll. This excludes extra seeds even where seedName and vegetableName
  are the same item (corn, peppers, barley). Extra produce is included; seed-only
  items and ordinary looting are excluded. No yield reroll or per-tick scanning.
- `farming` exports independent cumulative `planted`, `harvested` and `produce`
  maps, schema 1 and partial coverage. Daily maps are `farmingPlantedDeltas`,
  `farmingHarvestedDeltas`, `farmingProduceDeltas`. Approval stores separate
  summaries and crop/item dimensions. Existing saves have partial coverage.
- Installed vanilla-action/harvest Lua tests, daily rollover/reload regressions,
  23 focused website tests, syntax and prohibited-global checks pass.
- In-game test confirmed on 22 November, run
  `rr-1795374245-1795374245421-744936-711157`: three plantings,
  Basil 1, BellPepper 1 and BlackSage 1. Subsequent export records one Basil
  harvest and four `Base.Basil` produce items; planting counts remain unchanged.
  Both exports pass website validation; cumulative and day-1 deltas agree.
  Harvest was tested after debug-assisted crop growth. This confirms capture,
  not natural growth timing.
- Repeat-harvest and daily-rollover test confirmed on 22 November in the same
  run: cumulative plantings remain Basil 1, BellPepper 1 and BlackSage 1.
  Harvests are Basil 2, BellPepper 1 and BlackSage 1; produce totals are
  `Base.Basil` 8, `Base.BellPepper` 2 and `Base.BlackSage` 3.
  Sealed day 1 contains both Basil harvests and the BlackSage harvest (11
  produce items); active day 2 contains the BellPepper harvest (2 items),
  with no new plantings. The export passes validation and daily sums exactly
  match the independent cumulative totals: 3 plantings, 4 harvests, 13 items.
  This confirms repeat Basil harvesting from one planting and daily rollover.
  Seed-bearing yield separation, cancellation and save/reload remain separate
  outstanding in-game checks.
- Terminal-export test confirmed on 22 November in the same run:
  projection lifecycle and `run.ended` event sequence 7 both report `deceased`.
  Export validation passes. Farming totals remain 3 plantings, 4 harvests and
  13 produce items; sealed day 1 and active day 2 counts remain unchanged and
  agree with cumulative totals. This verifies farming evidence survives the
  death/terminal export, not save/reload or attempted post-death collection.
- Team Test refreshed on 22 November; all 616 mod files verified against source.
  The C: and E: profile paths are aliases for the same physical package,
  not two independent copies. Workshop metadata preserved; no upload.
  The earlier export lacked farming coverage because the package was stale.


## Cooked food collected (21 November 2026)

- Implemented in 42.22: successful solo transfers and ground pickups into the
  player's inventory/carried bags, including food inside acquired bags. Eligible
  Food items are cooked or tagged AlreadyCooked, and not burnt. No chef attribution.
- Persistent item ModData `TGSRRCookedFoodRunId` prevents the same item counting
  again after storage, retrieval, repeated callbacks or reload. Existing carried
  food is baselined once without credit when the collector is introduced.
- Cumulative raw full-item-type counts are independent of daily history.
  `cookedFood = {schema = 1, items = {...}, partial = true?}` exports with sparse
  `cookedFoodItemsDeltas` and coverage metadata. Approval normalizes item metrics
  and a cumulative summary. Missing historical coverage remains unknown.
- Keep this slice simple: no recipe/portioning marker propagation, cooking-XP
  inference, appliance scanning or per-item export ledger. New items created by
  slicing or transformations may count separately on later collection.
- In-game collection and storage/retrieval test confirmed on 22 November,
  run `rr-1795375945-1795375945361-908624-308765`: collecting one cooked
  fish fillet records `Base.FishFillet = 1` in cumulative items and the day-1
  delta. After the owner stored and retrieved that same fillet, both values
  remain exactly 1. Both exports pass validation, confirming no double count
  on this storage/retrieval path.
- Desktop collector, daily rollover/reinitialization and website validation tests
  pass. Whole-bag pickup, save/reload, midnight rollover, raw/burnt exclusions
  and collection of a second distinct item remain outstanding in-game checks.
  Team Test updated and all 614 mod files verified on 21 November. The C: and
  E: profile paths refer to the same physical package. Metadata preserved;
  no Workshop upload.


## Travel mode distance (21 November 2026)

- Replaced `OnPlayerMove` sampling with a constant-memory `OnTick` collector.
  Java build 26486631 emits the movement event from `justMoved`; vehicle
  occupants have their positions updated separately, so the old collector
  did not reliably measure vehicle routes.
- Store independent on-foot and driving metres alongside the total.
  Use `getVehicle()` and exposed `BaseVehicle.isDriver(player)` (also called
  by vanilla vehicle UI/actions). No route history or per-movement ledger.
- Stationary ticks skip square roots. Moving ticks use squared plausibility
  checks, scaled for game speed; reject steps above 50 tiles. Reset the spatial
  baseline on vehicle/role changes, reloads, invalid coordinates and gaps over
  one real second. Transition intervals are deliberately omitted. These are
  sampled planar distances, not guaranteed exact paths or teleport detection.
- Persist two counters and export cumulative values plus daily deltas.
  Approval stores two typed statistic summaries and nullable daily metres.
  Older cumulative mode coverage is partial; absent historical daily breakdowns
  remain unknown. Migration 0073 adds daily fields and summary choices.
- Validation: 94 website tests passed, followed by three focused distance tests
  after daily-total validation was added. Lua collector/daily/reading regressions,
  actual Lua format-4 to Python decoding, syntax and prohibited-global scans
  pass. Migration 0073 applied locally. Both Team Test copies regenerated and
  all 612 mod files verified, preserving unlisted metadata. No Workshop upload.
- In-game test run `rr-1795272441-1795272441421-553973-256261`:
  first walk exported 10.569395346465976 m on foot and zero driving (Twist
  displayed 10 m; this comparison is not a measured-route accuracy check).
  Further seated driving increased driving from 147.12007339899972 to
  185.68511079314385 m while on-foot stayed exactly 39.974607383098984 m.
  After exiting, driving reached 186.13080273046808 m and walking reached
  53.26266770324388 m. The owner confirmed the extra 0.44569193732423 m
  driving was the car rolling to a stop after unpausing.
- Save/reload without movement preserved both counters exactly and retained
  zero rejected samples. The next export sealed day 1 at 54.69581603499061 m
  on foot and 186.13080273046808 m driving. Active day 2 had
  1.3057826709771234 m on foot and zero driving, with cumulative on-foot
  56.00159870596773 m. All inspected exports passed website validation;
  cumulative/daily values agree within ordinary floating-point precision.
- Confirmed in game: foot/driver separation, persistence and daily rollover.
  Known-length route accuracy, fast-forward and deliberate teleport rejection
  remain separate acceptance checks. Existing desktop tests cover rejection.
- In-game acceptance: walk/run a route, drive a route, change
  seats, exit, pause, save/reload, fast-forward and cross midnight. Export after
  each phase and verify only the appropriate category grows, the total agrees
  on a new run, and stationary/transition/teleport movements add no false jumps.
  Non-driver seats are excluded from both categories and the tracked total.
  Passenger statistics were removed at the owner's request for the solo challenge.
  Migration 0074 removes the unused daily field and summary choice. Focused
  website/Lua tests and Lua-to-Python export checks pass for the two-category
  contract; both local Team Test copies were regenerated and verified again.



## Terminal death evidence (21 November 2026)

- Further infected-fall export validated: run
  `rr-1795260350-1795260350371-798215-158712` captures `infectedAtDeath=true`
  and `killedByFall=true`, with `deathDragDown=false`. Cause is `fall` with
  `explicit_flag`; latest `FALLDOWN` damage is 1010, 573 ms before death, at
  tile `(12492, 1608, 0)`. This confirms an explicit fatal-fall classification
  alongside independently captured systemic infection in an in-game export.

- Infected-fall test export validated: run
  `rr-1795260116-1795260116118-172564-775650` captures `infectedAtDeath=true`
  independently of cause. Both terminal flags were false; the fallback records
  `FALLDOWN` as suspected, amount 8332.5, 45 ms before death, at tile
  `(358, 9867, 1)`. Do not describe this example as explicit fatal-fall detection.
  Investigate why the engine flag was false before assuming it covers every
  fall death; retain the observed flag and suspected-source evidence unchanged.

- Added optional `infectedAtDeath`, read from the exposed
  `BodyDamage.isInfected()` systemic zombie-infection flag during the death
  callback, independently of damage history and cause selection. True/false
  observations are retained; older exports, unavailable body damage and later
  recovery capture remain unknown. No ordinary wound-infection inference or
  inference about deliberate death is made. Existing terminal captures remain
  immutable. Approval stores nullable `RunDeathSummary.infected_at_death`.
- Migration 0072 applied locally. All 38 focused death/codec tests, Lua tests,
  actual Lua-to-Python export validation and prohibited-global scans pass.
  Both local Team Test packages regenerated and all 611 mod files verified
  against source with the intentional Team Test metadata substitutions.
  Restart PZ before testing infected fall/drag-down and an uninfected control.
  No Workshop upload or hosted deployment was performed.

- Accelerated zombie-infection test export validated: run
  `rr-1795259560-1795259560018-546598-328997` records both terminal flags false,
  last damage source and cause `INFECTION`, with certainty `suspected`. Its sole
  recent source is infection, amount 110, 25 ms before death, at tile
  `(411, 9761, 0)`, building ID `10696053409972248`. This validates the tested
  infection mortality path; ordinary-duration and mixed-source cases remain
  separate coverage questions.

- Bleeding test export validated: run
  `rr-1795259179-1795259179537-160385-118086` records both terminal flags false,
  last damage source and cause `BLEEDING`, with certainty `suspected`. Its sole
  recent source is bleeding, amount approximately 0.439939, 14 ms before death,
  at tile `(11534, 6932, 0)`, building ID `7600017644716067`. This supplies an
  in-game example of the bleeding suspicion path and retained building identity.

- Fire test export validated: run
  `rr-1795258407-1795258407592-643512-581764` records both terminal flags false,
  last damage source and cause `FIRE`, with certainty `suspected`. The sole
  recent source is fire, amount approximately 0.106655, 32 ms before the death
  callback, at tile `(9771, 12828, 0)`. This validates the suspected-source path
  for this fire test; it does not establish certainty for mixed damage cases.

- Fatal-fall test export validated: run
  `rr-1795258117-1795258117309-734807-656668` records `killedByFall=true`,
  `deathDragDown=false`, cause `fall` with `explicit_flag`, and terminal tile
  `(8082, 11674, 1)`. The last damage observation is `FALLDOWN`, amount 1000,
  767 ms before the death callback. Both fall and drag-down classifications
  now have an in-game example; subsequent tests are recorded above.

- First in-game export validated: run
  `rr-1795257762-1795257762261-267784-578790` records explicit zombie drag-down,
  `killedByFall=false`, terminal tile `(7222, 8288, 0)`, fall damage 5,128 ms
  earlier and bleeding 12 ms earlier. This confirms the flag takes priority
  over the most recent damage source in this case; later fall tests are above.
- That export exposed sparse location `partial=false` omission by the exporter.
  Import comparison now expands only that documented default on validated
  copies, preserving original event/projection evidence and rejecting changed
  locations or flags. The original export now validates unchanged; 37 focused
  death/codec tests pass. This fix is website-only, no Team Test rebuild needed.

- First slice implemented in 42.22 with the in-game examples above: capture XYZ,
  optional building/outpost/landmark, explicit fatal-fall and drag-down flags,
  and bounded recent damage observations in the existing `run.ended` event.
- Flags take priority; otherwise the last observed damage source within ten
  real-time seconds is labelled suspected. Retain other recent sources and
  their ages because callback order does not establish fatal causation.
- Export carries the same schema-1 `deathEvidence` snapshot. Website decoding
  verifies event/projection agreement and classification consistency; approval
  stores typed death summary and recent-source rows (migration 0069).
- No per-hit ledger or position trail. The transient window resets on runtime
  initialization/recovery; repeated terminal export preserves the first record.
  A later recovery capture is explicitly labelled and has no reconstructed
  damage history. Old exports without the field retain unknown coverage.
- See the terminal testing checklist in `MOD_EXPORT_CHECKLIST.md`. No confirmed
  general zombie-attack, poisoning-subtype or moodle-based diagnosis is claimed.
- Validation: 124 website/export/approval tests passed, followed by all seven
  focused death tests after validator hardening. Lua collector/terminal tests,
  changed-file syntax checks, actual Lua format-4 export decoded by Python,
  migration consistency and prohibited-global scans pass. Migration 0069 is
  applied to the local development database. No Workshop/hosted deployment
  was performed; subsequent in-game results are recorded above.

## Approved RR 2 food requirement (19 November 2026)

- Require 20,000 calories per outpost, increased from 5,000. Retain existing
  non-spoilable-food and storage eligibility rules, including nested bags in
  qualifying world-object containers in registered ground-floor rooms.
- Decision recorded while reviewing the extra objective proposals. Implementation
  and validation are pending; the current runtime has not been changed by this
  decision capture. Define treatment of existing runs without rewriting their
  historical completion evidence.
- Player-crafted weapons/tools are also approved below; other supply and
  location proposals remain undecided in `docs/IDEAS.md`.
- Applies to RR 2 development, not the separate RR 1.0 maintenance line.

## Approved RR 2 player-crafted weapons and tools (19 November 2026)

- Outpost weapons and tools must have been crafted by the player. Require one
  forged crowbar and one forged sledgehammer at every outpost, approved on
  19 November 2026. The remaining equipment list is undecided.
- The owner's rationale is to give required Blacksmithing progression a useful
  stocking purpose and make equipment obtainable through crafting. The expectation
  that most recipes unlock by level 9 remains to be verified against the current
  build before selecting items.
- Quantities, condition thresholds, eligible items, shared weapon/tool credit,
  firearms/ammunition and treatment of earlier crafts remain undecided.
- Implementation is pending. Verify individual-item crafting provenance;
  possessing a forged item or a cumulative crafting count alone is insufficient
  evidence that the stored item was crafted by this player.

## Custom GameMode save-path report (16 November 2026)

- Official TIS report: [42.22.2: Custom GameMode names create invalid save paths on Windows](https://theindiestone.com/forums/topic/103293-42222-custom-gamemode-names-create-invalid-save-paths-on-windows/).
- The temporary `TGSRR:test` challenge registered successfully on build
  `26486631`. Console confirmed that `createWorld()` returned with that mode,
  followed by "The savefile directory doesn't exist" and the game closing.
  This reproduced the failure within the development mod with other mods
  enabled; an isolated reproduction has not been recorded.
- Public GameMode registration requires a non-base namespace, but the save
  path uses the identifier unchanged, including the Windows-invalid colon.
  Working vanilla challenges use private, hardcoded `registerBase()` entries.
  Retain the existing `Challenges/TGSRR_<name>` compatibility routing.
- Related report: [CDDA save conversion and Sandbox fallback](https://theindiestone.com/forums/topic/103113-42222-the-issue-of-converting-a-save-from-the-a-really-cd-da/).
  CDDA's missing built-in registration is distinct from the namespaced-path
  failure. No TIS fix or acknowledgement has been verified.
- Temporary probe: `42.22/media/lua/client/LastStand/TGSRR_SaveProbe.lua` under
  the mod source. Remove before release.

## Build 42.22.2 reference (10 November 2026)

- Installed Steam build `26486631`; the 10 November game console confirms
  `42.22.2`. The desktop manifest reports mounted `pre-release` but configured
  `public`; no Steam update or branch change was performed.
- Vineflower job 17 completed and validated
  `tgsrr_decompiled/build-26486631-job-17`. Verified `.tgsrr-build-id`,
  `zombie/characters/skills/PerkFactory.java` and `zombie/Lua/LuaManager.java`.
  Older reference directories remain intact.
- Decompiler limitations: method-writing warnings for Okio `commonSnapshot`
  and `snapshot`, and Kotlin reflection `getTypeName`. Successful sentinel
  validation is not a guarantee that every bundled method decompiled fully.
- Active mod development remains under `42.22`. No catalogue promotion was
  performed.
- Rat Race 1.0 maintenance is approved as a separate branch; see below.

## Rat Race 1.0 maintenance branch (10 November 2026)

- Created local `codex/rat-race-1.0-maintenance` from `master` at
  `a6e997c13112fe69c4b56e31259235b85b190683` (Add build 42.19 mod version).
  This is the legacy challenge implementation, without the RR 2.0 modules.
- Temporarily maintain 1.0 for 42.22.2 by porting narrowly scoped compatibility
  fixes. Do not merge the RR 2.0 development branch into this release line.
- Separate worktree created at
  `E:/LocalProfiles/Eurymachus/GameData/Zomboid/Workshop/The Great Spiffo's Rat Race - Legacy 1.0`.
  Its new `42.22` source ports spawn-screen routing, the map-mode comparison,
  legacy Random selection and registered-mode save routing for all three
  challenge variants. RR 2.0 modules were not imported. Changes are uncommitted;
  the branch has not been pushed or published.
- Verified the downloaded official Workshop item `3554864233` on 10 November:
  all 85 files match this branch's `Contents/` tree. There are 29 byte-identical
  files and 56 with only CRLF/LF differences; no content changes, additions or
  missing files. Local comparison and public SHA-256 hashes are recorded in
  `outputs/legacy-1.0-baseline/comparison.json`.
- Focused menu/save regression tests, seven-file Lua syntax checks and
  prohibited-global scans pass. Historical Contents remain unchanged.
  The legacy worktree has refreshed instructions and an isolated test profile
  with `tools/start-legacy-test.ps1`. Runtime testing of new games and copied
  existing saves remains required before release.
- The current workspace stays on `codex/rat-race-dev` with its uncommitted work
  preserved. Team Test continues to carry RR 2.0 development content.

### Spawn selection bypass (10 November 2026)

- The installed 42.22.2 `NewGameScreen.clickPlay` challenge path unconditionally
  calls `useDefaultSpawnRegion` and opens character creation. It bypasses
  TGSRR's existing spawn list even when multiple regions are available.
- `TGSRR/Patches/SpawnSelection.lua` preserves vanilla initialization, then
  opens spawn selection for TGSRR, TGSRR_CDDA and TGSRR_Sprinters when choices
  exist. Other challenges and single-region flows retain vanilla behaviour.
- The regression executes the installed vanilla `clickPlay`, reproduces the
  bypass before patching, and verifies restored routing and one initialization.
  Spawn-selection, official-mode and starting-location desktop tests pass;
  prohibited-global scans are clear. In-game acceptance remains outstanding.
- Regenerated the local Team Test package on 10 November using the canonical
  generator, including this fix. Verified all packaged Lua hashes against the
  source and retained `TGSRR-test`. Restart PZ to load the refreshed package.
  This is not a Rat Race 1.0 release; no Workshop upload was performed.

## Build 42.22.1 reference (4 November 2026)

- Installed pre-release Steam build: `26409601`.
- Existing Vineflower workflow completed decompile job 16 successfully:
  `tgsrr_decompiled/build-26409601-job-16`. Verified the matching
  `.tgsrr-build-id` marker and `zombie/characters/skills/PerkFactory.java`.
- Previous reference directories are retained. Active mod development remains
  under `42.22`. Catalogue review and mod compatibility verification are separate
  outstanding work; this operation only refreshed the Java reference.

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
- Debug-only synthetic export window offers one, two, five, and ten-year
  fixtures covering every current completed-day counter, including distance
  modes, leisure reading, animals, milk, fluids, injuries, repairs and time.
  Fixture v2 writes deterministic ledger segments into a separate
  `<runId>-benchmark-v2-<days>` directory, then uses the normal exporter and
  `Ledger.readAll` disk verification path. No full synthetic history cache is
  retained. Repeat fixtures keep stable block identities for cache tests.
- Benchmark results include disk-ledger bytes, build/export stage timings and
  sampled JVM heap baseline/peak/end values for fixture building and export.
  A `.benchmark.txt` report is saved beside each synthetic export. PZ's exposed
  Kahlua `collectgarbage("count")` measures the whole JVM heap in KiB, not Lua
  allocations or process RSS. Samples occur at cooperative work checkpoints
  at least 10 ms apart and at stage boundaries; brief intervening peaks can be
  missed. No forced GC or OS cache clearing: newly written fixture reads are
  normally warm-cache reads. Synthetic exports remain unsuitable for submission.
- Validation: desktop regression uses real temporary files and the production
  ledger reader, checks every current daily metric, deterministic repeat
  fixtures, live-run isolation, a 256-record segment boundary, memory reporting
  and I/O/corruption failures. In-game JVM memory and long-run timings still
  need rerunning with this richer fixture; old benchmark numbers are not v2.
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
