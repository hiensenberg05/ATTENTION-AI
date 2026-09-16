# Phase 2 Visual Audit — Dataset B (pre-Step 3 sanity check)

Targeted, manual inspection of actual screenshots + surrounding events for 13 representative
segments across the three highest-volume process candidates (`5132 payroll-items`,
`5132 onboarding`, `5132 leave-applications`), done before any Step 3 decision. No Phase 1F.5
change, no rerun of segmentation, no OCR/LLM pipeline — every screenshot below was opened and
read directly, and every text quote is copied from the raw `extracted_text` field or read off the
image. **No Step 3 winner is selected here.**

Segments were chosen to span the full duration range within each process type (shortest, several
mid-range, and the longest/most case-ID-dense), since §7 of `phase2_summary.md` had already flagged
duration as a proxy for how many real business actions might be merged into one reported segment.

Screenshot resolution: Dataset B has markedly better screenshot coverage than Dataset A — 3,860
actual `.jpg` files on disk against 4,759 referenced `screenshot_smart` events (~81%), so nearly
every inspected segment had real images available, not just OCR'd text.

## Headline finding (new, not in `phase2_summary.md` §7)

**The URL hash-route is not a reliable indicator of business function outside of what was
directly visually confirmed.** While inspecting a `5132 onboarding` segment that happened to
navigate into a second browser tab, a screenshot at event 414 (session
`ses_20260701-175258-LAPTOP-76QMG9DE`) showed a **Finance payment-reconciliation screen**
(window title "財務会計システム" — Finance Accounting System — showing a payments list with
invoice numbers, vendor names, amounts, and a "支払実行"/execute-payment button) while the raw
`browser_url` field for that exact event reads `http://127.0.0.1:5133/#/onboarding`. Checked the
raw event stream directly (not inferred) — confirmed byte-for-byte:

```
409  mouse_click     browser_url=http://127.0.0.1:5133/#/onboarding   window_title=財務会計システム...
...
414  screenshot_smart  (the payment-processing screenshot shown below)
```

Following up, **all 6 segments mechanically grouped as `5133_onboarding`** in
`process_summary.csv` were checked, and **none of them show HR onboarding content** — they show
IT equipment requests, payment confirmations (`支払処理確認`), contract management
(`契約管理処理`), and a Logistics/inventory dashboard. The `#/onboarding` route slug at port 5133
is evidently reused by that system for something else entirely (most likely a generic/misc.
operations tab in the Finance app, not a copy of the HR onboarding flow) — the same route name
does **not** mean the same business function across ports. This directly affects confidence in
any process-type row in `process_summary.csv` whose port is not 5132: **`5133_onboarding`'s
"employee onboarding workflow" description is wrong and should be treated as unverified/rare
misc. activity, not a real automation candidate, until manually re-checked.** The three families
the user asked to audit here are all at port 5132, and — see below — held up under direct visual
inspection; this finding is a bonus catch from that inspection, not a mark against 5132 itself.

---

## 1. `5132 payroll-items` — 5 segments inspected

| segment_id | duration | verdict |
|---|---:|---|
| `CHAITANYA0BCF::171614::seg009` | 4.4s | single, trivial (too short for text; likely a glance/misclick) |
| `NEELA9BAF::190250::seg002` | 11.7s | **single, clean, confirmed** |
| `CHAITANYA0BCF::171614::seg003` | 38.3s | **merged — 2 different systems** |
| `NEELA9BAF::173642::seg009` | 59.0s | **merged — 2 payroll cases** |
| `NEELA9BAF::190250::seg003` | 170.1s | **merged — 6+ distinct actions, 2 systems** |

