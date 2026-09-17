"""Screen specifications: what the executor needs to know about a target screen.

This is the whole reason Payroll Confirmation did not require a second executor.
The browser work for both workflows is identical in shape -

    open the queue -> locate the row -> open its detail panel -> read the fields
    -> enter a comment -> click the decided control -> re-read the status

- and differs only in the route it lives at, the `data-testid` names on it, and
which controls exist. Those differences are DATA, declared here, so adding a third
workflow means adding a `ScreenSpec`, not writing another driver.

Every value below is a `data-testid`. Nothing in this module is a CSS path, an
XPath, a coordinate, or on-screen text - see `playwright_executor` for why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.common import WorkflowType
from models.execution import ExecutionAction


@dataclass(frozen=True)
class ActionControl:
    """One clickable decision control on a detail panel."""

    testid: str
    #: The literal on-screen label observed in Dataset B, used in error messages
    #: and in the execution step log so the audit trail reads like the screen.
    label: str


@dataclass(frozen=True)
class ScreenSpec:
    """Everything the executor needs to drive one record-processing screen."""

    workflow: WorkflowType

    #: Path under the mock HR base URL, e.g. "leave-applications".
    route: str

    #: Present on the queue screen; its absence means the list did not load.
    list_testid: str
    #: Present on the detail panel; its absence means no record is open.
    detail_testid: str

    #: `f"{open_prefix}{record_id}"` - the control that opens a record.
    open_prefix: str
    #: `f"{row_status_prefix}{record_id}"` - the status cell on the QUEUE screen,
    #: which is what verification re-reads. Deliberately not the detail panel's.
    row_status_prefix: str

    #: Logical field name -> testid on the detail panel. The logical names end up
    #: in the execution step log, so they should read like the business record.
    detail_fields: dict[str, str]

    #: Which detail field carries the record id, for the "did I open the right
    #: record?" assertion.
    id_field: str

    #: The free-text box, if the screen has one.
    comment_testid: str

    #: Decision action -> the control that performs it.
    actions: dict[ExecutionAction, ActionControl] = field(default_factory=dict)

    #: Shown when the HR system refuses an action.
    error_testid: str = "action-error"


LEAVE_SCREEN = ScreenSpec(
    workflow=WorkflowType.LEAVE_APPROVAL,
    route="leave-applications",
    list_testid="leave-list",
    detail_testid="detail-panel",
    open_prefix="open-",
    row_status_prefix="row-status-",
    detail_fields={
        "record_id": "detail-record-id",
        "employee_id": "detail-employee-id",
        "employee_name": "detail-employee-name",
        "request_type": "detail-request-type",
        "request_date": "detail-request-date",
        "department": "detail-department",
        "status": "detail-status",
        "prior_approval_note": "detail-prior-approval",
    },
    id_field="record_id",
    comment_testid="comment-input",
    actions={
        ExecutionAction.APPROVE_LEAVE: ActionControl("approve-button", "承認"),
        ExecutionAction.REJECT_LEAVE: ActionControl("reject-button", "差戻し"),
    },
)

PAYROLL_SCREEN = ScreenSpec(
    workflow=WorkflowType.PAYROLL_CONFIRMATION,
    route="payroll-items",
    list_testid="payroll-list",
    detail_testid="payroll-detail",
    open_prefix="payroll-open-",
    row_status_prefix="payroll-row-status-",
    detail_fields={
        "record_id": "payroll-detail-record-id",
        "employee_id": "payroll-detail-employee-id",
        "employee_name": "payroll-detail-employee-name",
        "category": "payroll-detail-category",
        "amount": "payroll-detail-amount",
        "status": "payroll-status",
        "policy_reference": "payroll-detail-policy-reference",
    },
    id_field="record_id",
    comment_testid="payroll-comment",
    actions={
        # 登録確定 (confirm/register) - the action directly observed end to end.
        ExecutionAction.CONFIRM_PAYROLL: ActionControl(
            "payroll-confirm", "登録確定"
        ),
        # 保留 (hold) - the control exists on screen but was NEVER observed being
        # used, exactly like 差戻し on the leave screen. The workflow definition
        # marks it not auto-executable for the same reason.
        ExecutionAction.HOLD_PAYROLL: ActionControl("payroll-hold", "保留"),
    },
)

SCREENS: dict[WorkflowType, ScreenSpec] = {
    WorkflowType.LEAVE_APPROVAL: LEAVE_SCREEN,
    WorkflowType.PAYROLL_CONFIRMATION: PAYROLL_SCREEN,
}


def screen_for(workflow: WorkflowType) -> ScreenSpec:
    """The screen spec for a workflow, or raise if it has none."""
    try:
        return SCREENS[workflow]
    except KeyError:
        raise KeyError(f"No screen specification for workflow {workflow.value}") from None
