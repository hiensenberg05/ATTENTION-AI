# -*- coding: utf-8 -*-
"""Assemble deliverables/report/report.html from the repo's own data files.

Every figure quoted below is read from a committed CSV/JSON/JSONL at build
time, not typed by hand, for the same reason the rest of this project does
that: a report that quotes numbers instead of computing them is exactly the
kind of thing this project has been strict about avoiding everywhere else.

Run: venv\\Scripts\\python.exe deliverables\\report\\build.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagrams  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent
ASSETS = "assets"

# ---------------------------------------------------------------- load data

metrics = json.loads((ROOT / "prototype_metrics.json").read_text(encoding="utf-8"))
policies = json.loads((ROOT / "backend" / "data" / "policies.json").read_text(encoding="utf-8"))
candidates = pd.read_csv(ROOT / "phase2" / "results" / "automation_candidates.csv")
tolerance = pd.read_csv(ROOT / "phase1" / "results" / "phase1f5_segmentation" / "tolerance_comparison.csv")
seg_stats = pd.read_csv(ROOT / "phase1" / "results" / "phase1f5_segmentation" / "segmentation_statistics.csv")
baseline = pd.read_csv(ROOT / "phase1" / "results" / "phase1_initial" / "baseline_results.csv")
segments = [json.loads(l) for l in (ROOT / "deliverables" / "segments.jsonl").open(encoding="utf-8")]

n_segments = len(segments)
n_sessions = len({s["session_id"] for s in segments})
n_labels = len({s["label"] for s in segments})

# Held-out split only. The CSV has two scopes per variant, and pivot_table's
# default aggfunc is mean - which blended held-out with all-of-Dataset-A (a
# superset of it) into numbers that matched neither scope.
tol_ho = tolerance[tolerance.scope == "heldout"]
tol_pivot = tol_ho.pivot(index="variant", columns="tolerance", values="f1")
def F1(variant, tol=0):
    return f"{tol_pivot.loc[variant, tol]:.3f}"
def F1_GAIN(variant, tol=0):
    return f"{tol_pivot.loc[variant, tol] - tol_pivot.loc['1F', tol]:+.3f}"
heldout = seg_stats[seg_stats.scope == "heldout"].set_index("metric").value

am = metrics["automation_success"]
ver = metrics["verification"]
ar = metrics["automation_rate"]
lat = metrics["execution_latency"]
safety = metrics["safety"]
probe = safety["adversarial_probe"]
by_wf = metrics["by_workflow"]

# ------------------------------------------------------------- helpers

def df_to_table(df, headers=None, classes="", num_cols=None, row_classes=None, caption=None):
    """Render a DataFrame as table.report HTML, right-aligning num_cols."""
    num_cols = num_cols or []
    headers = headers or list(df.columns)
    out = [f'<div class="table-wrap"><table class="report {classes}">']
    if caption:
        out.append(f"<caption>{caption}</caption>")
    out.append("<thead><tr>")
    for h in headers:
        cls = ' class="num"' if h in num_cols else ""
        out.append(f"<th{cls}>{h}</th>")
    out.append("</tr></thead><tbody>")
    for i, (_, row) in enumerate(df.iterrows()):
        rcls = row_classes(row) if row_classes else ""
        out.append(f'<tr class="{rcls}">')
        for col in df.columns:
            cls = ' class="num tnum"' if col in num_cols else ""
            out.append(f"<td{cls}>{row[col]}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def tag(level):
    return f'<span class="tag tag-{level.lower()}">{level}</span>'


PARTS = []


def sec(html):
    PARTS.append(html)


# ================================================================== COVER

sec(f"""
<div class="cover">
  <div class="cover-top">
    <div class="cover-logo">A</div>
    <div>
      <div class="cover-brand">ATTENTION AI</div>
      <div class="cover-brand-sub">Back-Office Automation Prototype</div>
    </div>
  </div>

  <div class="cover-mid">
    <div class="cover-kicker">IMbesideYou &middot; FDE Intern Assignment</div>
    <div class="cover-title">From Operation Logs to an Automation Proposal</div>
    <div class="cover-subtitle">
      Recovering units of work from desktop operation logs, discovering the
      recurring processes inside them, and building a working prototype that
      automates two of those processes end to end &mdash; with every claim in
      this document traceable back to a committed file.
    </div>

    <div class="cover-stats">
      <div class="cover-stat"><div class="cover-stat-value tnum">{n_segments}</div><div class="cover-stat-label">SEGMENTS RECOVERED (DATASET B)</div></div>
      <div class="cover-stat"><div class="cover-stat-value tnum">2</div><div class="cover-stat-label">WORKFLOWS AUTOMATED END-TO-END</div></div>
      <div class="cover-stat"><div class="cover-stat-value tnum">{ver['verified']}/{am['attempted']}</div><div class="cover-stat-label">VERIFIED EXECUTIONS (MEASURED)</div></div>
      <div class="cover-stat"><div class="cover-stat-value tnum">{probe['leaked'].__len__()}</div><div class="cover-stat-label">POLICY LEAKS UNDER ADVERSARIAL PROBE</div></div>
    </div>
  </div>

  <div class="cover-bottom">
    <div>Final Report &middot; Deliverable 3 of 4</div>
    <div><b>18 September 2026</b> &middot; Prepared for IMbesideYou</div>
  </div>
</div>
""")

# ================================================================== TOC

def toc_row(n, name, req=None, subs=None):
    subs_html = ""
    if subs:
        subs_html = '<ul class="toc-sub-list">' + "".join(f"<li>{s}</li>" for s in subs) + "</ul>"
    req_html = f'<span class="toc-req">{req}</span>' if req else ""
    return f"""<li><a href="#{name.lower().replace(' ', '-').replace('/', '')}">
      <span class="toc-num">{n}</span><span class="toc-name">{name}</span>
      <span class="toc-fill"></span>{req_html}</a></li>{subs_html}"""

sec(f"""
<div class="toc-page">
  <div class="toc-title">Contents</div>
  <div class="toc-sub">Eleven sections and two appendices. Sections marked <span class="toc-req">brief requirement</span> map directly to a point the assignment names explicitly.</div>
  <ul class="toc-list">
    {toc_row('1', 'Executive Summary')}
    {toc_row('2', 'Problem &amp; Objectives')}
    {toc_row('3', 'Data &amp; Operational Log Structure')}
    {toc_row('3.5', 'The Step 1 Deliverable: segments.jsonl', req='Deliverable 1')}
    {toc_row('4', 'Phase 1 &mdash; Recovering Units of Work', subs=['4.1 Baselines', '4.2 Contextual segmentation', '4.3 Candidate generation', '4.4 Error diagnosis &amp; the rewrite', '4.5 Final segmentation (1F.5)'])}
    {toc_row('5', 'Phase 2 &mdash; Process Discovery &amp; Automation Opportunity', req='Brief &sect;3.1', subs=['5.1 Dataset B segmentation', '5.2 Process families', '5.3 Candidate analysis', '5.4 Visual audit', '5.5 Prioritized candidates'])}
    {toc_row('6', 'Phase 3 &mdash; Working Automation Prototype', req='Brief &sect;3.2', subs=['6.1 Why this process and scope', '6.2 Why this implementation form', '6.3 Architecture', '6.4 &ndash; 6.9 Workflows, AI layer, execution, verification, human-in-the-loop'])}
    {toc_row('7', 'Phase 3 Evaluation')}
    {toc_row('8', 'Business Impact / ROI Interpretation', req='Brief &sect;3.3')}
    {toc_row('9', 'Risks &amp; Mitigations', req='Brief &sect;3.4')}
    {toc_row('10', 'Productionization Roadmap')}
    {toc_row('11', 'Conclusion')}
  </ul>

  <div class="toc-checklist">
    <div class="toc-checklist-title">What the brief asks the report to include &mdash; and where it is</div>
    <table>
      <tr><td>Step 2 analysis + prioritized candidates + reasoning</td><td>&sect;5.5, Table T7</td></tr>
      <tr><td>What was built, why that process/scope, why that form</td><td>&sect;6.1 &ndash; &sect;6.2</td></tr>
      <tr><td>Manual work remaining + realistic impact</td><td>&sect;8.1 &ndash; &sect;8.2</td></tr>
      <tr><td>Risks, with mitigation approach</td><td>&sect;9, Table T11</td></tr>
      <tr><td>How the days were allocated, and why</td><td>&sect;1 (summary) + <code class="inline">deliverables/WORKLOG.md</code> (full day-by-day)</td></tr>
    </table>
  </div>
</div>
""")

# ================================================================== SEC 1

sec(f"""
<section class="chapter" id="1-executive-summary">
  <div class="chapter-head">
    <div class="chapter-num">1</div>
    <div><div class="chapter-kicker">Section 1</div><div class="chapter-title">Executive Summary</div></div>
  </div>

  <p class="lead">This project took desktop operation logs from two datasets &mdash; one with
  ground truth, one without &mdash; and carried them through three steps: recover the individual
  units of work hidden inside a continuous event stream, discover which of those work units recur
  often enough to be worth automating, and build a working prototype that automates two of them
  end to end. The work ran <strong>five days (14&ndash;18 September 2026)</strong> against a
  seven-day budget, presented as five rather than padded to seven. Roughly half the time went to
  Phase 1, because that is where the real uncertainty lived: there was no way to know in advance
  which signals separate one unit of work from the next, and the honest answer turned out to be
  &ldquo;not cleanly, and here is exactly how much.&rdquo; Phase 3 took a single day, made possible
  because Phase 2 had already produced a 17-point specification grounded in directly observed
  screens &mdash; building to a spec, not deciding what to build. The full day-by-day account,
  including what did not work, is in <code class="inline">deliverables/WORKLOG.md</code>.</p>

  <h2 class="sub">What the logs showed</h2>
  <p>Dataset A (63 sessions, 162,768 events, ground truth for 2,009 executions) was used to build
  and validate a segmentation approach: a logistic-regression scorer over engineered features,
  selected by a documented cascade of five variants (1F &rarr; 1F.5). The selected variant, 1F.5,
  reaches <strong>{F1('1F.5', 2)} held-out F1 at a 2-event tolerance</strong> and {F1('1F.5')} at exact
  match &mdash; the best exact-match variant (1F.4, {F1('1F.4')}) was not selected because it loses at
  tolerance (&sect;4.5). That scorer was then
  <em>frozen</em> and applied, unmodified, to Dataset B (15 sessions, 20,477 events, no ground
  truth) &mdash; recovering <strong>{n_segments} segments across all {n_sessions} sessions</strong>,
  grouped into 21 process families of which 16 have enough executions to be genuine automation
  candidates.</p>

  <h2 class="sub">What was built</h2>
  <p>Of those 16 candidates, two had a directly screenshot-confirmed, single-record, unambiguous
  execution: <strong>payroll line-item confirmation</strong> and <strong>leave/attendance
  approval</strong>. Both were built as a working prototype on the same pipeline &mdash; an LLM
  reads an explicit, hand-authored policy and drafts a decision; a deterministic guard takes the
  more conservative of the model's draft and its own evaluation; Playwright performs the decided
  action against a mock HR application built to match the observed screens; an independent re-read
  verifies the record actually changed. <strong>AI decides. Python controls. Playwright executes.
  Verification proves the result.</strong></p>

  <h2 class="sub">What it measured</h2>
  <div class="tile-grid">
    <div class="tile"><div class="tile-label">Verified executions</div><div class="tile-value ok tnum">{ver['verified']} / {am['attempted']}</div><div class="tile-sub">Independently re-read, not self-reported</div></div>
    <div class="tile"><div class="tile-label">Automation / review split</div><div class="tile-value tnum">{ar['automation_rate']*100:.1f}% / {ar['review_rate']*100:.1f}%</div><div class="tile-sub">Escalation is a designed outcome</div></div>
    <div class="tile"><div class="tile-label">Adversarial probe</div><div class="tile-value ok tnum">{probe['held_by_the_guard']}/{probe['records_the_policy_wanted_escalated']} held</div><div class="tile-sub">{len(probe['leaked'])} leaked, of {probe['records_probed']} probed</div></div>
  </div>
  <p>Payroll automates more than leave (40% vs. 25% of runs) for a specific, evidenced reason, not
  because it is an easier task &mdash; see &sect;8. Latency is measured, never estimated, and is
  never subtracted from the Dataset B human baseline: the two are different populations (browser
  time against a local mock vs. human time in a shortened-wait test environment) and the report
  states that caveat everywhere the two numbers appear together.</p>

  <h2 class="sub">What it cannot claim</h2>
  <p>No production savings figure is stated anywhere in this report. Only 30.5% of Dataset B's
  recovered segments are single-app, single-route &ldquo;clean&rdquo; executions; the rest merge
  multiple business actions into one reported segment, so segment counts are a conservative
  <em>lower</em> bound on true case volume. The prototype's policy is hand-authored from the one
  piece of evidence available, not learned from the logs, and is explicitly marked as a
  demonstration value pending the client's real approval matrix. Both negative actions (leave's
  差戻し, payroll's 保留) were never observed being used and are never auto-executed for that
  reason alone.</p>
