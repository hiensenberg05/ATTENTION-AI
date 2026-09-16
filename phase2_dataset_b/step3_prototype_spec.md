# Step 3 Prototype Specification — Evidence-Based, No Winner Selected

Built entirely from already-completed Phase 2 outputs (`phase2_summary.md`,
`automation_candidates.csv`, `visual_audit.md`, `segment_features.csv`,
`representative_segments.csv`) plus one direct re-read of the raw Dataset B event sequence for
the two segments named below, to pin down the exact action-by-action flow. No change to Phase
1F.5, segmentation, or any existing Phase 2 output. No LLM/ML introduced — this is a specification
document, not new analysis code.

**This document does not choose or recommend a winner.** It lays out both visually-confirmed
clean workflows on the same 17-point template so a choice can be made from it.

---

## Why these two, and not a longer/higher-volume segment

`visual_audit.md` directly confirmed only two segments, out of 13 inspected, as genuine
single-record, single-action executions with no merged activity — every other inspected segment
in the same process families was a multi-case work session (up to ~15 distinct actions merged
into one reported segment; see `visual_audit.md` §"Conclusions," point 2). A prototype built
against a merged segment would be automating an ill-defined, multi-step, multi-system session, not
one workflow. These two are therefore the only members of `automation_candidates.csv`'s two
largest process families with directly-verified, unambiguous scope.

---

## Workflow A — Payroll Expense/Change Confirmation

