# Phase 1F.1 — Error Diagnosis (audit only, no pipeline changes)

Scope: read-only analysis of the existing `phase1f_segmentation/boundary_results.csv` (threshold
0.83) and the underlying Dataset A event stream. No feature, scoring, post-processing, or LLM
change was made; Dataset B was not touched. Analysis scripts lived in the session scratchpad, not
the repo — only the resulting evidence (this report + example CSVs) is kept here.

## 1. Are errors concentrated near the 0.83 threshold?

**No.** If they were, moving the threshold would be an easy fix. It isn't:

| | count | within 0.05 of threshold | confidently past it |
|---|---:|---:|---:|
| FP (score ≥ 0.83, wrong) | 2,330 | 253 in [0.83, 0.88) = **10.9%** | 1,434 with score ≥ 0.95 = **61.5%** |
| FN_candidate (missed, was a candidate) | 542 | 52 in [0.78, 0.83) = **9.6%** | 41 with score < 0.3 = **7.6%** |

Score distributions for TP vs FP barely separate at the top end — **FP median score (0.964) is
actually higher than TP median score (0.936)**. The scorer is not weakly-confident-and-wrong near
the boundary; a majority of its false positives are just as confident as its true positives.
Candidate-stage recall is 100% (every one of the 1,382 GT boundaries is in the candidate pool,
`FN_not_candidate` = 0), so all recall loss happens at scoring/selection.

## 2. Where does FN recall loss actually come from?

Split `FN_candidate` (542 rows) by whether the score already cleared the threshold:

- **330 / 542 (60.9%)** scored ≥ 0.83 — the scorer *did* rank them as boundary-like, but
  `predicted_boundary = 0` anyway. That is only possible if the 3-event non-maximum suppression
  discarded them in favor of a higher- or equal-scoring neighbor in the same session.
- **212 / 542 (39.1%)** scored below 0.83 — the scorer itself ranked them as non-boundaries.

So the majority of missed boundaries are not "the model didn't see it" — they were seen, scored
high, and then lost in post-processing.

### Confirmed mechanism: same-signal bursts around one real switch

Inspecting NMS-suppressed cases directly (`nms_fn.csv`), e.g. session `ses_20260701-070320-JAYESH`
around event 753:

```
[750] extension_disconnected  Chrome  受発注在庫管理システム  exec=M1-N-1
[751] app_switch               Chrome  受発注在庫管理システム  exec=M1-N-1   <- accepted (FP)
[752] screenshot_smart         Chrome  受発注在庫管理システム  exec=M1-N-1
[753] app_switch               Chrome  受発注在庫管理システム  exec=M1-D-1   <- TRUE BOUNDARY, score 1.000, suppressed
[754] screenshot_smart         Chrome  受発注在庫管理システム  exec=M1-D-1   <- accepted (FP)
```

