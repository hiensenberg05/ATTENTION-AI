# -*- coding: utf-8 -*-
"""Render report.html -> Attention AI Final Report.pdf via Playwright's chromium.

Chosen over pandoc/wkhtmltopdf because Playwright's chromium is already
installed in the project venv (it drives Phase 3's executor), handles
Japanese text via system fonts without extra configuration, and gives
print-accurate CSS (flex, grid, @page margins) that a LaTeX-based path would
not for this HTML/CSS-authored document.

Two passes, merged:

  1. the cover, on a page with ZERO margin, so its artwork reaches the paper
     edge - Chromium clips page content to the margin box, so a full-bleed
     cover is impossible on any page that reserves a margin;
  2. the whole document with the reserved margins and the running
     header/footer - which need that margin to live in.

Page 1 of pass 2 (the same cover, letterboxed inside the margins) is dropped
in the merge. Rendering pass 2 whole rather than as a page range is deliberate:
it keeps Chromium's own "Page X of Y" numbering aligned with the merged file.
"""
from io import BytesIO
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

REPORT_DIR = Path(__file__).resolve().parent
HTML = REPORT_DIR / "report.html"
OUT = REPORT_DIR.parent / "Attention AI - Final Report.pdf"

# A4 minus nothing: on the bleed pass the cover IS the sheet.
COVER_BLEED_CSS = """
@page { margin: 0; }
.cover {
  width: 210mm;
  height: 297mm;
  margin: 0;
  padding: 32mm 32mm 26mm 32mm;
}
"""

HEADER_TEMPLATE = """
<div style="width:100%; font-size:7.5px; color:#94a3b8; padding:0 18mm;
            font-family:'Segoe UI',sans-serif; display:flex; justify-content:space-between;">
  <span>Attention AI &mdash; Final Report</span>
  <span>IMbesideYou FDE Assignment</span>
</div>
"""

FOOTER_TEMPLATE = """
<div style="width:100%; font-size:7.5px; color:#94a3b8; padding:0 18mm;
            font-family:'Segoe UI',sans-serif; display:flex; justify-content:space-between;">
  <span>18 September 2026</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""

with sync_playwright() as p:
    browser = p.chromium.launch()

    cover_page = browser.new_page()
    cover_page.goto(HTML.as_uri(), wait_until="networkidle")
    cover_page.add_style_tag(content=COVER_BLEED_CSS)
    cover_page.wait_for_timeout(300)
    cover_bytes = cover_page.pdf(
        format="A4",
        print_background=True,
        display_header_footer=False,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        page_ranges="1",
        prefer_css_page_size=False,
    )
    cover_page.close()

    body_page = browser.new_page()
    body_page.goto(HTML.as_uri(), wait_until="networkidle")
    # Let web fonts / layout settle before pagination is computed.
    body_page.wait_for_timeout(300)
    body_bytes = body_page.pdf(
        format="A4",
        print_background=True,
        display_header_footer=True,
        header_template=HEADER_TEMPLATE,
        footer_template=FOOTER_TEMPLATE,
        # Matches @page in style.css exactly - the two sources of truth for
        # page margin must agree, or content that trusts one and a renderer
        # that trusts the other collide.
        margin={"top": "26mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
        prefer_css_page_size=False,
    )
    browser.close()

body = PdfReader(BytesIO(body_bytes))
writer = PdfWriter()
writer.append(BytesIO(cover_bytes))
writer.append(body, pages=(1, len(body.pages)))
with open(OUT, "wb") as fh:
    writer.write(fh)

print(f"PDF written: {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(writer.pages)} pages)")