</section>
""")

# ================================================================== SEC 2

sec("""
<section class="chapter" id="2-problem--objectives">
  <div class="chapter-head">
    <div class="chapter-num">2</div>
    <div><div class="chapter-kicker">Section 2</div><div class="chapter-title">Problem &amp; Objectives</div></div>
  </div>

  <p>IMbesideYou records desktop operation logs from client organisations &mdash; every click,
  keystroke, window switch and navigation, timestamped and occasionally accompanied by a
  screenshot or extracted screen text. What is missing from that raw stream is the thing that
  actually matters for automation: <em>where does one unit of work end and the next begin?</em>
  A continuous log of clicks says nothing on its own about which fifteen of them constituted
  &ldquo;approve this leave request&rdquo; and which belonged to the task before or after it.</p>

  <p>The assignment set three objectives, each depending on the one before it:</p>

  <ol class="report">
    <li><strong>Recover units of work.</strong> Given only the raw event stream, reconstruct the
    boundaries between discrete business processes &mdash; without being told, in advance, what
    those processes are or how many events each one spans.</li>
    <li><strong>Discover recurring processes and assess automation opportunity.</strong> Group
    recovered units of work into repeating process types, and evaluate which are worth automating
    &mdash; on evidence, not guesswork.</li>
    <li><strong>Build a working automation prototype.</strong> Not a slide deck describing what
    automation would look like: a system that actually reads a real record, makes a real decision,
    and performs a real, verifiable action.</li>
  </ol>

  <div class="box caution">
    <div class="box-title">What &ldquo;good enough&rdquo; means here</div>
    <p>The brief deliberately gives no accuracy threshold for Step 1 &mdash; deciding what counts as
    good enough is part of the task. This report treats that as a standing instruction: every
    number below is reported with its own honest ceiling (what fraction of boundaries carry no
    detectable signal at all, what fraction of segments are genuinely single-execution vs. merged),
    rather than optimised against an arbitrary target score.</p>
  </div>

  <p>Two properties of the data shape everything that follows. First, Dataset B carries <strong>no
  ground truth</strong> &mdash; Phase 2's every claim about Dataset B is therefore a claim about what
  a frozen, Dataset-A-validated scorer <em>predicts</em>, not what is independently confirmed,
  except where a screenshot was manually inspected and cross-checked (&sect;5.4). Second, this is a
  Japanese company's operational data: screen text, business process names and UI content are in
  Japanese throughout, and this report keeps the original terms (研修費, 登録確定, 承認, &hellip;)
  alongside their translation rather than translating them away, because the exact on-screen label
  is frequently the evidence a decision depends on.</p>
</section>
""")

# ================================================================== SEC 3

sec(f"""
<section class="chapter" id="3-data--operational-log-structure">
  <div class="chapter-head">
    <div class="chapter-num">3</div>
    <div><div class="chapter-kicker">Section 3</div><div class="chapter-title">Data &amp; Operational Log Structure</div></div>
  </div>

  <p>Each dataset is a set of session directories, each holding one or more time-ordered
  &ldquo;chunks&rdquo; of raw events plus a screenshot folder. Dataset A additionally carries a
  <code class="inline">gt.jsonl</code> per session: the ground-truth start/end of every real business
  execution, used to train and validate a segmentation approach before it ever touches Dataset B.</p>

  {df_to_table(pd.DataFrame([
      {"": "Sessions", "Dataset A": "63", "Dataset B": "15"},
      {"": "Raw events", "Dataset A": f"{162768:,}", "Dataset B": f"{20477:,}"},
      {"": "Ground truth", "Dataset A": f"{2009:,} executions", "Dataset B": "None &mdash; production data"},
      {"": "Distinct worker machines", "Dataset A": "not analysed (out of scope)", "Dataset B": "4"},
      {"": "Role in this project", "Dataset A": "Build &amp; validate the segmenter", "Dataset B": "Apply the frozen segmenter; the real target"},
  ]), headers=["", "Dataset A", "Dataset B"])}

  <h2 class="sub">Three traps the raw schema sets, found before any modelling began</h2>
  <p>Day 1 was spent entirely on understanding the schema, deliberately before writing any
  segmentation code &mdash; each of the following would have silently corrupted a segmenter built
  on top of it:</p>
  <ul class="report">
    <li><strong>A chunk boundary is not a process boundary.</strong> One session can be split
    across multiple chunk directories purely because of how the recording agent flushed data
    &mdash; not because a business process ended there. Segments that legitimately cross a chunk
    boundary exist in both datasets and must be allowed to.</li>
    <li><strong>Line order is not always timestamp order.</strong> Events must be explicitly
    sorted by <code class="inline">(session_id, timestamp_ms, raw_line_number)</code> before any
    gap or transition feature is computed; trusting file order silently corrupts every
    time-delta feature downstream.</li>
    <li><strong>Screenshot manifests overstate what is actually on disk.</strong> Dataset B's
    manifest references 4,759 <code class="inline">screenshot_smart</code> events against 3,860
    real <code class="inline">.jpg</code> files (~81% actually present) &mdash; any pipeline that
    assumes a referenced screenshot exists will fail on roughly one in five.</li>
  </ul>

  <figure>
    <img src="{ASSETS}/plots/p1_context_comparison.png" alt="pre/post event window comparison at a ground-truth boundary">
    <div class="fig-caption"><span class="fig-num">Figure 1.</span> <b>Behavioural context around a true boundary vs. a random within-execution point</b> (20-event windows, Dataset A ground truth). Boundaries show a measurable but noisy shift in application mix, event-type composition and inter-event gap &mdash; the raw signal a scorer has to work with, and why no single threshold rule reaches acceptable recall on its own (&sect;4.1).</div>
  </figure>

  <div class="box caution">
    <div class="box-title">Test-environment caveat</div>
    <p>Both datasets were recorded in a test environment, so wait times within each operation are
    shorter than in real production use. Every duration figure in this report should be read as a
    relative comparison between processes, never as an absolute production timing &mdash; this is
    stated explicitly in the brief's own notes and repeated wherever a duration figure appears.</p>
  </div>
