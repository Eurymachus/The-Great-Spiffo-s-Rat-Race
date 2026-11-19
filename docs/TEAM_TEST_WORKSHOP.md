# Team Test Workshop Item

For local save/load tests and copied-save migration checks, follow the
[isolated mod testing environment](MOD_TEST_ENVIRONMENT.md).

The team-test item is a separate, unlisted Steam Workshop package generated
from the current repository contents. Its internal mod ID is `TGSRR-test`, so
it remains distinct from the public mod's `TGSRR` ID.
The package copies the versioned mod tree, including shared `common` content,
the active `42.22` version, and retained historical versions.

The test package is generated from production content, with only its displayed
name and internal mod ID changed in the copied version-specific `mod.info` files.

## Regenerate the local Team Test copy

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1
```

By default this replaces the actual local Team Test package in place at
`%USERPROFILE%/Zomboid/Workshop/The Great Spiffo's Rat Race - Team Test`.
On this machine, `C:/Users/refle/Zomboid` links to
`E:/LocalProfiles/Eurymachus/GameData/Zomboid`, so these are the same copy.
Its `workshop.txt` targets the existing unlisted Workshop item `3792308588`.
Restart PZ after regeneration so it loads the new Lua and version folders.
Regeneration does not publish a Steam Workshop update.

Only when an isolated upload/staging package is wanted, override the default:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1 -OutputPath "outputs/team-test-workshop"
```

The generator uses Workshop ID `3792308588` by default. The parameter remains
available if a different item must be targeted explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1 -WorkshopId 1234567890
```

The generated local package is outside this repository; `outputs/` staging
packages are ignored. The source template and generator are version controlled.
