# Participant Data Retention Schedule

Approved by the project owner on 2026-07-15 for Sentinel Tech Ltd's operation
of The Great Spiffo's Rat Race challenge platform.

| Information | Retention | End-of-period action |
| --- | --- | --- |
| Unverified registrations | 30 days from registration | Delete the account and identifying data. |
| Active participant accounts | While the account and challenge platform remain active | Retain unless closure is approved or the platform ends. Do not delete merely for inactivity. |
| Closed participant identity | Until an approved closure is processed | Remove login credentials, email, nickname, and other identifying account information. |
| Anonymised challenge reports and results | Indefinitely | Remove the participant link, retain each run independently, and display its owner as Former Rat Racer only when genuinely anonymised. |
| Moderation notes and evidence | Two years after the relevant run, decision, or closure | Delete or anonymise, unless needed for an active dispute or legal obligation. |
| Routine security and email-delivery logs | 90 days | Delete, unless needed for an active investigation. |
| Backups | Rolling 30 days | Allow deleted personal information to expire and do not restore it to the live service. |
| Non-personal closure receipts | Indefinitely | Retain only the random reference and request/process timestamps. |

Sentinel Tech Ltd will review this schedule at least annually and whenever the
platform's purpose or data processing changes. Earlier deletion or anonymisation
may be appropriate when information is no longer needed.

## Implementation status

This document is the approved policy. Account-closure redaction and non-personal
closure receipts are implemented locally. The scheduled deletion of unverified
registrations, moderation records, logs, and expired backups must be implemented
and tested as the relevant production systems and data models are introduced.