| | |
|---|---|
| **1. Process/workflow name** | Payroll line-item expense confirmation (HR payroll-items queue) |
| **2. Representative segment ID(s)** | `ses_20260701-190250-NEELA9BAF::seg002` |
| **3. Business objective** | Review one pending payroll/expense line item against policy and confirm/register it so it leaves the "unprocessed" queue |
| **4. Input** | One pending record in the `経費精算・給与変更` (expense settlement / salary change) queue of `HR人事給与システム`, port 5132 — in this instance record `P1-07046967-001`, employee `E2011` (清水祥平), category `研修費` (training expense), amount `¥25,213`, status `未処理` (unprocessed) |
| **5. Trigger/start state** | Worker is already on (or navigates to) the payroll-items list at `127.0.0.1:5132/#/payroll-items`; segment starts mid-navigation (event 232, `browser_navigation` from a different tab at port 5133) — i.e., this is one record processed as part of a worker's queue-clearing routine, not a freshly-opened session |
| **6. Exact human action sequence** (event-index-referenced, from `outputs/tables/dataset_b_events.parquet` directly) | `[229-230]` click on prior page (tail of previous record) → `[232]` browser navigates to the 5132 payroll-items list → `[233-235]` screenshot/app-switch (list renders) → `[236-237]` click into a specific row → `[239]` scroll down to the detail panel → `[240]` **detail panel visible** (screenshot-confirmed: record ID, employee, category, amount, status, comment box, 登録確定/保留 buttons) → `[241-242]` **click 登録確定 (confirm/register)** → `[244-247]` clipboard/shortcut/2 keystrokes (likely a short comment entered) → `[249]` form field commits → `[250-251]` click into the next row (tail, next record beginning) |
| **7. Fields/data the employee reads or enters** | Reads: 管理ID (record ID), 社員ID (employee ID), 区分 (category), 金額 (amount), ステータス (status), a reference note ("申請者区分：regular　承認権限：部門長" — visible in the UI screenshot, i.e. the applicable approval-authority rule). Enters: an optional free-text 処理コメント (processing comment) before confirming |
| **8. Policy/validation/decision step** | Implicit — the worker checks amount/category "規程内であることを確認した" (confirmed within regulations) before clicking confirm; the actual policy text (e.g. a training-expense cap) is not shown on this screen, only a reference note about approval authority. No branching observed in this instance (no reject path exercised) |
| **9. Final action/output** | Click `登録確定`; record status transitions from 未処理 → processed (an alternate `保留`/hold button exists but was not used here) |
| **10. Applications/browser route involved** | Single app: Microsoft Edge, `127.0.0.1:5132/#/payroll-items` (segment briefly touches `5133/#/payroll-items` at its very start — same route type, different system instance, consistent with `phase2_summary.md`'s finding that the same route recurs at multiple ports) |
| **11. Manual baseline metrics (this instance)** | 11.7s duration, 24 raw events, 4 clicks + 4 browser_clicks, 2 keystrokes, 1 scroll, 1 form input, 1 navigation — `total_interaction_events`=14 (`segment_features.csv`) |
| **11b. Manual baseline (family-level, `automation_candidates.csv`, `B-127.0.0.1_5132_payroll-items`)** | 39 executions observed, 30.2 observed minutes total, **median 28.8s** and **median 18 clicks / 10 keystrokes** per execution — notably higher than this clean instance, because the family median is pulled up by the merged multi-case segments `visual_audit.md` found (§1); this specific clean example is toward the fast end of the distribution, not representative of the median |
| **12. What can plausibly be automated** | Opening the correct pending record, extracting the displayed fields (category, amount, employee), and — if the policy rule is made explicit and simple (e.g. a fixed cap per category) — the confirm click itself. Candidate for a "read the queue, apply the rule, act" bot |
| **13. What must stay human-in-the-loop** | Any record where the applicable policy isn't a simple threshold check (the UI reference note shows approval authority already varies by requester type — `regular` vs presumably others — implying the real policy has branches not fully visible in one screenshot); anomalous amounts; the `保留` (hold) path, whose trigger condition was never observed in this sample |
| **14. Known exceptions/risks** | (a) The policy logic behind "規程内であることを確認した" is not fully captured in the logs — automating the *decision*, not just the *data entry*, requires the actual written policy, not inferred from one example. (b) `case_id_presence_fraction` for this family is only 23% (`automation_candidates.csv`) — most executions have no OCR'd text confirming what was actually done, so this one example cannot be assumed representative of every payroll-items execution. (c) The regex-matched case IDs attached to this very segment (`INV-2026-7998`...`INV-2026-8009`, `segment_features.csv`) are list-view noise from the dashboard table, **not** the actual record processed (`P1-07046967-001`) — automation built on regex-extracted case IDs alone would target the wrong identifier scheme; the real key is the `管理ID`/`社員ID` pair visible only in the detail panel. |
| **15. Success criteria for a prototype** | Correctly identifies the pending record, correctly extracts category/amount/employee, and either auto-confirms records matching an explicit, human-provided policy rule or correctly routes ambiguous ones to a human, with zero incorrect confirmations |
| **16. Metrics to compare before vs after** | Time per record (baseline: 11.7s clean case, up to 28.8s family median); clicks per record (baseline 4-18); % of queue clearable without human review under the stated policy; error rate (wrong confirm/hold decisions) |
| **17. Evidence strength and limitations** | **Strength**: directly screenshot-confirmed, single record, single clear action, exact event sequence reconstructed. **Limitation**: one instance out of 39 in this family; the specific policy rule is inferred, not read from a rules screen; extracted-text coverage for this family is under 25% for case-ID content, so most of the family's true behavior is not directly observable, only this one example and the two/three other partially-inspected examples in `visual_audit.md` §1 |

---

## Workflow B — Leave/Attendance Application Approval

| | |
|---|---|
| **1. Process/workflow name** | Leave/attendance application approval (HR leave-applications queue) |
| **2. Representative segment ID(s)** | `ses_20260701-180923-NEELA9BAF::seg013` |
| **3. Business objective** | Review one pending leave/attendance request and approve or reject it |
| **4. Input** | One pending record in the `勤怠・休暇申請` (attendance/leave application) queue, port 5132 — in this instance record `P2-07048822-006`, employee `E2001` (青木拓也), request type `代休申請` (compensatory day off), date `2026-07-13`, status `申請中` (pending) |
| **5. Trigger/start state** | Worker is on the leave-applications list at `127.0.0.1:5132/#/leave-applications`; segment starts with a direct click into a row (no navigation event, unlike Workflow A) — i.e., this looks like a mid-queue record within an ongoing review session |
| **6. Exact human action sequence** | `[1200-1201]` click into a specific row → `[1203-1204]` scroll down to the detail panel → `[1205]` **detail panel visible** (screenshot-confirmed: record ID, employee, request type, date, department, status, comment box, 承認/差戻し buttons) → `[1206-1207]` **click 承認 (approve)** → `[1208-1211]` clipboard/shortcut/2 keystrokes (likely a short comment entered) → `[1213]` form field commits → `[1214-1215]` click into the next row (tail, next record beginning) |
| **7. Fields/data the employee reads or enters** | Reads: 管理ID, 社員ID, 申請種別 (request type), 期間 (date/period), 所属部署 (department), ステータス, a reference note ("事前承認要否：要" — prior-approval-required flag, visible in the screenshot). Enters: an optional 承認コメント (approval comment) or a rejection reason before submitting |
| **8. Policy/validation/decision step** | The reference note flags whether prior approval is required ("要" = yes, here); the worker's implied check is whether that requirement is satisfied before approving. No reject path exercised in this instance either |
| **9. Final action/output** | Click `承認`; status transitions from 申請中 → approved (an alternate `差戻し`/reject-and-return button exists but was not used here) |
| **10. Applications/browser route involved** | Single app: Microsoft Edge, `127.0.0.1:5132/#/leave-applications` only — no port/tab switching observed in this instance, simpler than Workflow A |
| **11. Manual baseline metrics (this instance)** | 4.4s duration, 17 raw events, 3 clicks + 3 browser_clicks, 2 keystrokes, 2 scrolls, 1 form input, 0 navigation — `total_interaction_events`=12 (`segment_features.csv`) |
| **11b. Manual baseline (family-level, `automation_candidates.csv`, `B-127.0.0.1_5132_leave-applications`)** | 23 executions observed, 18.6 observed minutes total, **median 40.8s** and **median 19 clicks / 6 keystrokes** per execution — again considerably higher than this clean instance for the same reason as Workflow A (family median pulled up by merged segments; see `visual_audit.md` §3, where the longest inspected example in this family contained an invoicing task plus two leave approvals plus a contract review in one segment) |
| **12. What can plausibly be automated** | Opening the correct pending record, extracting request type/date/department, and checking the explicit "prior approval required" flag already shown on-screen — a more mechanical, rules-visible check than Workflow A's implicit policy note |
| **13. What must stay human-in-the-loop** | Requests genuinely requiring "prior approval" judgment (the flag says approval is *required*, not what the outcome should be); any request type not seen in this sample (only `代休申請` observed directly here, though `visual_audit.md` §3 also directly confirmed `半日有給申請` and `フレックス変更申請` approvals elsewhere in the family); the `差戻し` (reject) path, never observed |
| **14. Known exceptions/risks** | (a) Only one request *type* (代休申請) is used as the detailed example here, though the family clearly includes others (paid leave, flex-time — confirmed in `visual_audit.md`'s `SIDDHIGUPTAB00B::181913::seg002` inspection) with potentially different validation rules per type. (b) `case_id_presence_fraction` for this family is 22%, and this specific clean segment has `case_id_count=0` — meaning the case-ID signal that exists for other families is essentially absent here; automation would need to key off the `管理ID`/`社員ID` fields visible only in the detail panel, same as Workflow A. (c) No reject (`差戻し`) example was captured anywhere in the audit, so the rejection path and its criteria are completely unobserved. |
| **15. Success criteria for a prototype** | Correctly identifies the pending record, correctly extracts request type/date/department/approval-required flag, and either auto-approves requests matching an explicit policy or correctly routes ambiguous/approval-required ones to a human, with zero incorrect approvals |
| **16. Metrics to compare before vs after** | Time per record (baseline: 4.4s clean case, up to 40.8s family median); clicks per record (baseline 3-19); % of queue auto-approvable under the stated policy; error rate |
| **17. Evidence strength and limitations** | **Strength**: directly screenshot-confirmed, single record, single clear action, exact event sequence reconstructed, and — unlike Workflow A — at least two other request *types* within the same family independently confirmed as genuine leave approvals elsewhere in `visual_audit.md`, giving slightly broader (though still partial) support. **Limitation**: reject path entirely unobserved; only one of at least three known request types has a full detail-panel walkthrough; family-level extracted-text coverage is still under 25% for case-ID content specifically, and 26.1% of the family's executions have no extracted text at all |

---

## Side-by-side comparison (no winner declared)

| | Workflow A: payroll expense confirmation | Workflow B: leave application approval |
|---|---|---|
| Confirmed clean instance duration | 11.7s | 4.4s (shortest of any inspected segment) |
| Confirmed clean instance events / interactions | 24 events / 14 interactions | 17 events / 12 interactions |
| Family size (`automation_candidates.csv`) | 39 executions, 30.2 observed min | 23 executions, 18.6 observed min |
| Family median duration / clicks / keystrokes | 28.8s / 18 / 10 | 40.8s / 19 / 6 |
| Apps/routes touched in the clean instance | 2 (brief 5133 tail + 5132) | 1 (5132 only) |
| Decision complexity (from the one confirmed instance) | Implicit policy note ("regular / department-head approval authority"), amount+category-based | Explicit binary flag shown on screen ("prior approval required: yes"), simpler surface but unresolved *what to do* with that flag |
| Breadth of confirmed request/record variety | 1 category type shown in detail (研修費); family confidence is High per `automation_candidates.csv` but based on aggregate evidence, not multiple detailed walkthroughs | 1 type detailed here (代休申請) + 2 more types independently confirmed elsewhere in `visual_audit.md` (半日有給申請, フレックス変更申請) — broader direct evidence of the family's real variety |
| Reject/hold path observed | No (保留 button exists, unused) | No (差戻し button exists, unused) |
| Case-ID/content evidence quality (family-level) | 23.1% case-ID presence, 82.1% extracted-text presence | 21.7% case-ID presence, 73.9% extracted-text presence |
| Known data caveat specific to this example | Regex-matched case IDs on this exact segment are list-view noise, not the real record key | None specific beyond the family-level caveats |

Both are the same underlying pattern (open one queued record → read fields against a
visible policy note → click one decision button → optional comment), on the same platform
(Microsoft Edge, HR system, port 5132), with the same core limitations (small number of directly
confirmed instances, no reject path observed, real per-category/per-type policy rules not fully
captured in the logs). Workflow B's clean instance is faster and simpler (single system, no
navigation), and has slightly broader confirmed variety across request types; Workflow A's family
is larger by both execution count and total observed time. Neither difference is decisive on its
own — this table is the input to that decision, not the decision itself.
