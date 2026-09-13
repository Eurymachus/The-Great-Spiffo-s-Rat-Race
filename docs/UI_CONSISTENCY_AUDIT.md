# Website interface consistency audit

12 September 2026. Local development workspace, including the uncommitted search, filter and participant-tab changes.

## Scope and evidence

This is a layout and component audit, not a redesign or functional approval. No application styling was changed during this audit.

- Inventoried all 41 registered admin model entries and their configured list/detail templates.
- Reviewed the structure of the repository's full-page template families, shared templates and relevant CSS/JavaScript. The appendices identify the actual entry points, including inherited Django pages.
- Measured 17 representative page types in the signed-in local browser: Page editor, Challenge Runs list/detail, Participants list/detail, account dashboard, public run, public profile, run submission, approved submission review, navigation editor, operation job list, image library, Challenge Modes list, admin notifications and account settings/leaderboard.
- Measurements are CSS pixels in the current desktop theme. The screenshots supplied in the conversation can appear larger because of display scaling.
- Tables below distinguish browser-measured pages (B) from template/CSS-reviewed families (S). S is not a claim that every state was opened in a browser.
- Signed-out, narrow-screen, light-theme, empty/error/permission variants and live provider dialogs were source-reviewed where present, but not exhaustively exercised. No approvals, edits, deletes, uploads or provider actions were submitted.

## Overall finding

The visible differences are caused by multiple component systems within the same admin, not simply one wrong button size. Standard Django object tools, custom run-review controls, editor controls and the recently added shared toolbar each set their own dimensions. Some differences are appropriate, especially between compact admin tables and participant-facing touch controls. Identical admin actions such as History and Close should not change shape or size by page.

The latest toolbar changes contribute to the problem: `admin_list_toolbar.css` now contains successive overrides for earlier layouts rather than one final definition. The cascade is doing the work that a shared component contract should do. Further isolated tweaks will continue to cause drift.

## Measured comparison

| Page/control | Height | Text | Shape / implication |
|---|---:|---:|---|
| Standard admin History / View on site / Add | 26px | 11px | 15px radius, uppercase presentation; much smaller than run equivalents |
| Run detail History | 44px | 14px | 32px radius; same action has a different scale |
| Run detail Set status | 44px | 14px | 4px radius; different from its adjacent History |
| Shared list Search / Filters / Reset | 30px | 13px | 4px radius; these controls are now aligned |
| Challenge Runs row Open run | 44px | 13px | Large compared with adjacent table content and 30px toolbar |
| Page editor Add section / Add block | 36px | 13px | Split button, 4px outside corners |
| Page editor Save / Delete | 35px | 13px / 14px | Equal height, unequal typography |
| Page editor and Participant detail Close | 37px | 13.33px | Browser button font leaks into the shared footer |
| Approved review Close / Submit audit | 37px | 13.33px / 13px | Same height, different font rules |
| Navigation editor Close / Save | 41px / 35px | 14px / 13.33px | Largest directly measured mismatch inside one footer |
| Public dashboard/profile/run header actions | 44px | 16px | 7.2px radius in current theme; consistent within this family |

Heading comparison: standard admin page titles are 20px/300, but the record name is a subordinate 16px/700 heading. Run records use the record name as the 20px/300 primary heading within a framed banner. Public account/profile/run headings measured 26.4px/600; leaderboard uses 24px/700.

## Findings and priorities

### 1. Admin record headers do not follow one hierarchy (high)

Participant edit and Page editor show a generic action heading first (Change participant / Change page), then the record name, then separate pill object tools. Challenge Run and Submission Review suppress that inherited heading and put record identity, context, status and actions into a single banner. Workshop mod and legacy review templates add their own hero content without using the same header contract.

Recommendation: one admin record-header component with record type, record name, optional metadata/statuses and a consistent action group. Page editor's title should be the page name; participant detail's title should be the participant name. Keep a plain list heading for collections. Avoid using a generic Change heading as the most prominent identity.