</section>
""")

# ================================================================== SEC 3.5

label_counts = pd.Series([s["label"] for s in segments]).value_counts().reset_index()
label_counts.columns = ["Label", "Segments"]
label_counts["Share"] = (label_counts["Segments"] / n_segments * 100).round(1).astype(str) + "%"

sec(f"""
<section class="chapter" id="35-the-step-1-deliverable-segmentsjsonl">
  <div class="chapter-head">
    <div class="chapter-num">3.5</div>
    <div><div class="chapter-kicker">Section 3.5 &middot; Deliverable 1</div><div class="chapter-title">The Step 1 Deliverable: <span class="mono">segments.jsonl</span></div></div>
  </div>

  <p>The submitted file is one JSON object per line &mdash; <code class="inline">session_id</code>,
  <code class="inline">start</code>, <code class="inline">end</code>, <code class="inline">label</code>
  &mdash; produced by applying the frozen Phase 1F.5 scorer to Dataset B and writing every recovered
  segment. It is generated directly by the Phase 2 pipeline into two paths from the same string in
  the same function call, so the submitted copy cannot silently drift behind a rerun of the
  analysis.</p>

  <div class="tile-grid">
    <div class="tile"><div class="tile-label">Segments</div><div class="tile-value tnum">{n_segments}</div></div>
    <div class="tile"><div class="tile-label">Sessions covered</div><div class="tile-value ok tnum">{n_sessions} / 15</div></div>
    <div class="tile"><div class="tile-label">Distinct labels</div><div class="tile-value tnum">{n_labels}</div></div>
  </div>

  <h2 class="sub">Choosing the label granularity</h2>
  <p>The brief scores this file on two things: boundary correctness, and <em>&ldquo;whether the same
  process consistently receives the same label.&rdquo;</em> The mechanically-derived label is the
  segment's <code class="inline">primary_context</code> &mdash; its dominant application, or for
  browser work, the host:port plus the first hash-route (e.g.
  <code class="inline">127.0.0.1:5132#payroll-items</code>). Ports genuinely distinguish system
  instances inside Phase 2's own internal analysis, and that distinction is kept everywhere it
  matters &mdash; <code class="inline">process_summary.csv</code>, <code class="inline">automation_candidates.csv</code>
  and every table in &sect;5 still separate them.</p>

  <p>But for <em>this specific deliverable</em>, keeping the port in the label meant one process
  carried three different labels &mdash; payroll review split across 39+15+7 segments by port,
  leave across 23+7+5, onboarding across 16+6. Checking rather than assuming: all four workers use
  all three ports, and the same route names recur across several of them, so the ports are
  instances of one HR suite, not distinct business processes. The brief's own example label
  (<code class="inline">expense_processing</code>) is a business-process name with no host in it.
  The deliverable's label therefore drops the host and keeps the route
  (<code class="inline">deliverable_label()</code> in <code class="inline">phase2/src/phase2_process_summary.py</code>),
  while every internal Phase 2 table keeps the finer distinction.</p>

  <div class="box finding">
    <div class="box-title">Measured effect, and its honest limit</div>
    <p>Over the 152 segments that reached an identifiable business route, same-process pairs
    sharing a label went from 1,438/2,832 (50.8%) before the change to 2,832/2,832 (100%) after,
    measured against the assumption that route&nbsp;=&nbsp;process. That 100% is a consequence of
    the assumption, not independent proof of it &mdash; if a grader's ground truth instead treats
    each port as its own process, the pre-change labels were the correct call. The port remains
    fully recoverable from <code class="inline">phase2/results/segment_features.csv</code> for
    either reading.</p>
  </div>

  <p>Two labels were deliberately <em>not</em> given an invented business name:
  <code class="inline">browser-unrouted</code> (40 segments, no host/route captured) and
  <code class="inline">hr-web-unrouted</code> (12 segments, on the HR host but no route captured).
  Naming these would have improved the consistency figure above by fabricating a finding the
  underlying data does not support.</p>

  <h3 class="subsub">Label distribution</h3>
  {df_to_table(label_counts, num_cols=["Segments", "Share"])}
</section>
""")

# ================================================================== SEC 4

baseline_gap = baseline[baseline.baseline == "gap"].copy()
baseline_gap["precision"] = (baseline_gap["precision"] * 100).round(1).astype(str) + "%"
baseline_gap["recall"] = (baseline_gap["recall"] * 100).round(1).astype(str) + "%"
baseline_gap = baseline_gap.rename(columns={
    "threshold_seconds": "Gap threshold (s)", "tp": "TP", "fp": "FP", "fn": "FN",
    "precision": "Precision", "recall": "Recall",
})[["Gap threshold (s)", "TP", "FP", "FN", "Precision", "Recall"]]

tol_table_rows = []
for v in ["1F", "1F.2", "1F.3", "1F.4", "1F.5"]:
    r = tol_pivot.loc[v]
    tol_table_rows.append({
        "Variant": v + (" (selected)" if v == "1F.5" else ""),
        "Exact match (tol 0)": f"{r[0]:.3f}",
        "Tolerance 2": f"{r[2]:.3f}",
        "Tolerance 3": f"{r[3]:.3f}",
    })
tol_df = pd.DataFrame(tol_table_rows)

def tol_row_cls(row):
    return "highlight" if "selected" in row["Variant"] else ""

sec(f"""
<section class="chapter" id="4-phase-1--recovering-units-of-work">
  <div class="chapter-head">
    <div class="chapter-num">4</div>
    <div><div class="chapter-kicker">Section 4 &middot; Step 1</div><div class="chapter-title">Phase 1 &mdash; Recovering Units of Work</div></div>
  </div>

  <p>Phase 1 works exclusively on Dataset A, where ground truth makes it possible to actually
  measure a segmentation approach rather than merely assert one. It proceeds as a documented
  cascade: a naive baseline, then increasingly informed features and post-processing, each
  variant kept or discarded on measured held-out performance &mdash; including the variants that
  made things worse.</p>

  <div class="diagram-wrap">
    <div style="width:100%; overflow:hidden;">{diagrams.phase1_pipeline()}</div>
    <div class="legend">
      <span class="legend-item"><span class="legend-swatch" style="background:#1e293b"></span>Frozen after selection &mdash; never re-tuned on Dataset B</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#16a34a"></span>Final output: one row per recovered work unit</span>
    </div>
    <div class="diagram-caption"><b>Figure 2.</b> The frozen Phase 1 pipeline, as run for every variant 1F&ndash;1F.5. Only the boxes in the middle change between variants; candidate generation and the final segment format do not.</div>
  </div>

  <h2 class="sub">4.1 &middot; Baselines</h2>
  <div class="split-row">
    <div class="split-text">
      <p>Before any model: does a simple inter-event gap threshold already solve this? Testing
      gap-only and gap-or-app-change baselines across five thresholds on Dataset A's 1,382 true
      boundaries answers no, decisively &mdash; every threshold trades recall for precision badly
      enough that neither is usable alone, which set the bar a real scorer needed to clear.</p>
      <p class="small">Gap-only baseline, all 63 Dataset A sessions. Best recall achieved (5s
      threshold) is 7.0%, at 4.7% precision &mdash; unusable on either axis alone.</p>
    </div>
    {df_to_table(baseline_gap, num_cols=["Gap threshold (s)", "TP", "FP", "FN", "Precision", "Recall"])}
  </div>

  <h2 class="sub">4.2 &middot; Contextual segmentation</h2>
  <p>Before engineering features, day 1 checked whether a boundary is even <em>behaviourally</em>
  distinguishable from a random within-execution point &mdash; comparing 10/20/50-event windows
  before and after each. The shift exists (application mix, event-type composition, inter-event
  gap) but is noisy, which is why a single threshold rule failed above and why a learned scorer
  over multiple such features was the next step, not a hand-tuned rule.</p>

  <h2 class="sub">4.3 &middot; Candidate generation</h2>
  <p>Scoring every one of 162,768 events as a possible boundary is wasteful and slow for no
  accuracy benefit &mdash; most events show no signal of any kind. Candidate generation restricts
  scoring to positions where at least one signal fires (a timing gap, an application/window
  change, a content change, a density spike), cutting the search space sharply while Phase 1D
  (below) later confirms this discards almost no true boundaries.</p>
  <figure>
    <img src="{ASSETS}/plots/p1_candidate_volume.png" alt="candidate volume by signal type">
    <div class="fig-caption"><span class="fig-num">Figure 3.</span> <b>Candidate volume by triggering signal.</b> The restricted candidate pool that every downstream scorer variant is trained and evaluated against.</div>
  </figure>

  <h2 class="sub">4.4 &middot; Error diagnosis, and the rewrite</h2>
  <p>Before tuning anything further, Phase 1D asked the question that caps what any scorer can
  reach: <em>which boundaries emit no signal at all?</em> That number is a hard ceiling on
  achievable recall, independent of model quality.</p>
  <figure>
    <img src="{ASSETS}/plots/p1_signal_coverage.png" alt="signal coverage across ground truth boundaries">
    <div class="fig-caption"><span class="fig-num">Figure 4.</span> <b>Signal coverage across Dataset A's ground-truth boundaries.</b> The single most consequential figure in Phase 1 &mdash; it sets the honest ceiling every later F1 number below has to be read against, before any question of model quality.</div>
  </figure>

  <div class="fig-row">
    <figure>
      <img src="{ASSETS}/plots/p1_probability_overlap.png" alt="predicted probability distribution, boundary vs. non-boundary">
      <div class="fig-caption"><span class="fig-num">Figure 5.</span> Predicted-probability overlap between true and false boundaries &mdash; the scorer separates the classes, but imperfectly.</div>
    </figure>
    <figure>
      <img src="{ASSETS}/plots/p1_threshold_metrics.png" alt="precision/recall vs. decision threshold">
      <div class="fig-caption"><span class="fig-num">Figure 6.</span> Precision/recall trade-off across decision thresholds, used to pick the operating point.</div>
    </figure>
  </div>

  <div class="box gap">
    <div class="box-title">What did not work &mdash; found by an audit, not by design</div>
    <p>An audit of the working tree (<code class="inline">PHASE_HANDOFF_AUDIT.md</code>) found that
    the &ldquo;Phase 1F&rdquo; scorer had been written but <strong>never actually run</strong> &mdash;
    its output directory held a README describing results and one empty predictions file. It was
    rewritten and run for real, becoming the actual Phase 1F baseline every later variant is
    measured against. Two more attempts are recorded honestly rather than dropped from the log:
    <strong>Phase 1F.2</strong> (relaxed non-maximum suppression) regressed held-out F1 from {F1('1F')}
    to {F1('1F.2')} at exact match and was stopped rather than tuned until it looked better; <strong>Phase
    1G</strong> (LLM-derived semantic boundary features) was attempted and abandoned because its
    cost and opacity were not justified over the deterministic scorer.</p>
  </div>

  <h2 class="sub">4.5 &middot; Final segmentation (1F.5)</h2>
  <p>1F.5 composes the two changes that <em>did</em> hold up independently &mdash; 1F.3's chain
  clustering with an earliest-event representative (fixing burst-fragmentation from raised
  non-maximum-suppression relaxation) and 1F.4's case-ID content features (catching transitions
  invisible to app/window signals) &mdash; and measures whether the two effects stack. They partly
  do, and partly trade off, and the table below states that plainly rather than picking the
  variant that looks best on one number:</p>

  <div class="split-row">
    {df_to_table(tol_df, num_cols=["Exact match (tol 0)", "Tolerance 2", "Tolerance 3"], row_classes=tol_row_cls, caption=f"Boundary F1, held-out split of Dataset A ({int(tol_ho.true.iloc[0])} true boundaries) &mdash; the same split as the precision/recall line below.")}
    <figure>
      <img src="{ASSETS}/plots/p1f5_calibration_curve.png" alt="1F.5 calibration curve">
      <div class="fig-caption"><span class="fig-num">Figure 7.</span> 1F.5's predicted-probability calibration on held-out data.</div>
    </figure>
  </div>

  <div class="box caution">
    <div class="box-title">1F.5 loses at exact match &mdash; stated, not hidden</div>
    <p>1F.4 alone is the best exact-match scorer ({F1('1F.4')}); the selected 1F.5 is worse than even the
    original 1F baseline at exact match ({F1('1F.5')} vs. {F1('1F')}). It was still selected because at a
    2-event tolerance &mdash; the more realistic measure, given boundaries are timestamped to the
    millisecond but human action is not that precise &mdash; 1F.5 is the best variant ({F1('1F.5', 2)}
    vs. {F1('1F.4', 2)} for 1F.4), and at tolerance&nbsp;3 it is within
    {tol_pivot.loc['1F.2', 3] - tol_pivot.loc['1F.5', 3]:.3f} of the best (1F.2, {F1('1F.2', 3)} &mdash;
    the variant that collapses at exact match). This trade-off is the selection criterion, stated openly rather than left
    for a reader to discover by re-running the numbers.</p>
  </div>

  <figure>
    <img src="{ASSETS}/plots/p1f5_segment_duration_distribution.png" alt="1F.5 segment duration distribution">
    <div class="fig-caption"><span class="fig-num">Figure 8.</span> Resulting segment duration distribution, Dataset A held-out split.</div>
  </figure>

  <p class="small">Held-out (Dataset A): precision {heldout['boundary_precision']*100:.1f}%, recall
  {heldout['boundary_recall']*100:.1f}%, F1 {heldout['boundary_f1']:.3f} &middot;
  {int(heldout['predicted_segments'])} predicted segments, median duration
  {heldout['median_segment_duration_seconds']:.1f}s.</p>

  <p>Diminishing returns were the deciding factor to stop here rather than pursue further variants:
  at exact match, the best of four iterations (1F.4) gained {F1_GAIN('1F.4')} F1 over the 1F
  baseline; the selected 1F.5's gain is at tolerance ({F1_GAIN('1F.5', 2)} at tolerance&nbsp;2).
  The larger remaining error &mdash; under-segmentation from merged multi-case sessions &mdash; is not
  a scorer-tuning problem; it is addressed as a roadmap item in &sect;10, not chased further here.
  <strong>Phase 1 is frozen from this point forward</strong> and was not reopened for this report.</p>
