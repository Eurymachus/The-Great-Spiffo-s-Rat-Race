# Rat Race Run Export Contract

## Challenge evidence

Format-3 exports may add the following object to the existing schema-1 run
projection without changing the export format or projection schema:

```json
{
  "schema": 1,
  "currentKills": 123,
  "character": {},
  "challenge": {
    "id": "TGSRR_CDDA",
    "gameMode": "The Great Spiffo's Rat Race - CDDA"
  }
}
```

Both values are raw evidence. The mod must preserve Project Zomboid's exact
spelling and casing and must not emit an official/unofficial verdict.

Current known IDs are:

- `TGSRR` → `TGSRR - Standard`
- `TGSRR_CDDA` → `TGSRR - CDDA`
- `TGSRR_Sprinters` → `TGSRR - Sprinters`

## Website ingestion

- The `challenge` object is optional for backward compatibility.
- When present, `gameMode` must be a non-empty string. `id` is preserved as an
  exact string but may be empty when an existing Project Zomboid save does not
  expose it.
- Every immutable submission stores both raw values.
- The website maps exact IDs through its managed Challenge Mode catalogue and
  aliases. When the ID is empty, it may map the exact raw `gameMode` name without
  inventing an ID.
- Unknown IDs remain valid evidence and display as unmapped.
- Older exports without challenge evidence display as `Legacy / Unspecified`.
- The run stores its immutable starting challenge evidence separately from its
  current approved snapshot.
- A changed non-empty challenge ID is a dangerous review finding and cannot be
  approved as a continuation of that run.
- A later generated snapshot may be approved when its verified event sequence
  and ledger head are unchanged. This allows current-state projection changes to
  advance the canonical run even when no new semantic event occurred. Equal or
  older generation timestamps do not supersede the approved snapshot.

## Starting-location evidence

Current exports include immutable raw starting-location evidence under the
character projection:

```json
{
  "character": {
    "startingLocation": {
      "x": 10835,
      "y": 10144,
      "z": 0,
      "buildingId": "10835,10144,0",
      "registeredLocation": null,
      "capturedUtc": 1784800000,
      "worldAgeHours": 0
    }
  }
}
```

Coordinates are integer world tiles. `buildingId` is the precision-safe
BuildingDef ID when the starting tile is inside a building, otherwise it is an
empty string. The website preserves these raw values and owns any later mapping
to a town, spawn region, map label, or other presentation geography.

When the observed tile matches a registered TGSRR outpost or landmark,
`registeredLocation` contains its stable `kind`, `id`, and `registryVersion`.
The value is `null` for ordinary or unknown buildings. Build-specific raw
BuildingDef IDs are deployment-installed mappings to the stable catalogue entry;
they are not themselves treated as permanent identities.

An omitted `partial` field means false. When tracking begins on an existing
save, `partial` is present and true. In that case the
coordinates prove where TGSRR tracking began, not where the character originally
spawned.

Across projection schema 2, all partial-history flags are presence-only:
omission means false, and the mod emits the field only when true. Sparse
outpost, deliverable, town, and landmark lists work the same way against their
declared versioned registries. Omission means the catalogue-defined default,
not unknown evidence.

## Separate states

- **Challenge mode** identifies the selected Project Zomboid challenge variant.
- **Submission status** is Received, Approved, or Declined.
- **Run verification** records whether any submission has established a verified
  canonical snapshot.
- **Run eligibility** will be an organiser-owned decision; the mod does not
  classify it.
- **Lifecycle** is Active, Deceased, Abandoned, Completed, or Invalidated.

## Terminal death evidence

A death export sets `lifecycle` to `deceased` and supplies matching terminal
projection evidence:

```json
{
  "lifecycle": "deceased",
  "endedReason": "deceased",
  "endedUtc": 1784800003,
  "endedWorldAgeHours": 123.5,
  "endedEventSequence": 42
}
```

The signed ledger contains exactly one `run.ended` event at that sequence, UTC
and world age, with `payload.reason` set to `deceased`. The website rejects
duplicate or mismatched terminal evidence. Approval automatically changes an
Active run to Deceased. A later non-terminal export does not reverse an existing
terminal lifecycle.
