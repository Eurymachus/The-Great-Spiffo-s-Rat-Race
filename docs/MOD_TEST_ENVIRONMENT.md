# Isolated mod testing environment

Run local save compatibility tests in a separate PZ profile under
`outputs/pz422-official-test`. This directory is ignored by Git and is not a
Workshop package. Use the stock installed 42.22 executable for Lua-only tests.

## Prepare the profile

Close the test game before copying files. From the repository root:

```powershell
$testRoot = Join-Path (Get-Location) 'outputs\pz422-official-test'
$sourceMod = Join-Path (Get-Location) "Contents\mods\Great Spiffo's Rat Race"
$testMod = Join-Path $testRoot 'mods\TGSRR'
New-Item -ItemType Directory -Force -Path $testMod | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceMod '42.21') -Destination $testMod -Recurse -Force
Copy-Item -LiteralPath (Join-Path $sourceMod 'common') -Destination $testMod -Recurse -Force
Start-Process -FilePath 'C:\Games\Steam\steamapps\common\ProjectZomboid\ProjectZomboid64.exe' -WorkingDirectory 'C:\Games\Steam\steamapps\common\ProjectZomboid' -ArgumentList ('-nosteam "-cachedir=' + $testRoot + '"') -WindowStyle Hidden
```

Enable TGSRR through the game's Mods menu on first launch. First-start setup
can reset a prewritten mod-selection file. Use a fresh profile when deleted
source files would otherwise remain in an existing copied mod directory.
The normal profile's saves and mod selection are not used by this launch.

## Fresh RR Official save

1. Start RR Official and enter gameplay. Check that the world is stored under
   `Saves/Challenges/TGSRR_<world name>` inside the isolated profile.
2. Record the `[TGSRR Run]` run ID in that profile's `console.txt`.
3. Save and quit to the menu, then use Continue. Confirm the same run ID and
   an incremented session number. Check Load also recognizes the save.
4. Keep the `TGSRR_` prefix when renaming saves. It identifies RR Official
   within the shared `Challenges` storage mode.

## Copy an existing RR Official save

1. Close the game. Select a living character's save from
   `<original profile>/Saves/The Great Spiffo's Rat Race/<old name>`.
   Record its run ID from its existing run metadata or global mod data.
2. Record a SHA-256 manifest of all source save files and the matching
   `<original profile>/Lua/TGSRR/Runs/<run ID>` files before copying.
3. Copy the complete save folder into the test profile as
   `Saves/Challenges/TGSRR_<old name>_copytest`. Use a destination that does
   not already exist; never merge different saves or move the original.
4. Copy the complete matching `Lua/TGSRR/Runs/<run ID>` directory into the
   same relative location in the test profile. This preserves external run
   history and checkpoints. Within one profile, leave that directory in place
   when relocating just the save. Do not alter the run ID or edit binary data.
5. Make the save's declared mods available in the isolated profile. Retain
   the original mod IDs: `TGSRR-test` and `TGSRR` are different packages.
   Record any changed mod set when interpreting the session evidence.
6. Launch with the command above, select the copy through Load, and accept
   the game's version-conversion prompt for the copy. It can appear again
   after the game reloads Lua to match the save's mod list.
7. Enter gameplay, then pause. Confirm `Loaded run <original ID>, session N`
   in `console.txt`, without a tracker reset. Check the appended
   `sessions.log` entry retains `challengeId=TGSRR`, the original mode name,
   character identity, and expected mod delta. Existing session records must
   remain intact.
8. Save and quit. Confirm the saved global mod data still contains the
   original ID. Recompute the source hashes and compare file lists as well
   as hashes to establish that all original files remain unchanged.
9. Record results and limitations in `MOD_NOW.md`. Preserve the isolated
   copy and logs for inspection. Never submit test-run exports to standings.

The 27 October 2026 test used `2026-10-03_20-39-43`, copied as
`TGSRR_2026-10-03_20-39-43_copytest`. Run
`rr-1791056531-1791056531266-363709-651386` resumed as session 2 and saved
with its original ID. All 2,212 source save files and four run-history files
remained unchanged. The local hash baseline is
`outputs/legacy-save-copy-baseline.json`. TGSRROptimized assets were present
to match the save's mod list, but no optimized JAR was used. This is a load
and identity test, not a full gameplay or optimization compatibility audit.

See [current mod results](MOD_NOW.md) and the separate
[team-test Workshop packaging procedure](TEAM_TEST_WORKSHOP.md).