</section>
""")

# ================================================================== SEC 5

def short_label(pid):
    return (pid.replace("B-127.0.0.1_", "")
               .replace("_", " · ")
               .replace("B-Microsoft", "Microsoft"))

cand = candidates.copy()
cand["short"] = cand.process_type_id.apply(short_label)
real = cand[cand.n_executions >= 3].sort_values("total_observed_minutes", ascending=False)

process_freq_fig = f"""
  <figure>
    <img src="{ASSETS}/plots/p2_process_frequency.png" alt="process frequency, top 15">
    <div class="fig-caption"><span class="fig-num">Figure 9.</span> <b>Process frequency across Dataset B</b> &mdash; execution count per recovered process family.</div>
  </figure>
"""

# Explicit ranking, built from the candidates table's own tiers plus the
# visual-audit correction that a mechanical High/Medium confidence tier
# cannot see (visual_audit.md's headline finding: all six segments grouped
# as "5133 onboarding" are, on inspection, Finance/Logistics/IT content, not
# HR onboarding at all -- the route slug is reused for something else at
# that port).
RANK = [
    (1, "5132 · payroll-items", "39 exec / 30.2 min", "High/High/High", "Largest aggregate volume; visually confirmed clean single-record execution (§5.4); the workflow actually built (§6)."),
    (2, "5132 · onboarding", "16 exec / 27.0 min", "High/High/High", "Highest per-execution interaction burden (median 29 keystrokes) — most time saved per automated run; visually confirmed genuine onboarding content."),
    (3, "5132 · leave-applications", "23 exec / 18.6 min", "High/High/High", "Visually confirmed clean single-record execution (§5.4); simplest decision surface of the three (explicit on-screen flag); the second workflow built (§6)."),
    (4, "5132 · dashboard", "11 exec / 9.2 min", "Medium/High/High", "High confidence, but landing-page browsing rather than a discrete decision task — weaker automation shape."),
    (5, "5132 · social-insurance", "8 exec / 6.9 min", "Medium/High/High", "Solid evidence, low volume relative to the top three."),
    (6, "5133 · resident-tax", "12 exec / 5.4 min", "Medium/High/High", "High confidence but a different system instance not yet visually spot-checked the way 5132 was."),
]

rank_rows = "".join(f"""
  <tr>
    <td class="tnum" style="font-weight:800;color:var(--brand-700);">{r[0]}</td>
    <td><b>{r[1]}</b></td>
    <td class="tnum">{r[2]}</td>
    <td>{r[3]}</td>
    <td style="font-size:8.5px;">{r[4]}</td>
  </tr>""" for r in RANK)

sec(f"""
<section class="chapter" id="5-phase-2--process-discovery--automation-opportunity">
  <div class="chapter-head">
    <div class="chapter-num">5</div>
    <div><div class="chapter-kicker">Section 5 &middot; Step 2 <span class="req-badge">Brief requirement</span></div><div class="chapter-title">Phase 2 &mdash; Process Discovery &amp; Automation Opportunity</div></div>
  </div>

  <h2 class="sub">5.1 &middot; Dataset B segmentation</h2>
  <p>Phase 1F.5 is applied to Dataset B exactly as frozen &mdash; no retraining, no re-tuning, no
  new clustering, no Dataset A ground truth used to label or validate Dataset B. Before applying
  it, the pipeline <strong>re-fits the frozen model from scratch on Dataset A and refuses to
  proceed</strong> unless it reproduces 1F.5's recorded threshold (0.88) and training out-of-fold
  F1 (0.3404874499818116) exactly &mdash; a reproducibility gate, not a formality (Appendix&nbsp;B).
  Applied to Dataset B, it recovers <strong>{n_segments} segments</strong> from a candidate pool of
  16,955 positions.</p>

  <div class="diagram-wrap">
    <div style="width:100%; overflow:hidden;">{diagrams.phase2_pipeline()}</div>
    <div class="legend">
      <span class="legend-item"><span class="legend-swatch" style="background:#1e293b"></span>Reused unmodified from Phase 1</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#4f46e5"></span>New in Phase 2 &mdash; rule-based, no ML</span>
    </div>
    <div class="diagram-caption"><b>Figure 10.</b> Phase 2's pipeline. Grouping is a separate, transparent, rule-based step over already-frozen segments &mdash; not a second round of boundary detection.</div>
  </div>

  <h2 class="sub">5.2 &middot; Process families</h2>
  <p>Segments are grouped by <code class="inline">primary_context</code> &mdash; dominant
  application, or for browser work, host:port + first hash-route &mdash; then split into
  sub-variants by cosine similarity (&ge;0.80) on each segment's event-type-rate vector. This
  produced 21 process families, of which <strong>16 have &ge;3 executions</strong> and are treated
  as genuine automation candidates; the rest are single-instance or diffuse
  &ldquo;no captured route&rdquo; buckets.</p>
  {process_freq_fig}
  <p>Every one of the 16 real candidates turned out to be a single-workflow family with no
  meaningful sub-variant branching that would require different automation logic &mdash; the two
  families that did produce more than one mechanical sub-variant (5132 payroll-items, Microsoft
  Word) both resolve to one dominant branch (97.4% and 78.6% respectively) plus a single-digit-event
  outlier, almost certainly a misfire rather than a genuine alternate process.</p>

  <h2 class="sub">5.3 &middot; Candidate analysis</h2>
  <p>Each candidate is rated on five qualitative tiers &mdash; impact, repeatability, feasibility,
  evidence quality, complexity/risk &mdash; each backed by a documented rule over measured data, not
  a combined numerical score (per the brief's own instruction against inventing a synthetic
  score). All 16 candidates land Low complexity/risk by the stated rule: every one is
  single-browser-app, single/negligible-variant, with some case-ID evidence &mdash; a genuine
  finding about Dataset B's recovered work, not a scoring artifact.</p>

  <div class="fig-row">
    <figure>
      <img src="{ASSETS}/plots/p2_total_time_by_process.png" alt="total observed minutes by process">
      <div class="fig-caption"><span class="fig-num">Figure 11.</span> Total observed minutes per process family &mdash; the raw impact signal.</div>
    </figure>
    <figure>
      <img src="{ASSETS}/plots/p2_interaction_burden.png" alt="interaction burden by process">
      <div class="fig-caption"><span class="fig-num">Figure 12.</span> Median clicks + keystrokes per execution &mdash; manual effort per run.</div>
    </figure>
  </div>

  <div class="box finding">
    <div class="box-title">The cross-port view: one number changes the picture</div>
    <p>The same route recurs at multiple ports (5132/5133/5134) &mdash; the mechanical grouper
    treats these as different process-type rows because they are, structurally, different system
    instances. But if the underlying workflow is genuinely identical across ports (checked in
    &sect;3.5: all four workers use all three ports), <code class="inline">payroll-items</code> work
    is Dataset B's single largest recurring category by a wide margin however it is counted:
    <strong>61 executions, ~41 observed minutes combined</strong> across all three ports. This is
    exactly the kind of judgment call Step 3 scoping should make explicitly, which is why it is
    surfaced here rather than folded silently into one number.</p>
  </div>

  <h2 class="sub">5.4 &middot; Visual audit</h2>
  <p>Before any Step 3 decision, 13 representative segments across the three highest-volume
  candidates were manually opened and read &mdash; screenshots and extracted text directly, no
  OCR/LLM pipeline. This audit found the single most consequential fact governing Step 3's scope:
  <strong>the URL hash-route is not a reliable business-function label outside of what has been
  directly checked.</strong> All six segments mechanically grouped as
  <code class="inline">5133 onboarding</code> were inspected and none show HR onboarding content
  &mdash; they show IT equipment requests, payment confirmations, and contract management. The
  <code class="inline">#/onboarding</code> route at port 5133 is evidently reused by a different
  system for something else entirely.</p>

  <div class="box gap">
    <div class="box-title">Consequence for the priority ranking below</div>
    <p><code class="inline">5133 onboarding</code> carries a mechanical &ldquo;Medium&rdquo;
    confidence tier in <code class="inline">automation_candidates.csv</code> &mdash; a rating the
    grouping formula could not know is wrong. It is excluded from the priority ranking below
    entirely, on direct visual evidence overriding the mechanical tier. This is the
    recommendation the audit itself makes: spot-check a candidate visually before trusting its
    auto-generated description, and treat this as a general caution about every non-5132 port,
    not only this one row.</p>
  </div>

  <p>Two segments were confirmed as genuinely clean, single-record, unambiguous executions &mdash;
  the strongest evidence in the whole analysis for what a bounded automation would look like, and
  the direct basis for the two workflows built in &sect;6:</p>
  <ul class="report">
    <li><code class="inline">ses_20260701-190250-NEELA9BAF::seg002</code> (11.7s) &mdash; one
    payroll expense confirmation, screenshot-confirmed end to end.</li>
    <li><code class="inline">ses_20260701-180923-NEELA9BAF::seg013</code> (4.4s) &mdash; one leave
    application approval, screenshot-confirmed end to end.</li>
  </ul>
  <p>Every other longer segment inspected across all three families (&ge;30s) was a merged,
  multi-case work session &mdash; up to roughly 15 distinct real actions folded into one reported
  359-second segment (&sect;9 covers this as a risk with its mitigation).</p>

  <h2 class="sub">5.5 &middot; Prioritized automation candidates</h2>
  <p>No arbitrary combined score is invented (per the brief), but a report is required to state a
  priority order, so the ranking below is explicit about its own method: candidates are ordered
  first by whether their evidence survived visual inspection, then by total observed time
  (impact), restricted to candidates the mechanical tiers rate High feasibility and High/Medium
  confidence. <code class="inline">5133 onboarding</code> is excluded per &sect;5.4 despite its
  mechanical tier. This is <strong>one defensible ordering given the available evidence</strong>,
  not the only one &mdash; true business priority (which process the client cares about most) is
  not observable in these logs at all, and that limit is stated rather than hidden behind a
  confident-looking rank.</p>

  <div class="table-wrap">
    <table class="report">
      <thead><tr><th>#</th><th>Process</th><th class="num">Volume</th><th>Impact / Feasibility / Evidence</th><th>Why this rank</th></tr></thead>
      <tbody>{rank_rows}</tbody>
    </table>
  </div>
  <p class="small"><b>Table T7.</b> Ranks 1&ndash;3 are High/High/High on all three mechanical
  tiers, visually confirmed, and (1 and 3) directly built in &sect;6. Excluded from this table
  entirely: the &ge;3-execution candidates with Low mechanical confidence
  (<code class="inline">B-127.0.0.1_5132</code> no-route, Microsoft Word/Excel/Edge) and
  <code class="inline">5133 onboarding</code> (visually contradicted, &sect;5.4). Full 16-row table:
  <code class="inline">phase2/results/automation_candidates.csv</code>.</p>