Three `app_switch`-adjacent candidates within a 4-event span all score ≈1.0 because they look
identical at the feature level (same app, same window title, same event-type pattern). NMS keeps
751 and 754 (they're ≥3 events apart from each other) and drops 753 — the actual GT event — because
it's within 3 of both. Net effect on the confusion matrix: **one real transition produces one FN
and contributes to two FPs.** This single mechanism plausibly explains a large share of both the
FN and FP counts simultaneously (see §4).

A second, distinct cause of NMS-eligible-but-missed boundaries is **GT/observable-signal lag**:
in `ses_20260701-092027-SIDDHIGUPTAB00B` around event 1243, GT marks the switch at 1243 (still
inside the "HR人事給与システム" window), but the window title only visibly changes to
"受発注在庫管理システム" five events later at 1248. The candidate the scorer prefers nearby is not
necessarily the exact instant GT recorded.

**This category (~61% of FN) is a post-processing / evaluation-tolerance problem, not a
semantic-ambiguity or feature problem.** Exact-event matching plus a flat 3-event NMS radius will
keep manufacturing this exact failure mode regardless of what features or scoring model is used.

## 3. Where does FP volume actually come from?

Computed distance from every FP to the nearest true boundary in the same session:

| distance to nearest true boundary | count | share |
|---|---:|---:|
| ≤3 events (NMS-radius, likely the burst mechanism above) | 937 | 40.2% |
| 4–10 events | 418 | 17.9% |
| 11–30 events | 178 | 7.6% |
| **>30 events (nowhere near any real boundary)** | **797** | **34.2%** |

Mean score barely varies across these buckets (0.92–0.96 in every bucket) — the scorer's
confidence carries no information about whether it's near a real switch or nowhere close to one.

The >30-event bucket (real, unambiguous false alarms) was inspected directly (`far_fp.csv`).
Two representative, fully-inspected examples:

- `ses_20260630-121953-LAPTOP-R36BQBTE` event 2330 (score 1.0, 327 events from the nearest true
  boundary): Chrome → Notepad (`*SETUP.md`) → Windows Explorer "Task Switching", `execution_id =
  None` throughout — this is **unassigned/background activity** (setup script editing, task
  switching), not GT process work at all, but it produces the same app-switch/keystroke signature
  as a real transition.
- `ses_20260701-030836-yuvraj` event 2100 (score 1.0, 65–94 events from the nearest true
  boundary): a click into `procmine-desktop-agent` (the **recording agent's own UI**), then an
  admin PowerShell window, then `session_end` — literally session teardown, `execution_id = None`.

Both are GT-unassigned spans that behaviorally mimic a process switch (app/window changes,
keystrokes) but have no process on either side for `true_boundary` to be computed against. This
is **not primarily a modeling failure** — it's a blind spot in what `true_boundary` can represent
(it only exists where GT has an execution on both sides) combined with a feature set that has no
notion of "in-scope business system" vs "tooling/background." It would need either a `session_end`
/ agent-UI / setup-tooling exclusion rule, or genuine content understanding of the window — not
necessarily an LLM specifically.

## 4. Why do the errors overlap so heavily with TP? — the structural reason

**98.3% of all 1,382 GT boundaries (1,359 of them) occur with *no* visible app or window change at
the exact transition event.** Only 23 true boundaries show `app_change` or `window_change` at the
GT-recorded instant. This matches and sharpens Phase 1D's earlier finding (app change covered only
~1.7%, window change ~2.0%, of GT boundaries) — it is not a minor caveat, it is close to the whole
picture: **almost every real process switch in Dataset A happens inside the same application and
the same window**, typically a different case/order/record loaded into the same web portal page.

Two directly inspected same-app/same-window FN examples make this concrete:

- Event 1208 (`ses_20260630-121953-LAPTOP-R36BQBTE`, score 0.013): `mouse_click` inside Chrome,
  same "HR人事給与システム" window before and after, `execution_id` M1-C-3 → M1-B-3. No
  `extracted_text` at or near the switch. Nothing in event type, app, or window carries any signal
  that the underlying case changed.
- Event 986 (`ses_20260701-054901-LAPTOP-R36BQBTE`, score 0.018): this one *does* have an app
  change (Notepad → Chrome), yet still scored almost zero. Likely explanation: Notepad↔Chrome
  app-switches are extremely common as incidental, non-boundary activity elsewhere in the data
  (matches Phase 1D's low app-change precision), so the model has learned — correctly, on average —
  to discount plain app changes; this particular instance is a false negative caused by that
  learned skepticism being right most of the time and wrong here.

Given this, the reason TP and FP score distributions overlap so much (§1) is structural: since the
model can almost never lean on app/window identity, it is forced to separate real switches from
ordinary same-app activity (rapid clicking, scrolling, typing bursts) using finer signals — density,
gap, event-type-rate shifts — and those signals genuinely look alike in both cases much of the
time. This is a **feature/information ceiling**, not a threshold or post-processing artifact.

## 5. Does error concentrate in a few bad sessions, or is it broad-based?

The 10 sessions with the most FPs run 11–24% per-session precision (one outlier at 38.5%) against
an overall 26.5%/27.3% precision — worse than average, but not catastrophically so, and these are
simply the highest-volume/highest-candidate-count sessions. **Errors are broad-based across most
sessions, roughly proportional to activity volume, not concentrated in a small number of
pathological sessions.** This supports the "structural/information ceiling" reading over a
"handful of weird sessions confusing the model" reading.

## 6. Answering the core question: LLM-resolvable ambiguity, or feature/scoring/post-processing problems?

Both — but not in equal measure, and they point at different fixes:

| Error source | Share (approx.) | Nature | Would an LLM plausibly help? |
|---|---:|---|---|
| NMS burst-suppression + GT/observable-signal lag | ~61% of all FN (≈330/542) | Post-processing / evaluation-tolerance, not semantic | **No** — fixable by tolerance-based matching or cluster-then-pick before NMS, no new signal needed |
| Confident FPs on GT-unassigned background/tooling activity | ~34% of FPs, ≥2 confirmed examples | Blind spot in what `true_boundary` represents + missing "in-scope vs tooling" feature | Partially — needs "is this real business work" judgment, which an LLM *or* a simpler allowlist/heuristic could both plausibly supply |
| Same-app/same-window case switches with no visible signal | Majority of the remaining ~39% genuinely-low-scored FN, and a further share of FP | Real semantic/content ambiguity — distinguishing signal is which record is on screen, not app/window identity | **Yes, in principle** — but `extracted_text` is populated on only ~4% of events (per `DATA_SCHEMA.md`), so an LLM's usable coverage here is capped by how often screen content is actually captured near the transition, not by reasoning ability |

**Bottom line:** the largest single chunk of current error (the NMS/burst mechanism) is a
mechanical post-processing issue that has nothing to do with semantic understanding and should be
fixed before reaching for an LLM at all. The GT-unassigned/background-activity FPs are a labeling-
scope and feature gap, addressable with a much simpler heuristic than an LLM. Only the same-
app/same-window content-invisible switches are genuinely the kind of ambiguity an LLM could help
resolve — and even there, its practical value is bounded by how sparse `extracted_text`/screenshot
coverage actually is in this dataset, so it would not be a complete fix on its own.

## Evidence files

- `far_fp.csv` — high-score FPs >15 events from any true boundary (genuine false alarms)
- `near_fp.csv` — high-score FPs ≤3 events from a true boundary (burst/adjacency artifacts)
- `low_fn.csv` — FN_candidate with score < 0.3 (scorer confidently wrong)
- `nms_fn.csv` — FN_candidate with score ≥ 0.83 (NMS-suppressed despite clearing the threshold)
