"""PayrollItem - the business record for the Payroll Confirmation workflow.

DECLARED, NOT IMPLEMENTED. Payroll Confirmation is the second workflow and is
deliberately not wired into any endpoint, workflow definition or policy path yet.
This model exists so the schema layer is shaped for it and so the platform's
generality can be demonstrated later without reshaping the foundation.

Field set derived from the Dataset B Finance/HR payroll-items detail panel
(`127.0.0.1:5132/#/payroll-items`), confirmed by screenshot in
`phase2_dataset_b/visual_audit.md`:

    管理ID      -> record_id          (P1-07046967-001)
    社員ID      -> employee_id        (E2011)
    区分        -> category           (研修費)
    金額        -> amount             (25,213円)
    ステータス  -> status             (未処理)
    参照        -> policy_reference   (申請者区分：regular　承認権限：部門長)
    処理コメント -> comment            (free-text box, optional)

Note the identifier trap recorded in `step3_prototype_spec.md`: the regex-matched
case IDs attached to that segment (INV-2026-79xx) were dashboard list-view noise,
NOT the record actually processed. The real key is 管理ID + 社員ID.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PayrollStatus, Provenance


class PayrollItem(BaseModel):
    """One pending payroll/expense line item as read from the queue."""

    model_config = ConfigDict(use_enum_values=False, extra="forbid")

    record_id: str = Field(description="管理ID, e.g. P1-07046967-001")
    status: PayrollStatus = Field(description="ステータス, e.g. 未処理")

    employee_id: Optional[str] = Field(default=None, description="社員ID, e.g. E2011")
    employee_name: Optional[str] = Field(default=None, description="氏名, e.g. 清水 祥平")
    category: Optional[str] = Field(default=None, description="区分, e.g. 研修費")
    amount: Optional[Decimal] = Field(
        default=None, description="金額 in JPY, e.g. 25213. Decimal, never float, for money."
    )
    policy_reference: Optional[str] = Field(
        default=None,
        description="参照 note shown on the detail panel, e.g. 申請者区分：regular　承認権限：部門長",
    )
    comment: Optional[str] = Field(default=None, description="処理コメント free-text")

    provenance: Provenance = Field(description="Where this record's values came from")
    evidence_note: Optional[str] = Field(
        default=None,
        description="For observed records: the Dataset B segment/screenshot backing it.",
    )