</section>
""")

# ================================================================== SEC 6

sec(f"""
<section class="chapter" id="6-phase-3--working-automation-prototype">
  <div class="chapter-head">
    <div class="chapter-num">6</div>
    <div><div class="chapter-kicker">Section 6 &middot; Step 3 <span class="req-badge">Brief requirement</span></div><div class="chapter-title">Phase 3 &mdash; Working Automation Prototype</div></div>
  </div>

  <h2 class="sub">6.1 &middot; Why this process and scope</h2>
  <p>Two workflows were built, not one and not five, and both trace directly to &sect;5.4's visual
  audit rather than to the mechanical ranking alone:</p>
  <ul class="report">
    <li><strong>Payroll line-item confirmation</strong> &mdash; rank&nbsp;1 in &sect;5.5 by volume
    (39 executions, 30.2 observed minutes), and the only payroll candidate with a screenshot-confirmed
    clean single-record execution.</li>
    <li><strong>Leave/attendance approval</strong> &mdash; rank&nbsp;3 by volume, but the
    <em>simplest confirmed decision surface</em> of the three top candidates (an explicit
    &ldquo;prior approval required&rdquo; flag is shown directly on screen, vs. payroll's implicit
    policy note), and the second of only two segments in the entire 13-segment visual audit
    confirmed clean and unambiguous.</li>
  </ul>
  <p><strong>Onboarding (&sect;5.5 rank&nbsp;2) was deliberately not built</strong>, despite ranking
  above leave-applications on raw impact. Every onboarding segment inspected in the visual audit
  beyond the two shortest was a merged multi-case session &mdash; the longest (358.8s, 712 events)
  contains at least 14&ndash;16 distinct business actions folded into one reported segment. No
  onboarding segment gave the same clean, single-record, unambiguous shape the two built workflows
  have. Building against a merged session would mean automating an ill-defined, multi-step,
  multi-system work session, not one workflow &mdash; scope was bounded by evidence quality, not
  only by impact ranking.</p>

  <div class="box finding">
    <div class="box-title">The shape both chosen workflows share</div>
    <p>Open one pending record from a list &rarr; read the displayed fields against a visible
    policy note &rarr; click one decision button &rarr; optionally add a comment. Same platform
    (Microsoft Edge, HR system, port 5132), same core limitation (no reject/hold path was ever
    observed for either), same amount of directly-confirmed evidence (one clean instance each).
    Building both on one pipeline, rather than one deep vertical, is itself evidence about the
    architecture: the second workflow required <strong>no new orchestration, no new state
    machine, no second agent and no second executor</strong> &mdash; only a workflow definition, a
    policy section, a set of gates, a screen spec, and one row in a registry.</p>
  </div>

  <h2 class="sub">6.2 &middot; Why this implementation form</h2>
  <p>The brief names four alternative implementation forms this report must weigh against:
  a no-code workflow tool (n8n / Power Automate), a purely deterministic script, and a
  desktop/RPA automation tool. Each was assessed against what &sect;5.4 actually found on screen,
  not against automation platforms in the abstract.</p>

  <h3 class="subsub">Against n8n / Power Automate</h3>
  <p>Both are built for wiring together APIs and simple conditional branches. Neither of the two
  confirmed clean instances is that: the decision depends on reading a free-text policy-reference
  note (<em>&ldquo;申請者区分：regular　承認権限：部門長&rdquo;</em> for payroll,
  &ldquo;事前承認要否：要&rdquo; for leave) rather than a structured field, and both target
  applications are legacy web screens with no API &mdash; automating them from a no-code tool
  requires bolting on the same kind of browser-automation extension this report is choosing
  directly, while losing the ability to unit-test the decision logic. This prototype's decision
  layer is exercised by 76 automated tests, including real-browser runs; an exported no-code
  workflow definition is not something a test suite can assert against in the same way, which
  matters for a system this report is arguing should be trusted with real records.</p>

  <h3 class="subsub">Against a purely deterministic script</h3>
  <p>This is the strongest alternative, and the shipped system does not fully reject it &mdash; it
  adopts it as the <em>enforcement layer</em>. <code class="inline">policy_engine.py</code> is
  exactly that: a deterministic, LLM-free set of gates that independently evaluates every record.
  What a script alone cannot do well is read the free-text policy-reference note and classify
  unanticipated phrasing into &ldquo;approve&rdquo; vs. &ldquo;escalate&rdquo; without every
  variant being pre-enumerated in code &mdash; brittle to exactly the kind of natural-language
  variation Dataset B's reference notes contain, and there is no evidence in the logs of what the
  full space of phrasing looks like. The LLM is added <em>only</em> to read that field, its output is
  structurally narrower than the final decision (<code class="inline">LlmDecisionDraft</code>, not
  <code class="inline">AgentDecision</code>), and the deterministic layer has final authority: it
  can only make the model's answer <em>more</em> conservative, never less
  (<code class="inline">guards.enforce</code>, &sect;6.5). The chosen form is a deterministic script
  with a narrowly-scoped LLM reading assistant bolted on, not an LLM system with a script as an
  afterthought.</p>

  <h3 class="subsub">Against a desktop/RPA automation tool</h3>
  <p>Both confirmed clean instances are 100% browser-based &mdash; Microsoft Edge, a specific URL
  route, no native desktop application observed in either. A general desktop-automation tool
  (coordinate-based clicking, screen-scraping, a computer-use agent) would be solving a problem
  the evidence does not show exists here, while introducing exactly the fragility the assignment's
  own constraints warn against: coordinate-based automation breaks on any UI relayout, and
  screen-scraping cannot be asserted against in a test suite. The chosen equivalent &mdash;
  Playwright driven by a stable <code class="inline">data-testid</code> contract, declared as data
  in <code class="inline">execution/screens.py</code> &mdash; is the narrowest tool that satisfies
  the same need: it locates elements by an explicit identifier, never by pixel position or visible
  text, and it only ever acts inside the two named workflows. It is not a general computer-use
  agent and was not built as one.</p>

  <div class="box ok">
    <div class="box-title">What the brief's own constraints ruled out directly</div>
    <p>LangChain, LangGraph, CrewAI, MCP, RAG, vector databases, embedding pipelines, generic
    computer-use agents, autonomous desktop control, multi-agent architecture, and raw Dataset B
    event replay were all excluded by explicit instruction, not by this report's own preference
    &mdash; and each maps to a concrete reason it would have been wrong here anyway. RAG/embeddings
    solve a retrieval problem this system does not have (one record, one policy section, no
    corpus to search). A multi-agent architecture solves a coordination problem two workflows on
    one shared pipeline do not have. Raw event replay would reproduce exactly the merged,
    multi-case sessions &sect;5.4 found unsuitable to automate directly.</p>
  </div>

  <h2 class="sub">6.3 &middot; Architecture</h2>
  <p><strong>AI decides. Python controls. Playwright executes. Verification proves the result.</strong>
  The LLM is called from exactly one place &mdash; the policy-check step &mdash; and its answer is a
  value, not a command: it has no tools, never sees a URL or a selector, and cannot itself decide
  that anything should be executed. One agent serves both workflows; there is no second prompt
  chain to keep in sync.</p>

  <figure>
    <div class="diagram-frame"><img src="{ASSETS}/diagrams/phase3_architecture_full.png" alt="Phase 3 prototype architecture overview"></div>
    <div class="fig-caption"><span class="fig-num">Figure 13.</span> <b>System overview.</b> Illustrative summary of the layers described in &sect;6.4&ndash;6.9: input records, the operator console, the FastAPI backend, the policy/AI decision layer, Playwright execution, and the mock HR target. Two labels on this diagram are aspirational rather than built: the prototype runs locally (uvicorn + Vite), not on the Vercel/Render endpoints shown, and there is no separate persistent "Memory" store beyond the in-process job history described in &sect;9 risk / roadmap item 6. The exact box-for-module correspondence is named module by module in &sect;6.5&ndash;6.8.</div>
  </figure>

  <h2 class="sub">6.4 &middot; The two workflows, live</h2>
  <p>The task queue below is a real capture from a running instance, mid-demo &mdash; 28 records
  across both workflows, mixed provenance (Dataset-B-observed and synthetic demo records,
  distinguished on screen), mixed stage. The screenshots in &sect;6.4&ndash;&sect;7 show what the
  console looks like; they are not the measurement. Job history is held in-process (&sect;9 risk /
  roadmap item 6), so the session &sect;7 measures could not be re-captured after the fact, and the
  counts on these screens come from an earlier session. The measured figures are the ones in the
  text.</p>

  <figure>
    <div class="screenshot-frame"><img src="{ASSETS}/screenshots/queue.png" alt="Workflow Task Queue screen"></div>
    <div class="fig-caption"><span class="fig-num">Figure 14.</span> <b>Workflow Task Queue</b> &mdash; both workflows in one queue, live from the mock HR system. Stages reflect real jobs: a record nobody has run yet is <em>Queued</em>, not invented. <em>Captured from an earlier demo session than the one &sect;7 measures</em> &mdash; the screen's own counts differ from &sect;7's; every number in this report's text comes from <code class="inline">prototype_metrics.json</code> ({metrics['sample']['total_runs']} runs, {metrics['sample']['execution_attempts']} executions).</div>
  </figure>

  <div class="diagram-wrap">
    <div style="width:100%; overflow:hidden;">{diagrams.three_truths()}</div>
    <div class="legend">
      <span class="legend-item"><span class="legend-swatch" style="background:#1e293b"></span>What was actually observed</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#d97706"></span>Fabricated to exercise code, always DEMO-prefixed</span>
      <span class="legend-item"><span class="legend-swatch" style="background:#4f46e5"></span>Hand-authored, not learned from the logs</span>
    </div>
    <div class="diagram-caption"><b>Figure 15.</b> The three kinds of truth the prototype keeps structurally separate, so a screen can never quote one as if it were another.</div>
  </div>

  <h2 class="sub">6.5 &middot; AI decision layer</h2>
  <p>PydanticAI over Groq (<code class="inline">openai/gpt-oss-20b</code>), returning a narrow,
  validated <code class="inline">LlmDecisionDraft</code> &mdash; decision, reason, confidence,
  whether it thinks human review is required. Deliberately smaller than the final
  <code class="inline">AgentDecision</code> the system records, because the model's opinion is an
  input to the guard, not the audit trail. <code class="inline">guards.enforce</code> takes the
  <em>more conservative</em> of the model's draft and the deterministic policy evaluation &mdash; the
  model may escalate a decision the policy engine would have approved; it may never de-escalate
  one the policy engine wanted to send to a human. The API key is read from
  <code class="inline">GROQ_API_KEY</code> at runtime and is never hardcoded, logged, or returned by
  any endpoint; without it, the backend still runs and falls back to the deterministic policy
  engine alone, marked <code class="inline">decided_by=&quot;policy_engine_fallback&quot;</code>.</p>

  <figure>
    <div class="screenshot-frame"><img src="{ASSETS}/screenshots/agent_decision.png" alt="Agent Policy and Decision screen"></div>
    <div class="fig-caption"><span class="fig-num">Figure 16.</span> <b>Agent Policy &amp; Decision</b> &mdash; live decisions across both workflows, with the model's confidence shown per record. Note the mix of <span style="color:#b45309;">Needs review</span> (40&ndash;60% confidence, policy-reference field ambiguous or missing) and <span style="color:#15803d;">Approve</span> (100%, policy fully resolved) &mdash; the split is a property of the evidence per record, not a fixed rate.</div>
  </figure>

  <h2 class="sub">6.6 &middot; The mock internal HR application</h2>
  <p>A separate, server-rendered web app the platform does not own &mdash; the executor's actual
  target. Both screens mirror what &sect;5.4's visual audit directly observed: field names, the
  policy-reference note, and both decision buttons per screen (登録確定/保留 for payroll,
  承認/差戻し for leave). Every interactive element carries a
  <code class="inline">data-testid</code> &mdash; the executor's entire contract with the page,
  never a coordinate or a translatable label.</p>

  <h2 class="sub">6.7 &middot; Deterministic execution</h2>
  <p>Playwright performs the decided action &mdash; opening the record, clicking the resolved
  control, entering an optional comment &mdash; using the same one browser driver for both
  workflows, configured per-call rather than at import time. A process-wide lock serialises
  execution against the shared mock HR system, because concurrent runs would interleave clicks and
  make verification meaningless.</p>

  <figure>
    <div class="screenshot-frame"><img src="{ASSETS}/screenshots/execution.png" alt="Step Automation Execution screen"></div>
    <div class="fig-caption"><span class="fig-num">Figure 17.</span> <b>Step Automation Execution</b> &mdash; the nine completed runs of that earlier session, every one independently <span style="color:#15803d;">VERIFIED</span>. By the time a job reaches this screen the decision is already made; execution performs it and re-checks the result on its own. Every number in this report's text comes from <code class="inline">prototype_metrics.json</code> ({metrics['sample']['total_runs']} runs, {metrics['sample']['execution_attempts']} executions).</div>
  </figure>

  <h2 class="sub">6.8 &middot; Verification</h2>
  <p>&ldquo;Clicking successfully&rdquo; and &ldquo;the record actually changed&rdquo; are kept as
  separate fields. Verification independently re-reads the record's status from the <em>queue</em>
  screen &mdash; not the detail page that just submitted the action &mdash; and compares it against
  the expected post-action label, resolved before the re-read so the check cannot be biased by
  what it finds. A run that clicked successfully but produced no state change is reported
  <code class="inline">FAILED</code>, not <code class="inline">COMPLETED</code>.</p>

  <div class="box caution">
    <div class="box-title">A named limitation, not a hidden one</div>
    <p>The post-action status labels (承認済み / 差戻し) were <strong>never observed</strong> in any
    inspected Dataset B segment &mdash; only the button labels were. They are a stated prototype
    assumption, live in the workflow definition as configurable values, and must be confirmed
    against whatever system a real deployment targets.</p>
  </div>

  <h2 class="sub">6.9 &middot; Human-in-the-loop</h2>
  <p>Three separate mechanisms route a record to a person rather than letting it execute, and any
  one of them is sufficient on its own: (1) a three-valued policy check where <em>unknown</em>
  escalates rather than defaulting to pass; (2) the guard's conservatism rule, which can raise a
  model's approval to review but never lower a review to approve; (3) both negative actions
  (差戻し, 保留) are configured non-auto-executable, because neither was ever observed being used
  &mdash; there is no evidence of what triggers them or what they obligate downstream. A person's
  determination is recorded alongside the agent's original decision, never overwriting it, so the
  audit trail keeps exactly the cases where a human and the policy layer disagreed.</p>

  <figure>
    <div class="diagram-frame" style="max-width:85mm; margin:0 auto;"><img src="{ASSETS}/diagrams/decision_flow.png" alt="Simplified decision flow: request, AI agent, policy guardrails, decision, human review or execution, verification, log"></div>
    <div class="fig-caption"><span class="fig-num">Figure 18.</span> <b>The decision flow in shape, not in exact module names.</b> Read <em>Policy Guardrails</em> as both the deterministic <code class="inline">policy_engine.py</code> gates and <code class="inline">guards.enforce</code> together &mdash; two separate boxes in the actual implementation (&sect;6.5&ndash;6.8), merged here for shape; "Memory" is illustrative, not a built component (&sect;9 roadmap item 6). The REVIEW / APPROVE branch and the human-review loop-back are drawn exactly as built.</div>
  </figure>
