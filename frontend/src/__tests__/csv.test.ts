/**
 * CSV export.
 *
 * These assert the cases that produce a file which *looks* fine and is silently
 * wrong: an unescaped comma shifts every later column, and a lost null turns
 * "we never saw this field" into "this field is false".
 */
import { describe, it, expect } from 'vitest'
import { toCsv, stampedFilename, type CsvColumn } from '@/lib/csv'

interface Row {
  id: string
  note: string | null
  flag: boolean | null
  n: number | null
}

const columns: CsvColumn<Row>[] = [
  { header: 'id', value: (r) => r.id },
  { header: 'note', value: (r) => r.note },
  { header: 'flag', value: (r) => r.flag ?? 'UNKNOWN' },
  { header: 'n', value: (r) => r.n },
]

function rowsOf(csv: string) {
  return csv.split('\r\n')
}

describe('csv export', () => {
  it('writes a header even when there is nothing to export', () => {
    expect(toCsv([], columns)).toBe('id,note,flag,n')
  })

  it('quotes a value containing a comma so later columns do not shift', () => {
    const csv = toCsv([{ id: 'A', note: 'Tokyo, Japan', flag: true, n: 1 }], columns)
    expect(rowsOf(csv)[1]).toBe('A,"Tokyo, Japan",true,1')
  })

  it('doubles embedded quotes rather than truncating the cell', () => {
    const csv = toCsv([{ id: 'A', note: 'he said "no"', flag: null, n: null }], columns)
    expect(rowsOf(csv)[1]).toBe('A,"he said ""no""",UNKNOWN,')
  })

  it('quotes newlines so one record stays one row', () => {
    const csv = toCsv([{ id: 'A', note: 'line1\nline2', flag: false, n: 0 }], columns)
    // Three physical lines: header, then a record whose quoted cell spans two.
    expect(csv.startsWith('id,note,flag,n\r\nA,"line1\nline2",false,0')).toBe(true)
  })

  it('keeps null distinct from false', () => {
    const csv = toCsv(
      [
        { id: 'known', note: null, flag: false, n: 0 },
        { id: 'unseen', note: null, flag: null, n: null },
      ],
      columns,
    )
    const [, known, unseen] = rowsOf(csv)
    // false is a finding; null means the field was never visible. The export
    // must not flatten the second into the first.
    expect(known).toBe('known,,false,0')
    expect(unseen).toBe('unseen,,UNKNOWN,')
  })

  it('passes Japanese values through unchanged', () => {
    const csv = toCsv([{ id: 'P1', note: '研修費', flag: null, n: 25213 }], columns)
    expect(rowsOf(csv)[1]).toBe('P1,研修費,UNKNOWN,25213')
  })

  it('names the file with a sortable date and no characters Windows rejects', () => {
    const name = stampedFilename('attention-ai-queue')
    expect(name).toMatch(/^attention-ai-queue-\d{4}-\d{2}-\d{2}\.csv$/)
    expect(name).not.toContain(':')
  })
})
