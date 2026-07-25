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

## Separate states

- **Challenge mode** identifies the selected Project Zomboid challenge variant.
- **Submission status** is Received, Approved, or Declined.
- **Run verification** records whether any submission has established a verified
  canonical snapshot.
- **Run eligibility** will be an organiser-owned decision; the mod does not
  classify it.
- **Lifecycle** is Active, Deceased, Abandoned, Completed, or Invalidated.