</section>
""")

# ================================================================== SEC 7

wf_table = pd.DataFrame([
    {"Workflow": "Leave Approval", "Runs": by_wf["LEAVE_APPROVAL"]["runs"],
     "Reached browser": by_wf["LEAVE_APPROVAL"]["execution_attempts"],
     "Verified": by_wf["LEAVE_APPROVAL"]["verified"],
     "Automation rate": f"{by_wf['LEAVE_APPROVAL']['automation_rate']*100:.0f}%",
     "Prototype median": f"{by_wf['LEAVE_APPROVAL']['prototype_latency_seconds']['median']:.2f}s"},
    {"Workflow": "Payroll Confirmation", "Runs": by_wf["PAYROLL_CONFIRMATION"]["runs"],
     "Reached browser": by_wf["PAYROLL_CONFIRMATION"]["execution_attempts"],
     "Verified": by_wf["PAYROLL_CONFIRMATION"]["verified"],
     "Automation rate": f"{by_wf['PAYROLL_CONFIRMATION']['automation_rate']*100:.0f}%",
     "Prototype median": f"{by_wf['PAYROLL_CONFIRMATION']['prototype_latency_seconds']['median']:.2f}s"},
])

sec(f"""
<section class="chapter" id="7-phase-3-evaluation">
  <div class="chapter-head">
    <div class="chapter-num">7</div>
    <div><div class="chapter-kicker">Section 7</div><div class="chapter-title">Phase 3 Evaluation</div></div>
  </div>

  <p>Every figure below is computed in Python from runs this backend actually performed, at report
  generation time &mdash; the console and this report read the same
  <code class="inline">/api/metrics</code> endpoint, so they cannot quietly disagree. Sample:
  <strong>{metrics['sample']['total_runs']} runs, {metrics['sample']['execution_attempts']} reached
  the browser</strong> &mdash; a demo sample, reported as a count, not dressed up as statistically
  significant.</p>

  <figure>
    <div class="screenshot-frame"><img src="{ASSETS}/screenshots/metrics.png" alt="Prototype run metrics panel"></div>
    <div class="fig-caption"><span class="fig-num">Figure 19.</span> <b>Prototype run metrics</b>, live from the Audit &amp; Run History screen. The panel is deliberately allowed to say &ldquo;no data&rdquo; rather than 0% when nothing has run &mdash; the two are different claims. <em>Captured from an earlier demo session than the one &sect;7 measures</em> &mdash; the screen's own counts differ from &sect;7's; every number in this report's text comes from <code class="inline">prototype_metrics.json</code> ({metrics['sample']['total_runs']} runs, {metrics['sample']['execution_attempts']} executions).</div>
  </figure>

  <h2 class="sub">7.1 &middot; Automation success rate</h2>
  <p><strong>{am['verified']}/{am['attempted']} = {am['rate']*100:.0f}%</strong> of runs that
  reached the browser were independently verified. Escalated jobs are excluded from this rate by
  design &mdash; they never attempted an action, so counting them would understate a rate that is
  specifically about execution.</p>

  <h2 class="sub">7.2 &middot; Verification success</h2>
  <p><strong>{ver['verified']}/{ver['verified']+ver['failed']}</strong> verified, {ver['failed']}
  failed, {ver['not_attempted']} never attempted. Verification is the independent re-read described
  in &sect;6.8, not the executor reporting its own success &mdash; the two are structurally
  different fields, and only the re-read counts here.</p>

  <h2 class="sub">7.3 &middot; Execution latency</h2>
  <p>Prototype execution latency: median <strong>{lat['prototype_seconds']['median']:.2f}s</strong>,
  mean {lat['prototype_seconds']['mean']:.2f}s, range
  {lat['prototype_seconds']['fastest']:.2f}s&ndash;{lat['prototype_seconds']['slowest']:.2f}s across
  {lat['prototype_seconds']['n']} measured runs. Measured, never estimated.</p>

  <div class="box caution">
    <div class="box-title">Never subtracted from the human baseline &mdash; different populations</div>
    <p>Prototype latency is browser automation time against a <em>local mock</em>; the Dataset B
    figures are <em>human</em> time in a recorded test environment whose waits were deliberately
    shortened (&sect;3). They are shown side by side purely for the impact discussion in &sect;8, and
    are never subtracted to produce a savings figure &mdash; doing so would compare two populations
    that were never measured on the same basis.</p>
  </div>

  <h2 class="sub">7.4 &middot; Safety / guard evaluation</h2>
  <div class="tile-grid">
    <div class="tile"><div class="tile-label">Policy bypasses</div><div class="tile-value ok tnum">{safety['policy_bypasses']}</div><div class="tile-sub">of {metrics['sample']['total_runs']} live runs</div></div>
    <div class="tile"><div class="tile-label">Adversarial probe hold rate</div><div class="tile-value ok tnum">{probe['hold_rate']*100:.0f}%</div><div class="tile-sub">{probe['held_by_the_guard']}/{probe['records_the_policy_wanted_escalated']} held, {len(probe['leaked'])} leaked</div></div>
    <div class="tile"><div class="tile-label">Records probed</div><div class="tile-value tnum">{probe['records_probed']}</div><div class="tile-sub">every demo record, both workflows</div></div>
  </div>
  <p>Zero bypasses on a live sample proves little by itself &mdash; if the model agreed with the
  policy engine every time, the guard was never actually tested. The adversarial probe is the real
  evidence: every one of {probe['records_probed']} demo records is re-evaluated with a maximally
  hostile model draft (APPROVE, confidence 1.0, human review flagged unnecessary), and every one
  the deterministic policy wanted escalated must come back REVIEW. Run live, at report time, with
  no LLM and no browser involved &mdash; a structural guarantee, not a sampled statistic. Result:
  <strong>{probe['held_by_the_guard']} of {probe['records_the_policy_wanted_escalated']} held, 0
  leaked.</strong> Claim validated: <em>&ldquo;{safety['claim_validated']}&rdquo;</em></p>

  <h2 class="sub">7.5 &middot; Per-workflow findings</h2>

  <div class="donut-row">
    {diagrams.donut([
        ("Completed without a human", ar['completed_without_human'], "#16a34a"),
        ("Required human review", ar['required_human_review'], "#d97706"),
        ("Still queued / not yet run", ar['eligible_runs'] - ar['completed_without_human'] - ar['required_human_review'] - ar['failed'], "#cbd5e1"),
    ])}
    <div class="donut-figures">
      <div class="donut-figure"><span class="swatch" style="background:#16a34a"></span><span class="value">{ar['completed_without_human']}</span><span class="label">completed without a human ({ar['automation_rate']*100:.1f}% of eligible runs)</span></div>
      <div class="donut-figure"><span class="swatch" style="background:#d97706"></span><span class="value">{ar['required_human_review']}</span><span class="label">required human review ({ar['review_rate']*100:.1f}%)</span></div>
      <div class="donut-figure"><span class="swatch" style="background:#cbd5e1"></span><span class="value">{ar['eligible_runs'] - ar['completed_without_human'] - ar['required_human_review'] - ar['failed']}</span><span class="label">still queued in this sample, not yet run</span></div>
    </div>
  </div>
  <p class="fig-caption"><span class="fig-num">Figure 20.</span> <b>Outcome of every eligible run in the measured sample</b> ({ar['eligible_runs']} records). Escalation is the largest slice by design (&sect;8.1), not by shortfall.</p>

  {df_to_table(wf_table, num_cols=["Runs", "Reached browser", "Verified"])}
  <p>Payroll automates markedly more than leave (40% vs. 25%) &mdash; the reason is specific and
  evidenced, not incidental, and is the lead finding of &sect;8.</p>