### 2. Footer controls are inconsistent even within the same footer (high)

Most add/change forms share a fixed Save/Close footer, but dimensions come from a combination of native input styles, anchor styles and injected button styles. Navigation editor builds another fixed footer. Review screens substitute their own decision actions. Custom operational forms use `.submit-row` without necessarily receiving the `body.change-form` selectors that make it fixed.

Recommendation: a shared action-bar layout and explicit control classes for button, anchor and submit input. Close left, task actions right; one standard action size. Only editable/review workflows need a persistent action bar. Read-only pages can use header Back/History without an empty footer.

### 3. Search and filter appearance is closer than the behaviour (high)

Challenge Runs updates results asynchronously after a 180ms debounce, preserves the picker, serializes requests and reports progress through a toast. Standard lists navigate the whole page after 800ms, restoring picker scroll/open state. Date/custom filter groups remain single-choice despite being drawn as checkboxes, while exact-field filters can be multi-select.

The shared toolbar builder only runs when `#changelist-filter` exists. Search-only pages therefore retain the original toolbar markup. No-search/no-filter lists have no toolbar, which is reasonable, but spacing should still follow a common list layout.

Recommendation: share toolbar markup, filter group semantics, selection state and feedback. Explicitly distinguish single-choice groups from additive groups. Keep the selected-filter count and overlay stable. Reset filters versus Reset view may remain different labels only if their different behaviour is intentional and understandable.

### 4. Table density and row actions are different (medium)

Challenge Runs uses padded custom table headings (12px 16px) and explicit 44px row action buttons. Standard admin table heading cells measured zero direct padding because their linked headings carry the spacing. Review ledgers use another density (11.2px 13.6px heading padding). Participants still has the standard admin action checkbox column, multi-column sort controls and a bulk-action bar, even though its tabs now look like Challenge Runs.

Recommendation: define a shared admin table density, sortable heading style, status treatment, date format, empty state and compact row-action size. Retain selection checkboxes only where batch actions exist. Do not force the public leaderboard's card/grid layout into an admin table.

### 5. Same-purpose controls use incompatible button families (medium)

History is both a 26px uppercase pill and a 44px sentence-case pill. Close ranges from 35-41px depending on markup. Editor controls are 36px, toolbar controls 30px, run header actions 44px. Different sizes are useful; having no assigned roles for them is the issue.

Recommendation: define compact (30px, dense lists), standard (36px, editor/header/footer) and comfortable (44px, public/touch) sizes. Apply a consistent radius and typography within each role. Keep status badges visually distinct from clickable actions. Red Reset was explicitly requested earlier; this audit is not reversing that choice, but reversible reset and permanent deletion should remain clearly labelled.

### 6. Tabs share appearance but not a single implementation (medium)

Challenge Runs and Participants have matching saved tabs but separate view models, preference code and template/dialog wiring. Other lists have no saved views. Run-local Overview/Submissions/Audits tabs are navigation within a record, while public notifications and managed content tabs are different navigation/filter concepts.

Recommendation: share saved-view presentation and behaviour without conflating it with record-local navigation. Keep tabs attached to their results. Do not add saved views to every form or tree editor merely for consistency.

### 7. Public pages are mostly coherent, with a few local differences (medium/low)

Account, profile, settings and public run pages share the public shell, footer and comfortable header actions. Leaderboard's heading differs in size/weight; Notifications hides Dashboard in an overflow menu whereas Settings and submission pages expose it. Auth and confirmation pages use simpler cards and inline actions. These are not all defects, but navigation terminology and action priority need a deliberate rule.

Recommendation: preserve the public design family. Align page-heading hierarchy and Back/Dashboard placement where the journey is equivalent. Keep data-heavy public run cards and leaderboard progress rows purpose-specific.

### 8. Feedback, dialogs and exceptional states need the same component treatment (medium)

