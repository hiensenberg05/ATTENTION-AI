"""The workflow registry: one table binding a workflow to its moving parts.

WHAT THIS BUYS. The orchestrator, the guard layer, the state machine, the decision
agent, the executor, verification and the audit trail are all workflow-neutral.
The things that genuinely differ per workflow are exactly five, and they are all
listed in one `WorkflowBinding` below:

    definition   the declarative WorkflowDefinition (steps, actions, evidence)
    record_type  which Pydantic model the record is
    policy_key   which section of data/policies.json applies
    evaluate     the deterministic policy gates for that record type
    load_record  how to read one record from the live HR system

Adding a third workflow means adding a definition, a policy section, a gate
function, a screen spec and one row here. It does not mean touching
`orchestrator.py`, and that is the test of whether this is a platform or a demo.

NO LLM IN THIS FILE, and no execution - it is a lookup table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from models.common import WorkflowType
from models.leave import LeaveRequest
from models.payroll import PayrollItem

from .base import WorkflowDefinition
from .leave_approval import LEAVE_APPROVAL_WORKFLOW
from .payroll_confirmation import PAYROLL_CONFIRMATION_WORKFLOW

BusinessRecord = Union[LeaveRequest, PayrollItem]


@dataclass(frozen=True)
class WorkflowBinding:
    """Everything the platform needs in order to run one workflow."""

    definition: WorkflowDefinition
    record_type: type[BusinessRecord]

    #: (record, policy) -> PolicyEvaluation. Imported lazily at call time to keep
    #: this module free of any dependency on the agent package, so the workflow
    #: layer stays importable on its own.
    evaluate: Callable[[Any, dict[str, Any]], Any]

    #: (record_id) -> record, read from the LIVE HR system, not the seed file.
    load_record: Callable[[str], BusinessRecord]

    @property
    def workflow(self) -> WorkflowType:
        return self.definition.workflow

    @property
    def policy_key(self) -> str:
        return self.definition.policy_key


def _evaluate_leave(record: Any, policy: dict[str, Any]) -> Any:
    from agent.policy_engine import evaluate_leave_request

    return evaluate_leave_request(record, policy)


def _evaluate_payroll(record: Any, policy: dict[str, Any]) -> Any:
    from agent.policy_engine import evaluate_payroll_item

    return evaluate_payroll_item(record, policy)


def _load_leave(record_id: str) -> LeaveRequest:
    from mockhr import leave_store

    return leave_store.get(record_id)


def _load_payroll(record_id: str) -> PayrollItem:
    from mockhr import payroll_store

    return payroll_store.get(record_id)


REGISTRY: dict[WorkflowType, WorkflowBinding] = {
    WorkflowType.LEAVE_APPROVAL: WorkflowBinding(
        definition=LEAVE_APPROVAL_WORKFLOW,
        record_type=LeaveRequest,
        evaluate=_evaluate_leave,
        load_record=_load_leave,
    ),
    WorkflowType.PAYROLL_CONFIRMATION: WorkflowBinding(
        definition=PAYROLL_CONFIRMATION_WORKFLOW,
        record_type=PayrollItem,
        evaluate=_evaluate_payroll,
        load_record=_load_payroll,
    ),
}


def binding_for(workflow: WorkflowType) -> WorkflowBinding:
    """The binding for a workflow, or raise if it is declared but not implemented."""
    try:
        return REGISTRY[workflow]
    except KeyError:
        raise KeyError(
            f"Workflow {workflow.value} is declared but has no implementation binding."
        ) from None


def maybe_binding_for(workflow: WorkflowType) -> Optional[WorkflowBinding]:
    """The binding for a workflow, or None."""
    return REGISTRY.get(workflow)


def all_definitions() -> tuple[WorkflowDefinition, ...]:
    """Every implemented workflow definition, in registration order."""
    return tuple(b.definition for b in REGISTRY.values())
