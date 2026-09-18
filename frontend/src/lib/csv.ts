/**
 * CSV export.
 *
 * Two details that matter more than they look:
 *
 *  1. **Escaping.** Record comments and evidence notes are free text and do
 *     contain commas, quotes and newlines. A naive `join(',')` produces a file
 *     that opens misaligned and silently shifts every column after the offending
 *     cell — the worst kind of wrong, because it still looks like a table.
 *
 *  2. **A UTF-8 BOM.** Nearly every value here is Japanese (申請中, 研修費,
 *     登録確定済み). Excel on Windows opens a BOM-less UTF-8 CSV as cp932 and
 *     renders all of it as mojibake. The three-byte BOM is what makes the export
 *     actually readable by the person most likely to open it.
 */

/** One column: a header, and how to read it off a row. */
export interface CsvColumn<T> {
  header: string
  value: (row: T) => string | number | boolean | null | undefined
}

/** RFC 4180: quote when needed, and double any embedded quote. */
function cell(raw: string | number | boolean | null | undefined): string {
  if (raw === null || raw === undefined) return ''
  const s = String(raw)
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv<T>(rows: readonly T[], columns: readonly CsvColumn<T>[]): string {
  const lines = [columns.map((c) => cell(c.header)).join(',')]
  for (const row of rows) {
    lines.push(columns.map((c) => cell(c.value(row))).join(','))
  }
  // CRLF: what RFC 4180 specifies, and what Excel expects.
  return lines.join('\r\n')
}

/** Trigger a browser download. No-op outside a DOM, so tests can call the rest. */
export function downloadCsv(filename: string, csv: string): void {
  if (typeof document === 'undefined') return
  const blob = new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** `queue-2026-09-18.csv` — sortable, and no colons for Windows filenames. */
export function stampedFilename(prefix: string): string {
  return `${prefix}-${new Date().toISOString().slice(0, 10)}.csv`
}