Admin save and run-filter feedback now share toast styling, but their lifecycle code is separate. Standard filtering still reloads the page. Review dialogs, saved-view dialogs, editor menus, Close confirmation, media tools and public provider dialogs have separate sizing and Close controls. Run history combines a custom moderation-history panel with inherited admin history. Invalid export, empty list and unavailable comparison states are not interchangeable and should retain accurate wording while sharing spacing and typography.

Recommendation: a shared modal header/actions/close pattern and toast API, plus explicit empty, unavailable, loading and error presentations. Do not overwrite integrity errors with generic empty-state copy.

## Page-family comparison

B = browser measured; S = source reviewed. Standard forms inherit the fixed admin footer unless a template explicitly replaces it. Standard lists use pagination/optional list-editable Save, not a record-edit action footer.

### Admin pages

| Distinct entry family | Evidence | Header / footer | Search, actions and columns | Assessment |
|---|---|---|---|---|
| Admin home and app index | S | Admin shell; dashboard modules; no record footer | Navigation/module tables | Intentional dashboard family; share outer spacing only |
| Participants list | B | Generic Select participant heading; new attached tabs | Shared search/filter overlay; batch action bar; standard columns | Tabs are aligned conceptually, title/table density still differ from runs |
| Participant account record, add, password edit | B/S | Generic Change participant plus nickname; 26px History; fixed Save/Close | Aligned fieldsets, avatar moderation links | Strong candidate for shared record header; normalize footer |
| Challenge Runs list | B | Plain Challenge Runs title; tabs at table | Custom async filters, toast, padded columns, large Open actions | Closest current list reference, but row actions oversized for compact mode |
| Challenge Run record: Overview/Submissions/Audits | B/S | Framed identity/status banner; 44px actions; local tabs | Summary cards, event/submission/audit tables; status dialog | Good semantic hierarchy; normalize action shapes and table rules |
| Submission review: pending/approved/declined/invalid | B/S | Custom record hero; fixed review footer; state-specific actions | Findings, baseline comparisons, evidence, ledger; audit/decline/evidence dialogs | Preserve state-specific content; unify dialog/footer control sizes |
| Submission/audit compatibility queues | S | Custom or inherited queue shells, with redirects in some entry points | Older queue and run-queue templates remain in the repository | Check reachability before restyling; do not create a second moderation workspace |
| Run history | S | Custom moderation panel plus inherited admin history | Date/actor/action/reason table | Hybrid header and table family; use shared history layout |
| Standard object history/delete confirmation | S | Inherited Django heading and content | History table or confirmation form | Must be included in component rollout, not only main detail pages |
| Challenge Modes list/detail | B/S | Standard heading/object tools; standard detail footer | Search-only list; inline editable booleans | Search-only frame is useful reference; ensure inline Save has an intentional placement |
| Admin notifications list/detail | B/S | Generic heading; standard detail footer | Shared filters, standard action/column layout | Same list family as Participants without saved tabs |
| Other standard registry records | S | Standard admin headings, object tools and footers | Per-model filters/search and columns | Inherit the same inconsistencies; see full model inventory |
| Workshop mod list/review | S | Standard outer heading plus custom mod hero/voting panels | Request, policy, vote/rationale controls and standard edit fields | Hybrid page; voting actions and record Save need clear hierarchy |
| Legacy run record/list | S | Standard admin | Standard columns/fields | Normalize through base components |
| Legacy submission and claim review | S | Claim-style hero plus inherited outer shell; custom decision footer | Review summaries, approval/decline dialog | Similar workflow to current reviews but separate presentation |
| Legacy import list/upload/preview | S | Standard list; custom upload heading; preview within change form | Upload/validate/confirm controls and preview table | Upload operation footer differs from record-edit footer |
| Page list and page editor | B/S | Generic Change page plus name; pill History/View on site; fixed footer | 36px split Add section/block controls, editor cards | Direct example of header/action drift; editor structure itself is intentional |
| Code-managed page list/detail | S | Standard form with restricted save template | Informational configuration | Read-only capability should drive footer, not stylistic imitation of editor |
| Navigation list/tree and item form | B/S | Generic list heading plus Navigation structure; custom fixed footer | Drag tree replaces table; 41px Close versus 35px Save | Keep tree layout; fix footer mismatch and redundant heading hierarchy |
| Branding settings | S | Standard record shell with custom image section | Branding/image selectors; standard Save | Normalize header/footer; preserve specialized inputs |
| Theme editor | S | Standard shell with Typography and shape section | Theme controls; standard Save | Same normalization target as Branding |
| Image library list/detail/manager | B/S | Standard list title; Upload images button instead of ordinary Add | Image-oriented columns and injected manager UI | Custom upload entry needs same action hierarchy; dialog states still need visual QA |
| Website settings | S | Standard admin form | Configuration fieldsets | Inherits baseline admin inconsistencies |
| Groups and permissions | S | Standard Django admin | Selectors and generic list/detail controls | Preserve permission workflow; normalize shell/control styles |
| Catalogue entries, aliases and typed detail records | S | Standard admin | Dense model-specific columns and search | Shared table density and column wrapping are preferable to individual restyles |
| Reference source/job/artwork lists and details | B/S | Standard outer shell with operations enhancements | Status/progress and job columns; details/forms | Job state is read-only data, not a reason for oversized buttons |
| Catalogue import review list/detail | S | Operations list; review-specific footer action | Import decisions and data fields | Match review action hierarchy, preserve operation meaning |
| Check update/decompile/catalogue dry run/artwork sync | S | Custom base-site operation forms | Source/config fields with submit rows | Fixed-footer rules may not apply without change-form body class |
| Steam authentication/approval waiting | S | Custom operation form | Inline waiting/error feedback, Cancel/submit | Keep credential workflow separate; normalize form action layout only |
| Run data danger zone | S | Dedicated heading/cards and warnings | Reset versus purge workflows | Deliberate stronger treatment; should retain distinct risk hierarchy |
| Account closure confirmation | S | Custom confirmation heading | Confirmation action and cancel link | Shared confirmation layout; preserve destructive copy |
| Admin login/logout/password flows | S | Framework account templates and shared branding | Authentication forms | Separate form family; need same focus/error/submit conventions |