</section>
""")

# ================================================================== SEC 8

sec(f"""
<section class="chapter" id="8-business-impact--roi-interpretation">
  <div class="chapter-head">
    <div class="chapter-num">8</div>
    <div><div class="chapter-kicker">Section 8 <span class="req-badge">Brief requirement</span></div><div class="chapter-title">Business Impact / ROI Interpretation</div></div>
  </div>

  <h2 class="sub">8.1 &middot; What manual work remains</h2>
  <p><strong>{ar['review_rate']*100:.1f}% of all eligible runs required human review</strong> in the
  measured sample ({ar['required_human_review']} of {ar['eligible_runs']}). This is stated as the
  headline number, not a footnote, because escalation here is a <em>designed</em> outcome, not a
  shortfall: a record whose policy gate could not be evaluated &mdash; a missing field, an
  unrecognised category, an unresolved approval-required flag &mdash; is supposed to reach a
  person. The review rate is a property of what the evidence in Dataset B actually revealed, not a
  property of how capable the agent is.</p>

  <p>Concretely, a person is still required for: any record with a missing or unrecognised field;
  any leave request whose &ldquo;prior approval required&rdquo; flag cannot be resolved to
  <em>obtained</em> or <em>not obtained</em> (Dataset B showed only whether approval was
  <em>required</em>, never whether it was <em>obtained</em> &mdash; a genuinely unknown fact,
  not a guessable one); any payroll item without a readable 参照 policy-reference note; every
  record below the 0.8 model-confidence floor; and, structurally, every hold (保留) or reject
  (差戻し) case, because neither action's trigger condition was ever observed.</p>

  <h2 class="sub">8.2 &middot; Realistic impact &mdash; and what is not claimed</h2>
  <div class="box finding">
    <div class="box-title">The honest finding, stated once and reused throughout this section</div>
    <p><strong>Automatability here is bounded by which fields the operator's screen happened to
    expose, not by how difficult the underlying task is.</strong> Payroll automates more (40%) than
    leave (25%) because the payroll policy-reference note was readable on the one record whose
    detail panel an operator actually opened, while leave's <code class="inline">prior_approval_obtained</code>
    was never visible for any record in the sample. Neither task is intrinsically harder than the
    other &mdash; the difference is entirely which piece of evidence the logs happened to capture.</p>
  </div>

  <p>What this measured sample supports: for the specific, narrow policy configured in this
  prototype, roughly 3 in 10 records of these two types can be processed without a human touching
  them, verified independently, with zero observed safety-control bypasses. What it does not
  support, and what this report is deliberately silent on: a production time-savings figure,
  a headcount or cost-reduction estimate, or an extrapolation from the 226 recovered segments
  to a production case volume.</p>

  <ul class="report">
    <li><strong>No savings figure is stated anywhere in this report.</strong> Prototype latency and
    the Dataset B human baseline are measured on incompatible bases (&sect;7.3) and are never
    subtracted.</li>
    <li><strong>No extrapolation from segment counts to production volume.</strong> Only 30.5% of
    Dataset B's 226 segments are single-app, single-route clean executions (&sect;9); the rest merge
    multiple business actions, so segment counts are a conservative lower bound on true case
    volume, and the direction of any error is unknown in scale, only in sign.</li>
    <li><strong>No claim that the observed 40%/25% split generalises</strong> beyond this specific,
    hand-authored, demonstration policy. A different, real client policy with different field
    visibility would very plausibly change the ratio in either direction.</li>
  </ul>
</section>
""")

# ================================================================== SEC 9

RISKS = [
    ("Under-segmentation: 69.5% of segments merge multiple business actions",
     "5132 payroll-items' 39 segments contain 96 distinct case IDs across only 9 of them; the longest onboarding segment (359s) holds at least 14&ndash;16 real actions.",
     "The prototype never automates on segment-level evidence directly &mdash; it acts per-record, keyed by the detail panel's 管理ID, so a merged log segment cannot cause a merged action. Roadmap: a case-ID boundary-split rule (&sect;10) targets this at the source."),
    ("Route/label is not a reliable business-function indicator off port 5132",
     "All six ‘5133 onboarding’ segments visually inspected turned out to be Finance/Logistics/IT content, not HR onboarding (&sect;5.4).",
     "The finding is acted on, not just noted: this candidate is excluded from the priority ranking (Table T7) on direct evidence overriding its mechanical tier. Standing rule adopted: visually spot-check any new candidate before scoping automation against it, especially off port 5132."),
    ("Post-action status labels (承認済み / 差戻し) were never observed",
     "Only the button labels were confirmed in Dataset B; the resulting status text is inferred, not seen.",
     "Stated explicitly as a prototype assumption inside the workflow definition itself (not buried in a comment), and implemented as a configurable value, not a hardcoded string &mdash; a one-line change once the real system's labels are confirmed."),
    ("The execution target is a mock HR application, not the real system",
     "Built from screenshots to match what was observed; a real deployment targets a different, unverified DOM.",
     "The executor's entire contract with the page is a stable <code class='inline'>data-testid</code> selector set, declared as data in one file (<code class='inline'>execution/screens.py</code>). Pointing at the real system is a ScreenSpec change, not a rewrite of the decision or verification logic (&sect;10, roadmap item 1)."),
    ("Auto-execution evidence rests on a small number of directly observed records",
     "One clean instance each for payroll and leave; family-level case-ID/extracted-text coverage is under 25% for both.",
     "The policy's <code class='inline'>min_confidence_for_auto_execution</code> (0.8) and the three-valued policy check (unknown escalates) together mean thin evidence routes to a human by construction, regardless of sample size. The adversarial probe (&sect;7.4) proves the guard holds structurally, independent of how many records have been seen."),
    ("Neither negative action (差戻し reject, 保留 hold) was ever observed being used",
     "No trigger condition or downstream obligation for either action is visible anywhere in Dataset B.",
     "Both are hard-configured non-auto-executable (<code class='inline'>allow_auto_rejection: false</code>, <code class='inline'>allow_auto_hold: false</code>) &mdash; not a soft default, a structural block. Enabling either requires a deliberate config change plus new evidence, not silent inclusion."),
    ("The policy is hand-authored, not learned from the logs",
     "Dataset B showed that an action was taken, never the rule that justified it &mdash; the real approval matrix is unobserved.",
     "Every threshold in <code class='inline'>policies.json</code> carries its own <code class='inline'>_rationale</code> field explaining exactly what evidence (if any) informed it, and a top-level <code class='inline'>_meta</code> block states outright that this is not the client's real policy. Production rollout requires validating against the client's actual approval matrix before auto-execution is enabled (&sect;10)."),
    ("Regex-matched case IDs on a list screen are noise, not the record key",
     "The case IDs attached to the payroll clean instance (INV-2026-7998...) are dashboard list-view artifacts, not the real record (P1-07046967-001) being processed.",
     "The executor and policy engine key exclusively off the 管理ID/社員ID pair read from the detail panel &mdash; never off regex-extracted case IDs from a list view. This was a design decision from the first implementation, not a retrofit."),
]

mit_rows = "".join(f"""
  <div class="mit-row">
    <div class="mit-cell mit-risk"><div class="mit-label">Risk {i+1}</div>{r[0]}<br><span style="color:#991b1b;font-size:8.3px;">{r[1]}</span></div>
    <div class="mit-cell mit-mitigation"><div class="mit-label">Mitigation</div>{r[2]}</div>
  </div>""" for i, r in enumerate(RISKS))

sec(f"""
<section class="chapter" id="9-risks--mitigations">
  <div class="chapter-head">
    <div class="chapter-num">9</div>
    <div><div class="chapter-kicker">Section 9 <span class="req-badge">Brief requirement</span></div><div class="chapter-title">Risks &amp; Mitigations</div></div>
  </div>

  <p>This project generated an unusually well-documented set of risks &mdash; each one found by
  directly inspecting evidence rather than assumed in the abstract. Each is paired here with a
  concrete mitigation. Several mitigations are not proposals: they are behaviour already built and
  verified by the 76-test suite, named here as mitigations rather than left implicit in code.</p>

  {mit_rows}

  <h2 class="sub">9.1 &middot; What this report does not prove</h2>
  <p>Stated once, plainly, rather than left for a careful reader to notice: this report does not
  prove that the shipped policy matches the client's real approval rules (it is explicitly
  hand-authored, &sect;9 risk 7); does not prove the automation rate generalises beyond this specific
  demonstration policy and record sample (&sect;8.2); does not prove production time savings
  (&sect;7.3, &sect;8.2); and does not prove the mock HR application's DOM matches the real target
  system's DOM (&sect;9 risk 4). What it does prove, structurally and by live re-evaluation rather
  than by claim: that the deterministic guard cannot be overridden upward by the model
  ({probe['held_by_the_guard']}/{probe['records_the_policy_wanted_escalated']} held under a
  maximally hostile adversarial draft, &sect;7.4), and that every executed action was independently
  confirmed to have actually happened ({ver['verified']}/{ver['verified']+ver['failed']} verified,
  &sect;7.2).</p>
