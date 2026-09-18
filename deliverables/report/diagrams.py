# -*- coding: utf-8 -*-
"""Architecture diagrams, drawn as inline SVG.

Every box below corresponds to a real module named in backend/README.md's own
ASCII diagram - this just makes it presentable. Colour is meaningful, not
decorative: grey/ink = deterministic Python, indigo = the one LLM call,
amber = the human-in-the-loop path. Nothing here is invented; it is a picture
of code that exists.
"""

INK = "#1e293b"
INK_LIGHT = "#64748b"
LINE = "#cbd5e1"
BRAND = "#4f46e5"
BRAND_LIGHT = "#e0e7ff"
OK = "#16a34a"
OK_LIGHT = "#dcfce7"
WARN = "#d97706"
WARN_LIGHT = "#fef3c7"
SURFACE = "#ffffff"
CANVAS = "#f8fafc"


def _box(x, y, w, h, title, sub, fill=SURFACE, stroke=INK, title_color=None, rx=8):
    title_color = title_color or INK
    lines = sub if isinstance(sub, list) else [sub]
    sub_svg = "".join(
        f'<text x="{x + w/2}" y="{y + 40 + i*13}" text-anchor="middle" '
        f'font-size="9" fill="{INK_LIGHT}" font-family="Segoe UI, sans-serif">{ln}</text>'
        for i, ln in enumerate(lines)
    )
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"
          stroke="{stroke}" stroke-width="1.4"/>
    <text x="{x + w/2}" y="{y + 22}" text-anchor="middle" font-size="12.5" font-weight="700"
          fill="{title_color}" font-family="Segoe UI, sans-serif">{title}</text>
    {sub_svg}
    """


def _arrow(x1, y1, x2, y2, label=None, dashed=False, color=INK_LIGHT, label_dy=-6):
    dash = 'stroke-dasharray="4,3"' if dashed else ""
    label_svg = ""
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label_svg = (
            f'<rect x="{mx-38}" y="{my+label_dy-11}" width="76" height="14" fill="{CANVAS}" opacity="0.92"/>'
            f'<text x="{mx}" y="{my+label_dy}" text-anchor="middle" font-size="8.3" fill="{INK_LIGHT}" '
            f'font-family="Segoe UI, sans-serif">{label}</text>'
        )
    return f"""
    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6" {dash}
          marker-end="url(#arrow)"/>
    {label_svg}
    """


def _defs():
    return f"""
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="{INK_LIGHT}"/>
      </marker>
    </defs>
    """


def phase3_architecture():
    """The end-to-end decision -> execution -> verification pipeline."""
    w, h = 980, 360
    bw, bh = 138, 84
    y0 = 46
    gap = (w - 40 - 6 * bw) / 5
    xs = [20 + i * (bw + gap) for i in range(6)]

    boxes = [
        ("Record", ["LeaveRequest /", "PayrollItem", "(from mock HR)"], SURFACE, INK),
        ("Policy Engine", ["Deterministic gates", "PolicyCheck[]", "no LLM"], SURFACE, INK),
        ("Decision Agent", ["PydanticAI + Groq", "openai/gpt-oss-20b", "one call, no tools"], BRAND_LIGHT, BRAND),
        ("Guards", ["enforce(): takes the", "more conservative of", "model vs. policy"], SURFACE, INK),
        ("Orchestrator", ["State machine", "JobState transitions", "no LLM"], SURFACE, INK),
        ("Executor", ["Playwright", "data-testid selectors", "clicks the real screen"], SURFACE, INK),
    ]

    svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    for i, (x, (title, sub, fill, stroke)) in enumerate(zip(xs, boxes)):
        svg.append(_box(x, y0, bw, bh, title, sub, fill=fill, stroke=stroke,
                         title_color=(BRAND if fill == BRAND_LIGHT else INK)))
        if i < len(xs) - 1:
            svg.append(_arrow(x + bw, y0 + bh / 2, xs[i + 1], y0 + bh / 2))

    # Verification box, offset below-right, closing the loop back onto the record.
    vx, vy = xs[5], y0 + bh + 70
    svg.append(_box(vx - 40, vy, bw + 30, bh - 10, "Verification", ["Independent re-read", "from the QUEUE screen", "(not the page that acted)"],
                     fill=OK_LIGHT, stroke=OK, title_color=OK))
    svg.append(_arrow(xs[5] + bw / 2, y0 + bh, vx + bw / 2 - 10, vy, label="acts"))
    svg.append(_arrow(vx - 40, vy + (bh - 10) / 2, xs[0] + bw, y0 + bh / 2 + 8, label="confirms", dashed=True, color=OK))

    # Human review branch off Guards.
    hx, hy = xs[3], y0 + bh + 70
    svg.append(_box(hx, hy, bw, bh - 10, "Human Review", ["Escalation path", "REVIEW decisions", "never auto-executed"],
                     fill=WARN_LIGHT, stroke=WARN, title_color=WARN))
    svg.append(_arrow(xs[3] + bw * 0.3, y0 + bh, hx + bw * 0.3, hy, label="REVIEW", color=WARN))

    # Caption strip.
    svg.append(
        f'<text x="20" y="{h-14}" font-size="9.5" fill="{INK_LIGHT}" font-family="Segoe UI, sans-serif">'
        f'The model may escalate a decision; it may never de-escalate one. The Guards box enforces that as code, not as a prompt instruction.</text>'
    )
    svg.append("</svg>")
    return "\n".join(svg)


def phase1_pipeline():
    """Candidate generation -> features -> scorer -> selection -> segments."""
    w, h = 980, 190
    bw, bh = 168, 92
    y0 = 30
    gap = (w - 40 - 5 * bw) / 4
    xs = [20 + i * (bw + gap) for i in range(5)]

    boxes = [
        ("Candidate positions", ["Every event with a", "signal (gap, app change,", "content change, …)"]),
        ("Feature engineering", ["Pre/post window stats", "case-ID content features", "(1F.4)"]),
        ("Logistic scorer", ["Trained per-candidate", "boundary probability", "fixed random_state"]),
        ("Selection (1F.3)", ["Tooling filter +", "chain clustering,", "earliest-event pick"]),
        ("Segments", ["start / end / label", "one row per work unit"]),
    ]
    svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    for i, (x, (title, sub)) in enumerate(zip(xs, boxes)):
        fill = OK_LIGHT if i == 4 else SURFACE
        stroke = OK if i == 4 else INK
        svg.append(_box(x, y0, bw, bh, title, sub, fill=fill, stroke=stroke, title_color=(OK if i == 4 else INK)))
        if i < len(xs) - 1:
            svg.append(_arrow(x + bw, y0 + bh / 2, xs[i + 1], y0 + bh / 2))
    svg.append("</svg>")
    return "\n".join(svg)


def phase2_pipeline():
    """Frozen scorer -> Dataset B -> segments -> grouping -> candidates."""
    w, h = 980, 190
    bw, bh = 168, 92
    y0 = 30
    gap = (w - 40 - 5 * bw) / 4
    xs = [20 + i * (bw + gap) for i in range(5)]

    boxes = [
        ("Frozen 1F.5 scorer", ["Re-fit on Dataset A,", "verified to match exactly", "before use"]),
        ("Dataset B events", ["15 sessions,", "no ground truth,", "different departments"]),
        ("226 segments", ["primary_context", "= host:port + route", "(or dominant app)"]),
        ("Process grouping", ["Single-linkage on", "event-type-rate vectors", "cosine >= 0.80"]),
        ("16 candidates", [">=3 executions,", "5-tier qualitative", "assessment, no score"]),
    ]
    svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    for i, (x, (title, sub)) in enumerate(zip(xs, boxes)):
        fill = BRAND_LIGHT if i == 4 else SURFACE
        stroke = BRAND if i == 4 else INK
        svg.append(_box(x, y0, bw, bh, title, sub, fill=fill, stroke=stroke, title_color=(BRAND if i == 4 else INK)))
        if i < len(xs) - 1:
            svg.append(_arrow(x + bw, y0 + bh / 2, xs[i + 1], y0 + bh / 2))
    svg.append("</svg>")
    return "\n".join(svg)


def donut(segments, size=150, thickness=20):
    """A ring chart from real (label, value, color) triples - no library, just
    the arithmetic a donut chart actually is: each slice's share of the
    circle's circumference, laid end to end via stroke-dasharray."""
    total = sum(v for _, v, _ in segments) or 1
    r = (size - thickness) / 2
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r
    offset = 0
    arcs = []
    for _, value, color in segments:
        frac = value / total
        length = frac * circumference
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{thickness}" stroke-dasharray="{length:.2f} {circumference:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += length
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'xmlns="http://www.w3.org/2000/svg">' + "".join(arcs) + "</svg>"
    )


def three_truths():
    """The three kinds of truth the prototype keeps separate."""
    w, h = 980, 180
    bw, bh = 280, 130
    gap = (w - 3 * bw) / 4
    xs = [gap + i * (bw + gap) for i in range(3)]
    y0 = 20

    items = [
        ("Dataset B evidence", ["What was actually observed.", "1 record: full detail panel +", "action, screenshot-confirmed.", "6 more: list-row only, so", "detail fields are null (unknown)."], SURFACE, INK),
        ("Prototype / demo records", ["Fabricated to exercise code", "paths. Always DEMO- prefixed", "so they can never be mistaken", "for an observed record."], WARN_LIGHT, WARN),
        ("Prototype policy", ["Hand-authored rules.", "The logs never revealed the", "real approval policy — only", "that an action was taken.", "Nothing here was learned."], BRAND_LIGHT, BRAND),
    ]
    svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">', _defs()]
    for x, (title, sub, fill, stroke) in zip(xs, items):
        svg.append(_box(x, y0, bw, bh, title, sub, fill=fill, stroke=stroke,
                         title_color=(stroke if stroke != INK else INK)))
    svg.append("</svg>")
    return "\n".join(svg)
