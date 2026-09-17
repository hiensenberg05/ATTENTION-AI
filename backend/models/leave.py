"""LeaveRequest - the business record for the Leave Approval workflow.

Field set is derived from what was actually visible in the Dataset B HR system
(`127.0.0.1:5132/#/leave-applications`), confirmed by screenshot in
`phase2_dataset_b/visual_audit.md`:

    管理ID      -> record_id                  (P2-07048822-006)
    社員ID      -> employee_id                (E2001)
    氏名        -> employee_name              (青木 拓也)
    申請種別    -> request_type               (代休申請)
    期間        -> request_date               (2026-07-13)
    所属部署    -> department                 (営業部)
    ステータス  -> status                     (申請中)
    参照        -> prior_approval_required    (事前承認要否：要)
    承認コメント -> comment                    (free-text box, optional)

WHY MOST FIELDS ARE OPTIONAL: this model represents "what we could read off the
record", not "a record guaranteed complete enough to act on". Completeness is a
separate validation step (state VALIDATING) that can route a record to human
review. Two real cases require this: list-only Dataset B records whose detail
panel was never opened, and the deliberately incomplete demo records. Only
`record_id` and `status` are structurally required.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import LeaveStatus, Provenance


class LeaveRequest(BaseModel):
    """One pending leave/attendance request as read from the HR queue."""

    model_config = ConfigDict(use_enum_values=False, extra="forbid")

    record_id: str = Field(description="管理ID, e.g. P2-07048822-006")
    status: LeaveStatus = Field(description="ステータス, e.g. 申請中")

    employee_id: Optional[str] = Field(default=None, description="社員ID, e.g. E2001")
    employee_name: Optional[str] = Field(default=None, description="氏名, e.g. 青木 拓也")
    request_type: Optional[str] = Field(default=None, description="申請種別, e.g. 代休申請")
    request_date: Optional[date] = Field(default=None, description="期間, e.g. 2026-07-13")
    department: Optional[str] = Field(default=None, description="所属部署, e.g. 営業部")

    prior_approval_required: Optional[bool] = Field(
        default=None,
        description=(
            "事前承認要否 from the detail panel's reference note. None means UNKNOWN "
            "(detail panel never opened for this record), not False."
        ),
    )
    prior_approval_obtained: Optional[bool] = Field(
        default=None,
        description=(
            "PROTOTYPE-ONLY FIELD. Dataset B's UI showed whether prior approval was "
            "REQUIRED, never whether it had been OBTAINED. This field exists so the "
            "prototype policy has something decidable to evaluate; it is not an "
            "observed field and must not be presented as one."
        ),
    )
    comment: Optional[str] = Field(default=None, description="承認コメント free-text")

    provenance: Provenance = Field(description="Where this record's values came from")
    evidence_note: Optional[str] = Field(
        default=None,
        description="For observed records: the Dataset B segment/screenshot backing it.",
    )
