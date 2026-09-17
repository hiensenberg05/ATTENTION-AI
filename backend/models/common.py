"""Shared enums and provenance types used across every backend model.

Kept in one module so `models.leave`, `models.payroll`, `models.agent`,
`models.execution`, `models.job`, `state.machine` and `workflows.*` can all import
the same definitions without circular imports.

PROVENANCE IS LOAD-BEARING HERE. This prototype deliberately distinguishes three
different kinds of truth, because Phase 2's visual audit showed that mechanical
labels and screen-visible fields are not equally trustworthy:

  1. dataset_b_observed      - the record's detail panel AND the operator action on it
                               were directly confirmed in a Dataset B screenshot.
  2. dataset_b_list_observed - the record's row was visible in a Dataset B list view,
                               but its detail panel was never opened, so detail-only
                               fields (e.g. 事前承認要否 / prior_approval_required)
                               are genuinely UNKNOWN, not merely unset.
  3. synthetic_demo          - fabricated for this prototype to exercise code paths.
                               NEVER to be presented as observed behaviour.
"""

from __future__ import annotations

from enum import Enum


class Provenance(str, Enum):
    """Where a prototype record's field values actually came from."""

    DATASET_B_OBSERVED = "dataset_b_observed"
    DATASET_B_LIST_OBSERVED = "dataset_b_list_observed"
    SYNTHETIC_DEMO = "synthetic_demo"


class WorkflowType(str, Enum):
    """Workflows the platform is designed to carry.

    LEAVE_APPROVAL is the first implementation target. PAYROLL_CONFIRMATION is
    declared now so schemas/state are shaped for it, but is NOT implemented yet.
    """

    LEAVE_APPROVAL = "LEAVE_APPROVAL"
    PAYROLL_CONFIRMATION = "PAYROLL_CONFIRMATION"


class DecisionType(str, Enum):
    """What the policy evaluation concluded about a record.

    This is NOT a job state. A job can be in state EXECUTING while carrying
    decision APPROVE. See `state.machine` for the state axis.
    """

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


class AmbiguityType(str, Enum):
    """Why a record could not be decided automatically.

    'Ambiguous' covers several genuinely different failure modes that need
    different handling and different messaging in the human-review UI, so they
    are distinguished at the schema level rather than collapsed into one flag.
    """

    MISSING_REQUIRED_DATA = "MISSING_REQUIRED_DATA"
    POLICY_NOT_COVERED = "POLICY_NOT_COVERED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CONFLICTING_SIGNALS = "CONFLICTING_SIGNALS"
    ACTION_NOT_AUTO_EXECUTABLE = "ACTION_NOT_AUTO_EXECUTABLE"


class LeaveStatus(str, Enum):
    """Status labels for a leave/attendance request.

    PENDING is the label directly observed on screen in Dataset B (`申請中`).
    The post-action labels were NEVER observed - no approved or returned record
    was captured in any inspected segment - so they are explicit prototype
    assumptions, and `workflows.leave_approval` flags them as such.
    """

    PENDING = "申請中"  # observed in Dataset B
    APPROVED = "承認済み"  # PROTOTYPE ASSUMPTION - post-action label not observed
    RETURNED = "差戻し"  # PROTOTYPE ASSUMPTION - taken from the reject button label


class PayrollStatus(str, Enum):
    """Status labels for a payroll/expense line item.

    UNPROCESSED (`未処理`) was observed. The post-action labels are prototype
    assumptions, same caveat as LeaveStatus.
    """

    UNPROCESSED = "未処理"  # observed in Dataset B
    CONFIRMED = "登録確定済み"  # PROTOTYPE ASSUMPTION - post-action label not observed
    ON_HOLD = "保留"  # PROTOTYPE ASSUMPTION - taken from the hold button label