### Participant-facing pages

| Distinct entry family | Evidence | Header / footer | Search, actions and columns | Assessment |
|---|---|---|---|---|
| Home | S | Public shell and promotional heading; site footer | Primary/secondary calls to action | Intentional landing-page family |
| Managed pages: Hall of Fame, rules and other editorial routes | S | Shared shell; headings controlled by sections/blocks; site footer | Managed tabs/cards/ranking blocks | Audit section hierarchy, not each content record as a new UI system |
| Participant account dashboard | B | Welcome hero, avatar, 44px actions; site footer | Run cards/progress, account summaries | Coherent public reference |
| Participant public profile | B | Nickname hero and return action; site footer | Public run cards | Aligns with dashboard; public/private data differences are intentional |
| Public run detail | B | Character hero, Back action; local run footer plus site footer | Progress cards, skills/outposts/build/map dialogs | Coherent public family; detail dialogs are secondary component audit targets |
| Account settings | B | Account identity hero and Dashboard action | Settings rows, provider controls, avatar dialog | Same shell; provider action styles are a separate subfamily |
| Submit run | B | Submission header and Dashboard action; inline form actions | Export/evidence/provider selection and validation states | Keep step workflow; align secondary controls and feedback |
| Submit legacy update / update evidence | S | Same submission family | Different fields/provider choices | Should inherit one submission-step component |
| Leaderboard | B | 24px bold hero versus 26.4px semibold account hero; site footer | Ordered ranking grid, progress columns and drill-ins | Small heading drift; grid is an intentional public data view |
| Mods catalogue | S | Mods hero and public footer | Catalogue filters/cards, rules and submit dialogs | Purpose-specific cards; align header/secondary action rules |
| Exploits and edge cases | S | Policy hero and footer | Category tabs and ruling panels | Content tabs differ legitimately from saved admin views |
| Notifications | S | Compact heading and overflow actions; footer | All/Unread tabs, dated cards, pagination | Dashboard location differs from other account pages |
| Login/signup | S | Simple public card; footer | Form controls, validation, alternate actions | Intentionally simpler; consistent button/error conventions needed |
| Thanks/resend/verification outcomes | S | Outcome card and footer | Inline follow-up actions; expired/invalid variants | Shared status/result component opportunity |
| Password change/reset/request/confirm/complete | S | Form/outcome cards; footer | Inline submits and follow-ups | Keep authentication family consistent, including invalid-link states |
| Account closure/request received | S | Closure/outcome cards; footer | Destructive workflow with follow-up | Preserve consequence-specific hierarchy |
| Privacy/development disclosure and dialogs | S | Policy content and public footer or modal header | Long-form text, Close control | Same content in page and dialog; unify dialog chrome |
| Maintenance | S | Standalone fallback document | Availability message | Intentionally independent; branding and readable spacing should be checked separately |

