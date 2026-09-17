"""Read-only access to the prototype's JSON data files.

Deliberately simple: load once, validate through the Pydantic models, cache in
memory. No database, no ORM, no write path - this stage only needs to make the
foundation's data reachable by the API (and later by the agent layer).

Every file is validated on load, so a malformed demo record or a status label that
is not in the enum fails loudly at startup rather than surfacing later as a
mysterious 500.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from models.common import WorkflowType
from models.leave import LeaveRequest
from models.payroll import PayrollItem
from workflows.base import WorkflowDefinition
from workflows.leave_approval import LEAVE_APPROVAL_WORKFLOW

DATA_DIR = Path(__file__).resolve().parent / "data"

LEAVE_REQUESTS_FILE = DATA_DIR / "leave_requests.json"
PAYROLL_ITEMS_FILE = DATA_DIR / "payroll_items.json"
POLICIES_FILE = DATA_DIR / "policies.json"


class RecordNotFound(KeyError):
    """Raised when a record id does not exist in the demo dataset."""


class PolicyNotFound(KeyError):
    """Raised when a policy key does not exist in policies.json."""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def get_leave_requests() -> tuple[LeaveRequest, ...]:
    """All demo leave requests, validated. Immutable tuple so the cache is safe."""
    payload = _read_json(LEAVE_REQUESTS_FILE)
    return tuple(LeaveRequest.model_validate(row) for row in payload["records"])


@lru_cache(maxsize=1)
def get_payroll_items() -> tuple[PayrollItem, ...]:
    """All demo payroll items, validated. Prepared for workflow #2, not yet used."""
    payload = _read_json(PAYROLL_ITEMS_FILE)
    return tuple(PayrollItem.model_validate(row) for row in payload["records"])


def get_leave_request(record_id: str) -> LeaveRequest:
    """One leave request by its 管理ID, or raise RecordNotFound."""
    for record in get_leave_requests():
        if record.record_id == record_id:
            return record
    raise RecordNotFound(record_id)


@lru_cache(maxsize=1)
def get_policies() -> dict[str, Any]:
    """The whole prototype policy document, including its `_meta` honesty block."""
    return _read_json(POLICIES_FILE)


def get_policy(policy_key: str) -> dict[str, Any]:
    """One policy section by key (e.g. 'leave_approval'), or raise PolicyNotFound."""
    policies = get_policies()
    if policy_key not in policies or policy_key.startswith("_"):
        raise PolicyNotFound(policy_key)
    return policies[policy_key]


def get_workflows() -> tuple[WorkflowDefinition, ...]:
    """Every declared workflow definition.

    Only Leave Approval is defined so far. Payroll Confirmation is declared as an
    enum member and has demo data and a draft policy section, but has no
    WorkflowDefinition yet and is intentionally absent here.
    """
    return (LEAVE_APPROVAL_WORKFLOW,)


def get_workflow(workflow: WorkflowType) -> Optional[WorkflowDefinition]:
    """One workflow definition by type, or None if it is not defined yet."""
    for definition in get_workflows():
        if definition.workflow is workflow:
            return definition
    return None
