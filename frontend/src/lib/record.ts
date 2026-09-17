/**
 * Workflow-neutral helpers for rendering a business record.
 *
 * The screens are the same for both workflows — a queue, a detail panel, a policy
 * gate list, a decision. Only the FIELDS differ, so the difference lives here as
 * data and the pages stay workflow-agnostic. Adding a third workflow means adding
 * a branch in this file, not a branch in every screen.
 */

import type { BusinessRecord, LeaveRequest, PayrollItem, WorkflowType } from '@/types'
import { isLeaveRequest } from '@/types'

export interface RecordField {
  label: string
  value: string
  /** True when the value is absent — rendered as a gap, never as a blank. */
  missing: boolean
  mono?: boolean
}

/** Money as the HR screen prints it: grouped, with the unit. */
export function yen(amount: string | null): string {
  if (!amount) return ''
  const n = Number(amount)
  return Number.isFinite(n) ? `¥${n.toLocaleString('ja-JP')}` : amount
}

/** The status a record must be in for its workflow to act on it. */
export function actionableStatus(workflow: WorkflowType): string {
  return workflow === 'LEAVE_APPROVAL' ? '申請中' : '未処理'
}

export function isPending(record: BusinessRecord): boolean {
  return record.status === '申請中' || record.status === '未処理'
}

export function workflowOf(record: BusinessRecord): WorkflowType {
  return isLeaveRequest(record) ? 'LEAVE_APPROVAL' : 'PAYROLL_CONFIRMATION'
}

export const WORKFLOW_LABEL: Record<WorkflowType, string> = {
  LEAVE_APPROVAL: 'Leave Approval',
  PAYROLL_CONFIRMATION: 'Payroll Confirmation',
}

/** The short line under a record's name in a list. */
export function recordSubtitle(record: BusinessRecord): string {
  if (isLeaveRequest(record)) {
    return [record.request_type, record.request_date].filter(Boolean).join(' · ') || '—'
  }
  return [record.category, yen(record.amount)].filter(Boolean).join(' · ') || '—'
}

/** What a record's own screen calls its grouping — department, or expense category. */
export function recordContext(record: BusinessRecord): string {
  if (isLeaveRequest(record)) return record.department ?? 'department missing'
  return record.category ?? 'category missing'
}

/** The business fields of a record, in the order its HR screen shows them. */
export function recordFields(record: BusinessRecord): RecordField[] {
  if (isLeaveRequest(record)) {
    const r = record as LeaveRequest
    return [
      { label: '管理ID / Record', value: r.record_id, missing: false, mono: true },
      { label: '社員ID / Employee', value: r.employee_id ?? '', missing: !r.employee_id, mono: true },
      { label: '氏名 / Name', value: r.employee_name ?? '', missing: !r.employee_name },
      { label: '申請種別 / Type', value: r.request_type ?? '', missing: !r.request_type },
      { label: '期間 / Date', value: r.request_date ?? '', missing: !r.request_date, mono: true },
      { label: '所属部署 / Dept', value: r.department ?? '', missing: !r.department },
    ]
  }

  const r = record as PayrollItem
  return [
    { label: '管理ID / Record', value: r.record_id, missing: false, mono: true },
    { label: '社員ID / Employee', value: r.employee_id ?? '', missing: !r.employee_id, mono: true },
    { label: '氏名 / Name', value: r.employee_name ?? '', missing: !r.employee_name },
    { label: '区分 / Category', value: r.category ?? '', missing: !r.category },
    { label: '金額 / Amount', value: yen(r.amount), missing: !r.amount, mono: true },
  ]
}

/**
 * The reference note each workflow's decision depends on, and the evidence gap
 * behind it.
 *
 * Both workflows have the same shape of gap, and it is the single most important
 * thing the UI has to communicate honestly: a note that was visible only for the
 * records whose detail panel an operator actually opened, and is genuinely
 * unknown everywhere else.
 */
export interface ReferenceNote {
  label: string
  value: string
  unknown: boolean
  caveat: string
}

export function referenceNote(record: BusinessRecord): ReferenceNote {
  if (isLeaveRequest(record)) {
    const required = record.prior_approval_required
    const obtained = record.prior_approval_obtained
    const caveat =
      'Dataset B showed whether prior approval was required, never whether it was obtained.'

    // The note has to express the state the DECISION turns on, which is both
    // halves together. Reporting only `required` would hide exactly the gap that
    // sends the one screenshot-confirmed record to a human.
    if (required === null) {
      return { label: '事前承認要否 / Prior approval', value: 'Unknown', unknown: true, caveat }
    }
    if (required === false) {
      return {
        label: '事前承認要否 / Prior approval',
        value: '不要 (not required)',
        unknown: false,
        caveat,
      }
    }
    if (obtained === null) {
      return {
        label: '事前承認要否 / Prior approval',
        value: '要 (required) · obtained: Unknown',
        unknown: true,
        caveat,
      }
    }
    return {
      label: '事前承認要否 / Prior approval',
      value: obtained ? '要 (required) · obtained' : '要 (required) · not obtained',
      unknown: false,
      caveat,
    }
  }
  return {
    label: '参照 / Approval authority',
    value: record.policy_reference ?? 'Unknown',
    unknown: !record.policy_reference,
    caveat:
      'Dataset B showed that approval authority varies by requester type, never the amount thresholds attached to it.',
  }
}

/** Free-text fields a search box should cover, for either record type. */
export function searchableText(record: BusinessRecord): string {
  const common = [record.record_id, record.employee_id, record.employee_name]
  const specific = isLeaveRequest(record)
    ? [record.request_type, record.department, record.request_date]
    : [record.category, record.amount, record.policy_reference]
  return [...common, ...specific].filter(Boolean).join(' ').toLowerCase()
}