### `NEELA9BAF::190250::seg002` (11.7s) — clean single execution, visually confirmed
Screenshot (event 240) shows `HR人事給与システム` at `127.0.0.1:5132/#/payroll-items`: a payroll
items list (`P4-07046967-xxx`) with a detail panel open for **`P1-07046967-001 · 清水祥平`**
(Shimizu Shohei), 区分=研修費 (training expense), 金額=25,213円, ステータス=未処理
(unprocessed), a comment box, and 登録確定 (confirm)/保留 (hold) buttons. `extracted_text[241]`:
*"経費精算確認済み。費目：研修費　金額：25,213円。規程内であることを確認した。"* ("Expense
settlement confirmed. Category: training expense. Amount: ¥25,213. Confirmed within regulations.")
**Input → processing → output**: open the specific pending record → review amount/category
against policy → confirm/register. One record, one action, one screen. This is the cleanest,
most automation-ready pattern found in the whole audit.

### `CHAITANYA0BCF::171614::seg003` (38.3s) — merged, two different business systems
Already flagged in `phase2_summary.md` §7. Confirmed again here: starts with a genuine payroll
change ("給与変更登録。変更種別：役職手当新設。...確認完了" — salary change registered, new
position allowance, confirmed) at port 5132, then **navigates to port 5134** mid-segment and
switches to inventory-adjustment text ("在庫調整登録。品番：BATCH-W2...") — an entirely different
business system (Logistics, not HR/Payroll). One reported segment, two unrelated case executions
in two different systems.

### `NEELA9BAF::173642::seg009` (59.0s) — merged, two payroll cases, same system
No port-switching this time, but the text shows **two separate salary-change registrations**:
*"給与変更登録。変更種別：残業手当調整。...確認完了。"* (overtime allowance adjustment) at event
786, then *"給与変更登録。変更種別：役職手当新設。...確認完了。"* (new position allowance) at
event 805 — two different employees' payroll changes, back to back, with dashboard re-checks in
between, reported as one segment.

### `NEELA9BAF::190250::seg003` (170.1s, 300 events) — merged, at least 6 distinct actions
The richest example. In order: HR dashboard → inventory adjustment memo (Notepad,
"在庫調整メモ...BATCH-W2...") → an expense-settlement memo referencing case `P1-07046967-002`
(¥24,395, transportation) → a second expense settlement (¥8,691, consumables) → HR dashboard
again → **Finance dashboard** → invoice reconciliation **INV-2026-8008, ¥588,515, "差異あり要確認"
(discrepancy found, needs review)** → invoice reconciliation **INV-2026-8009, ¥1,876,206,
"差異なし承認" (no discrepancy, approved)** → a policy document read in full
("業務委託経費規程" — outsourcing expense regulation) → more HR dashboard checks. This single
reported segment spans at least two invoice reconciliations (one flagged for review, one clean —
a meaningfully different outcome branch), two expense settlements, an inventory memo, and a
policy lookup, crossing between the HR and Finance dashboards repeatedly. **Not one execution —
a whole multi-task work session.**

---

## 2. `5132 onboarding` — 5 segments inspected

| segment_id | duration | verdict |
|---|---:|---|
| `LAPTOP-76QMG9DE::191537::seg002` | 2.1s | single, trivial (too short for text) |
| `NEELA9BAF::180923::seg006` | 45.2s | **ambiguous — dashboard/browsing only, no onboarding-specific action seen** |
| `SIDDHIGUPTAB00B::173246::seg004` | 210.5s | **merged — onboarding + procurement + contracts** |
| `CHAITANYA0BCF::171614::seg011` | 177.1s | **merged — onboarding + payments + payroll** |
| `LAPTOP-76QMG9DE::175258::seg004` | 358.8s | **merged — the largest single case found, crosses a chunk boundary** |

### `LAPTOP-76QMG9DE::175258::seg004` (358.8s / 712 events) — the extreme case
Confirmed visually. This segment **crosses a chunk boundary** (`chunk_...1730` →
`chunk_...1800`) and contains, in sequence: Windows Explorer file browsing (unrelated desktop
navigation) → an outsourcing-worker onboarding procedure document → the genuine HR onboarding
screen (screenshot confirmed: `入社手続き` list with candidates like 岩田明美, matching the label)
→ **six separate payment confirmations** (¥1,616,594; ¥487,127; ¥534,343; ¥485,376; ¥1,632,714;
¥624,090 — each with its own "工程：請求書照合..." completion note) → the payment-regulation
document (read repeatedly) → **five separate expense settlements** (two travel expenses, one
entertainment, one transport, one training, each with its own amount) → two expense **approvals**
by a manager (a different action from settlement — approval requires manager authority) → an
entertainment-expense regulation document → the outsourcing-expense regulation document again →
a second onboarding checklist read → a second onboarding verification completed ("入社照合完了。
採用区分：新卒家族持。" — new-grad-with-family hire type). **Conservatively, at least 14-16
distinct business actions** (6 payments + 5 expense settlements + 2 approvals + 2 onboarding
verifications) inside one reported "segment," spanning nearly 6 minutes and a chunk boundary that
Phase 1F.5 correctly stitched together but did not further subdivide.

### `SIDDHIGUPTAB00B::173246::seg004` (210.5s) — merged across three departments
Screenshot at event 519 confirms genuine onboarding content (`入社手続き` list, HR system, port
5132). But the same segment also contains: purchase-order processing (発注管理処理, annual
packaging-materials contract, ¥21.7M), an onboarding checklist read, an onboarding verification
completed ("入社照合完了。採用区分：中途。" — mid-career hire), a new-contract-procedure document,
a contract-termination-procedure document, an actual file being edited
("keiyaku_kaijo_tetsuzuki" — contract termination doc), a Logistics dashboard
(受発注在庫管理システム), and two contract-management actions (a maintenance-contract renewal,
a new basic transaction contract). Three departments' work (HR, Finance/procurement, Logistics)
in one segment.

### `NEELA9BAF::180923::seg006` (45.2s) — ambiguous, possibly mislabeled
No onboarding-specific action text appears anywhere in this segment. `extracted_text[543]` shows
a Finance **procurement** dashboard (発注管理, purchase orders, `P10-07048822-001`), and the only
other text is a browser favorites-bar hint mentioning the onboarding route. This segment was
grouped under `5132 onboarding` by route, but the visible content is procurement/dashboard
browsing, not an onboarding action — a second, smaller instance of the same route-vs-content
mismatch flagged in the headline finding, worth a manual re-check before treating it as a genuine
onboarding execution.

---

## 3. `5132 leave-applications` — 3 segments inspected

| segment_id | duration | verdict |
|---|---:|---|
| `NEELA9BAF::180923::seg013` | 4.4s | **single, clean, confirmed** |
| `NEELA9BAF::182634::seg004` | 34.5s | **ambiguous — no leave-specific action, just repeated dashboard views** |
| `SIDDHIGUPTAB00B::181913::seg002` | 199.5s | **merged — invoicing + contracts + 2 real leave approvals** |

### `NEELA9BAF::180923::seg013` (4.4s) — clean single execution, visually confirmed
Screenshot (event 1205) shows `HR人事給与システム` at `.../#/leave-applications`: an attendance
list (`P2-07048822-xxx`) with a detail panel open for **`P2-07048822-006 · 青木拓也（E2001）`**,
申請種別=代休申請 (compensatory-day-off request), 期間=2026-07-13, ステータス=申請中, and
承認 (approve)/差戻し (reject) buttons. `extracted_text[1206]`: *"勤怠申請確認。種別：代休申請。
取得日：2026-07-13。問題なし承認。"* ("Attendance request confirmed. Type: comp-day-off.
Date: 2026-07-13. No issues, approved.") **Input → processing → output**: open the specific
pending request → check against policy → approve. Same clean single-record pattern as the
payroll-items clean example above — this is the second of two genuinely automation-ready
examples found in the whole audit.

### `SIDDHIGUPTAB00B::181913::seg002` (199.5s) — merged, but genuinely contains leave content
This is the segment `process_summary.csv` flagged with `case_id_count=2` (vs. the usual 12) —
worth explaining why: it contains a **monthly recurring-vendor reference list** (not case
records), **two invoice reconciliations** (INV-2026-7067, ¥3,164,947, approved; INV-2026-7070,
¥568,642, approved), a Logistics/contract-management dashboard, contract procedure documents, two
contract-management actions (a maintenance-contract renewal, a new basic contract), **and,
genuinely, two leave/attendance approvals**: *"勤怠申請確認。種別：半日有給申請。...問題なし承認"*
(half-day paid leave, approved) and *"勤怠申請確認。種別：フレックス変更申請。...問題なし承認"*
(flex-time change, approved). So the `leave-applications` label is not wrong here — the segment
does contain real leave approvals — but it also contains substantial unrelated invoicing and
contract-management work, so treating this as "one leave-application execution" would be wrong;
it is at minimum one invoicing task plus two leave approvals plus a contract review.

### `NEELA9BAF::182634::seg004` (34.5s) — ambiguous
Only two near-identical Finance-dashboard snapshots two minutes apart
(`財務会計システム...請求書承認・経費精算`), no leave-specific text or action anywhere. Likely
either idle dashboard browsing while the worker decided what to do next, or a leave-related click
that didn't get OCR'd — cannot confirm either way from available evidence. Flagged Low confidence
for the same reason `process_summary.csv` already rates it Medium/borderline.

---

## Conclusions for Step 3 scoping (evidence, not a decision)

1. **A genuine, clean, single-record, automatable pattern exists and was directly confirmed
   twice**: `NEELA9BAF::190250::seg002` (payroll-items expense confirmation) and
   `NEELA9BAF::180923::seg013` (leave-application approval). Both follow the same shape: open one
   pending record from a list → check amount/policy → click one confirm/approve button. This is
   the strongest evidence in the whole Phase 2 analysis for what a bounded, well-defined
   automation would actually look like.
2. **The majority of longer segments (≥30s) in all three families are merged multi-case work
   sessions**, confirmed directly (not just inferred from duration/case-ID statistics as in
   `phase2_summary.md` §7) — up to ~15 distinct real actions in one 359-second reported segment.
   Any frequency/duration estimate that includes these longer segments as "one execution" is a
   meaningful undercount of true case volume.
3. **New finding: the URL hash-route is not a reliable business-function label outside of what
   has been directly checked.** Confirmed wrong for `5133_onboarding` (all 6 segments — actually
   Finance/Logistics/IT work, not HR onboarding) and ambiguous for one `5132 onboarding` segment
   and one `5132 leave-applications` segment. **Recommendation: before Step 3 scoping on any
   process type, spot-check its representative segments visually the same way this document did
   — do not trust `process_summary.csv`'s auto-generated `human_readable_description` at face
   value for ports other than 5132, and even at 5132 treat the shorter/cleaner segments as the
   trustworthy evidence, not the long merged ones.**
4. **No automation candidate is selected or ranked here.** This document only establishes what is
   and isn't directly supported by the raw evidence for three specific candidates the user named;
   `phase2_summary.md` §6 already covers the broader shortlist and explicitly declines to name a
   winner, and that remains unchanged.