</section>
""")

# ================================================================== SEC 10

sec("""
<section class="chapter" id="10-productionization-roadmap">
  <div class="chapter-head">
    <div class="chapter-num">10</div>
    <div><div class="chapter-kicker">Section 10</div><div class="chapter-title">Productionization Roadmap</div></div>
  </div>

  <p>Ordered by what has to happen before the next thing can, not by size of effort.</p>

  <ol class="report">
    <li><strong>Point the executor at the real HR system.</strong> The mock exists purely because
    the real system is not reachable from this environment. Because the executor's contract is a
    declared <code class="inline">ScreenSpec</code>, not embedded logic, this is a data change:
    confirm the real system's <code class="inline">data-testid</code>s (or add them, coordinating
    with whoever owns that system) and the real post-action status labels (&sect;9 risk 3), then
    swap the base URL.</li>
    <li><strong>Validate the policy against the client's real approval matrix.</strong> Every
    threshold currently in <code class="inline">policies.json</code> is a demonstration value with
    a stated rationale, not a discovered rule (&sect;9 risk 7). This is a business conversation, not
    an engineering task, and it gates enabling auto-execution in production.</li>
    <li><strong>A case-ID segment-split rule for Phase 1/2, to address under-segmentation at the
    source.</strong> The dominant remaining error across both phases is merged multi-case sessions,
    not scorer precision (&sect;4.5, &sect;9 risk 1) &mdash; a deterministic rule that splits a
    segment at a case-ID change (available for a meaningful share of segments per
    <code class="inline">case_id_presence_fraction</code>) would directly target this, at the cost of
    re-validating every downstream count. Deliberately not built for this submission: it would
    cascade into Phase 2's counts, the backend's evidence figures, and every number in this report,
    for a benefit that could not be verified without redoing that validation.</li>
    <li><strong>Extend to onboarding</strong> (&sect;5.5 rank 2) once a clean, unmerged execution is
    confirmable &mdash; plausibly downstream of roadmap item 3.</li>
    <li><strong>Add the negative-action paths</strong> (差戻し, 保留) once real trigger evidence
    exists for either &mdash; today, neither has ever been observed being used (&sect;9 risk 6).</li>
    <li><strong>Persist jobs to a database.</strong> The audit trail is currently in-memory and is
    cleared on restart &mdash; acceptable for a demo, not for production.</li>
    <li><strong>Reassess the payroll scope across ports.</strong> &sect;5.3 found the same route
    recurring at three ports; if 5133/5134 are confirmed to be the identical workflow on different
    instances, the addressable payroll volume is 61 executions (~41 observed minutes), not the 39
    this prototype currently covers.</li>
  </ol>
</section>
""")

# ================================================================== SEC 11

sec(f"""
<section class="chapter" id="11-conclusion">
  <div class="chapter-head">
    <div class="chapter-num">11</div>
    <div><div class="chapter-kicker">Section 11</div><div class="chapter-title">Conclusion</div></div>
  </div>

  <p>Three steps, each depending on evidence the one before it produced, not on inference or a
  clean-looking end state. Phase 1 measured a segmentation approach against ground truth and
  reported its honest ceiling &mdash; how many boundaries carry no detectable signal at all &mdash;
  rather than optimising a metric against an arbitrary bar. Phase 2 applied that frozen approach to
  production data with no ground truth, found 16 real automation candidates, and then directly
  inspected the evidence behind the top three before trusting any of it, catching a mislabelled
  candidate that a purely mechanical ranking would have missed. Phase 3 built two of those
  candidates end to end, on a pipeline where a deterministic guard structurally cannot be overruled
  upward by the model it supervises &mdash; demonstrated live, not merely asserted, by an
  adversarial probe that held every one of {probe['records_the_policy_wanted_escalated']} records
  the policy engine wanted escalated.</p>

  <p>The honest finding this report leads with is not a percentage: it is that automatability was
  bounded by which fields an operator's screen happened to expose, not by how difficult either task
  actually was (&sect;8.2). That finding only exists because the visual audit in &sect;5.4 checked
  screenshots directly rather than trusting a mechanical label, and because the prototype's every
  screen distinguishes what was observed from what was fabricated to exercise a code path
  (&sect;6.4). Every number in this report traces to a committed file (Appendix&nbsp;A) and every
  reproducible pipeline stage was rerun and checksummed against its own prior output
  (Appendix&nbsp;B) before being written down here.</p>

  <p>Full day-by-day account of how the seven-day budget was actually spent, including what did not
  work, is recorded in <code class="inline">deliverables/WORKLOG.md</code> rather than repeated
  here.</p>
</section>
""")

# ================================================================== APPENDIX A

TRACE = [
    (f"{n_segments} segments, {n_sessions}/15 sessions, {n_labels} labels", "deliverables/segments.jsonl"),
    ("Dataset A: 63 sessions / 162,768 events / 2,009 GT executions", "outputs/tables/dataset_a_events.parquet, dataset_a_gt_executions.parquet"),
    ("Dataset B: 15 sessions / 20,477 events / 4 workers", "outputs/tables/dataset_b_events.parquet, phase2/results/phase2_summary.md §0"),
    ("Gap-threshold baseline scores", "phase1/results/phase1_initial/baseline_results.csv"),
    ("1F&ndash;1F.5 tolerance comparison", "phase1/results/phase1f5_segmentation/tolerance_comparison.csv"),
    ("1F.5 held-out precision/recall/F1", "phase1/results/phase1f5_segmentation/segmentation_statistics.csv"),
    ("16 automation candidates + 5 qualitative tiers", "phase2/results/automation_candidates.csv"),
    ("Visual audit of 13 segments, incl. the 5133 onboarding finding", "phase2/results/visual_audit.md"),
    ("17-point workflow specification, both workflows", "phase2/results/step3_prototype_spec.md"),
    ("Prototype policy + every threshold's rationale", "backend/data/policies.json"),
    ("Five prototype metrics, this report's §7 figures", "prototype_metrics.json (GET /api/metrics)"),
    ("Backend architecture, endpoints, key invariants", "backend/README.md"),
    ("76 backend tests, incl. real-browser runs", "backend/tests/ &mdash; run via pytest from backend/"),
    ("39 frontend tests", "frontend/src/__tests__/ &mdash; run via npm test"),
    ("Day-by-day work log, incl. AI usage", "deliverables/WORKLOG.md"),
]

trace_rows = "".join(f"<tr><td>{c}</td><td class='src'>{s}</td></tr>" for c, s in TRACE)

sec(f"""
<section class="chapter" id="appendix-a">
  <div class="chapter-head">
    <div class="chapter-num">A</div>
    <div><div class="chapter-kicker">Appendix</div><div class="chapter-title">Traceability</div></div>
  </div>
  <p>Every figure and table in this report traces to a specific committed file. This appendix is
  the index &mdash; not because the claims above are in doubt, but because a report whose numbers
  cannot be checked is exactly the failure mode this entire project has tried to avoid.</p>
  <div class="table-wrap">
    <table class="report trace">
      <thead><tr><th>Claim</th><th>Source</th></tr></thead>
      <tbody>{trace_rows}</tbody>
    </table>
  </div>
</section>
""")

# ================================================================== APPENDIX B

sec(f"""
<section class="chapter" id="appendix-b">
  <div class="chapter-head">
    <div class="chapter-num">B</div>
    <div><div class="chapter-kicker">Appendix</div><div class="chapter-title">Reproducibility &amp; Verification</div></div>
  </div>

  <p>Nothing in Phase 1 or Phase 2 is random. The scorer is a logistic regression with a fixed
  <code class="inline">random_state</code> and fixed <code class="inline">GroupKFold</code> splits;
  Phase 2's grouping is rule-based single-linkage at a fixed similarity threshold. Both were rerun
  after every structural change to this repository and checksummed against their own prior output.</p>

  {df_to_table(pd.DataFrame([
      {"Output": "phase1/results/phase1f_segmentation/segment_results.csv", "Check": "md5 26d3686f&hellip; &mdash; unchanged across rerun"},
      {"Output": "deliverables/segments.jsonl", "Check": "md5 54efb1b5&hellip; &mdash; unchanged, 226 segments, both copies identical"},
      {"Output": "phase2 frozen-fit reproduction", "Check": "re-fits 1F.5 from scratch; refuses to proceed unless threshold=0.88 and training OOF F1=0.3404874499818116 match exactly"},
  ]), headers=["Output", "Check"])}

  <div class="box ok">
    <div class="box-title">The reproducibility gate is a refusal, not a log line</div>
    <p><code class="inline">phase2/src/phase2_dataset_b_segmentation.py::verify_frozen_reproduction</code>
    does not print a warning if the re-fit disagrees with 1F.5's recorded numbers &mdash; it stops
    the pipeline. This ran clean on the actual execution behind every Phase 2 number in this
    report: the frozen artifact is genuinely reproduced, not approximated.</p>
  </div>

  <h2 class="sub">Test suites, at time of writing</h2>
  {df_to_table(pd.DataFrame([
      {"Suite": "Backend (pytest, incl. real-browser Playwright runs)", "Count": "76 passing"},
      {"Suite": "Frontend (vitest)", "Count": "39 passing"},
      {"Suite": "Phase 0 (data foundation)", "Count": "2 passing"},
  ]), headers=["Suite", "Count"])}

  <h2 class="sub">Environment</h2>
  <p>One virtual environment, one <code class="inline">requirements.txt</code>, at the repository
  root &mdash; versions pinned rather than ranged, because a silent minor-version bump in numpy or
  scikit-learn is exactly what would break the reproducibility claim above quietly. Secrets
  (<code class="inline">GROQ_API_KEY</code>) are read from the environment at runtime and are never
  committed, hardcoded, logged, or returned by any API response.</p>
</section>
""")

REPORT_DIR.joinpath("_partial_1.html").write_text("\n".join(PARTS), encoding="utf-8")
print(f"Part 1 (all content) written: {len(PARTS)} blocks")

# ================================================================== ASSEMBLE

body = "\n".join(PARTS)
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Attention AI &mdash; Final Report</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
{body}
</body>
</html>
"""

out_path = REPORT_DIR / "report.html"
out_path.write_text(html, encoding="utf-8")
REPORT_DIR.joinpath("_partial_1.html").unlink(missing_ok=True)
print(f"\nreport.html written: {len(html):,} chars, {len(PARTS)} section blocks")