## Recommended implementation sequence

1. Establish shared admin record-header and action-bar components first. Apply them to Participant detail, Page editor and run detail/review as the reference set. These are the most visible inconsistencies in the supplied screenshots.
2. Consolidate the toolbar CSS overrides into one definition and share the search/filter behaviour. Standardize the table density, row actions and selected-filter overlay.
3. Apply the same contracts to editor, operation, legacy and catalogue families, including confirmation/history pages.
4. Then do a focused public-page pass for heading hierarchy, journey actions, dialogs and result states. Preserve public 44px controls rather than shrinking them to admin density.

Before accepting a rollout, compare reference pages at the same viewport/theme with populated, empty, loading, error and disabled states; check long names, wrapping, keyboard focus and fixed-footer overlap. This audit does not claim those checks have already passed.

## Source references

- Admin shell and object tools: `apps/website/templates/admin/base_site.html`, `change_form_object_tools.html`, `submit_line.html`.
- Shared toolbar: `apps/website/registry/static/registry/admin_list_toolbar.css` and `.js`.
- Admin footer, Close and save toast: `registry/static/registry/admin.css`, `admin_close.js`, `admin_save.js`.
- Run headers/tables/tabs: `registry/static/registry/admin_run_review.css` and `registry/templates/admin/registry/challengerun/`, `runsubmission/`.
- Page/navigation editors: `apps/website/pages/templates/admin/pages/` and `pages/static/pages/`.
- Public shell and controls: `registry/templates/registry/base.html`, page-family templates, `registry/static/registry/site.css`.

## Appendix A: complete registered admin model inventory

Every entry below was inspected through its registered ModelAdmin configuration. A default template is an inherited family, not a separately hand-built page. Runtime view overrides can redirect legacy queues or singleton pages; the source-family table above records those distinctions.

