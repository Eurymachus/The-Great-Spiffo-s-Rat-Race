# Team Test Workshop Item

The team-test item is a separate, unlisted Steam Workshop package generated
from the current repository contents. Its internal mod ID is `TGSRR-test`, so
it remains distinct from the public mod's `TGSRR` ID.
The package contains only the shared `common` content and the changed `42.20`
version. Historical game-version directories are not copied.

The test package is generated from production content, with only its displayed
name and internal mod ID changed in the copied `42.20/mod.info`.

## Prepare a new item

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1
```

The upload-ready package is written to `outputs/team-test-workshop`. Its
`workshop.txt` starts with an empty `id=` and `visibility=unlisted`. Select that
folder in the Project Zomboid Workshop uploader to create the item.

To create it directly in the local Project Zomboid Workshop authoring folder,
provide an absolute output path:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1 -OutputPath "C:\Users\refle\Zomboid\Workshop\The Great Spiffo's Rat Race - Team Test"
```

After Steam assigns the item an ID, retain that ID for future updates:

```powershell
powershell -ExecutionPolicy Bypass -File tools/prepare-team-test-workshop.ps1 -WorkshopId 1234567890
```

The generated package is excluded from Git. The source template and generator
are version controlled.