| Model | List template | Detail template | Search / filters |
|---|---|---|---|
| auth.Group | `admin/change_list.html` | `admin/change_form.html` | Search; 0 filter groups |
| administration.WebsiteSettings | `admin/change_list.html` | `admin/change_form.html` | No search; 0 filter groups |
| branding.WebsiteTheme | `admin/change_list.html` | `admin/branding/websitetheme/change_form.html` | Search; 3 filter groups |
| branding.SiteBranding | `admin/change_list.html` | `admin/branding/sitebranding/change_form.html` | No search; 0 filter groups |
| branding.ManagedImage | `admin/branding/managedimage/change_list.html` | `admin/change_form.html` | Search; 0 filter groups |
| pages.CodeManagedPage | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| pages.Page | `admin/change_list.html` | `admin/pages/page/change_form.html` | Search; 2 filter groups |
| pages.NavigationItem | `admin/pages/navigationitem/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| registry.ExploitRuling | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| registry.LegacyRun | `admin/change_list.html` | `admin/change_form.html` | Search; 1 filter groups |
| registry.LegacyRunSubmission | `admin/change_list.html` | `admin/registry/legacyrunsubmission/change_form.html` | Search; 2 filter groups |
| registry.LegacyRunClaim | `admin/change_list.html` | `admin/registry/legacyrunclaim/change_form.html` | Search; 1 filter groups |
| registry.LegacyDataImport | `admin/registry/legacydataimport/change_list.html` | `admin/registry/legacydataimport/change_form.html` | No search; 1 filter groups |
| registry.WorkshopMod | `admin/registry/workshopmod/change_list.html` | `admin/registry/workshopmod/change_form.html` | Search; 3 filter groups |
| registry.Participant | `admin/registry/participant/change_list.html` | `admin/change_form.html` | Search; 4 filter groups |
| registry.AccountClosureRecord | `admin/change_list.html` | `admin/change_form.html` | No search; 0 filter groups |
| registry.Notification | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| registry.StreamingAccount | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| registry.StreamingMedia | `admin/change_list.html` | `admin/change_form.html` | Search; 4 filter groups |
| registry.ChallengeMode | `admin/change_list.html` | `admin/change_form.html` | Search; 0 filter groups |
| registry.ParticipantChallengeModeLimit | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| registry.ChallengeRun | `admin/registry/challengerun/change_list.html` | `admin/registry/challengerun/change_form.html` | Search; 6 filter groups |
| registry.RunSubmission | `admin/change_list.html` | `admin/registry/runsubmission/change_form.html` | Search; 3 filter groups |
| registry.SubmissionAudit | `admin/registry/submissionaudit/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| zomboid_catalogue.CatalogueEntry | `admin/change_list.html` | `admin/change_form.html` | Search; 4 filter groups |
| zomboid_catalogue.CatalogueAlias | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| zomboid_catalogue.TraitDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| zomboid_catalogue.OccupationDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 0 filter groups |
| zomboid_catalogue.SkillDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| zomboid_catalogue.ItemDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| zomboid_catalogue.ItemDisplayCategory | `admin/change_list.html` | `admin/change_form.html` | Search; 0 filter groups |
| zomboid_catalogue.AnimalDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| zomboid_catalogue.DeliverableDetails | `admin/change_list.html` | `admin/change_form.html` | Search; 1 filter groups |
| zomboid_catalogue.MapLocationVersion | `admin/change_list.html` | `admin/change_form.html` | Search; 3 filter groups |
| zomboid_catalogue.MapLocationBuilding | `admin/change_list.html` | `admin/change_form.html` | Search; 2 filter groups |
| zomboid_catalogue.CatalogueAsset | `admin/change_list.html` | `admin/change_form.html` | Search; 5 filter groups |
| operations.RunDataDangerZone | `admin/operations/run_data_danger_zone.html` | `admin/change_form.html` | No search; 0 filter groups |
| operations.ReferenceSource | `admin/operations/change_list.html` | `admin/change_form.html` | No search; 0 filter groups |
| operations.ReferenceUpdateJob | `admin/operations/change_list.html` | `admin/change_form.html` | No search; 0 filter groups |
| operations.CatalogueImportReview | `admin/operations/catalogueimportreview/change_list.html` | `admin/operations/catalogueimportreview/change_form.html` | No search; 0 filter groups |
| operations.PZWikiArtworkSyncJob | `admin/operations/change_list.html` | `admin/change_form.html` | No search; 3 filter groups |

## Appendix B: full-page template inventory

Repository templates with an explicit parent are listed below. Shared partials (ledger rows, dialogs, navigation, content blocks and sections) were included in the relevant family rather than counted as separate routes. Framework defaults such as add/delete/history/authentication are covered in the family matrix above.

| Template | Parent |
|---|---|
| `apps/website/branding/templates/admin/branding/managedimage/change_list.html` | `admin/change_list.html` |
| `apps/website/branding/templates/admin/branding/sitebranding/change_form.html` | `admin/change_form.html` |
| `apps/website/branding/templates/admin/branding/websitetheme/change_form.html` | `admin/change_form.html` |
| `apps/website/operations/templates/admin/operations/catalogue_dry_run.html` | `admin/base_site.html` |
| `apps/website/operations/templates/admin/operations/catalogueimportreview/change_form.html` | `admin/change_form.html` |
| `apps/website/operations/templates/admin/operations/catalogueimportreview/change_list.html` | `admin/operations/change_list.html` |
| `apps/website/operations/templates/admin/operations/change_list.html` | `admin/change_list.html` |
| `apps/website/operations/templates/admin/operations/check_reference_update.html` | `admin/base_site.html` |
| `apps/website/operations/templates/admin/operations/decompile_reference.html` | `admin/base_site.html` |
| `apps/website/operations/templates/admin/operations/run_data_danger_zone.html` | `admin/base_site.html` |
| `apps/website/operations/templates/admin/operations/steam_auth.html` | `admin/base_site.html` |
| `apps/website/operations/templates/admin/operations/sync_pzwiki_artwork.html` | `admin/base_site.html` |
| `apps/website/pages/templates/admin/pages/navigationitem/change_list.html` | `admin/change_list.html` |
| `apps/website/pages/templates/admin/pages/page/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/rat_race_app_index.html` | `admin/app_index.html` |
| `apps/website/registry/templates/admin/rat_race_index.html` | `admin/index.html` |
| `apps/website/registry/templates/admin/registry/challengerun/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/challengerun/change_list.html` | `admin/base_site.html` |
| `apps/website/registry/templates/admin/registry/confirm_account_closure.html` | `admin/base_site.html` |
| `apps/website/registry/templates/admin/registry/legacydataimport/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/legacydataimport/change_list.html` | `admin/change_list.html` |
| `apps/website/registry/templates/admin/registry/legacydataimport/upload.html` | `admin/base_site.html` |
| `apps/website/registry/templates/admin/registry/legacyrunclaim/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/legacyrunsubmission/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/participant/change_list.html` | `admin/change_list.html` |
| `apps/website/registry/templates/admin/registry/run_history.html` | `admin/object_history.html` |
| `apps/website/registry/templates/admin/registry/runsubmission/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/runsubmission/change_list.html` | `admin/base_site.html` |
| `apps/website/registry/templates/admin/registry/runsubmission/run_queue.html` | `admin/base_site.html` |
| `apps/website/registry/templates/admin/registry/submissionaudit/change_list.html` | `admin/change_list.html` |
| `apps/website/registry/templates/admin/registry/workshopmod/change_form.html` | `admin/change_form.html` |
| `apps/website/registry/templates/admin/registry/workshopmod/change_list.html` | `admin/change_list.html` |
| `apps/website/registry/templates/registry/account.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/account_closure.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/account_closure_received.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/account_settings.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/development_disclosure.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/exploits.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/home.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/leaderboard.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/login.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/mods.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/notifications.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/page.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/participant_profile.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/password_change.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/password_change_done.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/password_reset_complete.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/password_reset_confirm.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/password_reset_request.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/privacy_notice.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/public_run_detail.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/register.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/resend_verification.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/submit_legacy_run.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/submit_run.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/thanks.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/update_run_submission_evidence.html` | `registry/base.html` |
| `apps/website/registry/templates/registry/verification_result.html` | `registry/base.html` |
| `apps/website/templates/admin/base_site.html` | `admin/base.html` |
| `apps/website/templates/admin/pages/codemanagedpage/change_form.html` | `admin/change_form.html` |
