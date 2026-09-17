"""Deterministic execution: browser control, verification, and run assembly.

    playwright_executor.py  the browser driver (no judgement, testid selectors only)
    verification.py         independent re-read of the record after acting
    runner.py               assembles an ExecutionResult from a decided action

Nothing in this package imports the agent package, and no LLM is reachable from
any of it. Execution is mechanical by construction.
"""

from .playwright_executor import (
    ExecutionError,
    LeaveApprovalExecutor,
    PayrollConfirmationExecutor,
    RecordScreenExecutor,
)
from .runner import (
    ActionNotAutoExecutable,
    action_spec_for,
    execute_decision,
    execute_leave_decision,
)
from .screens import SCREENS, ScreenSpec, screen_for
from .verification import VerificationOutcome, expected_status_after, verify_record_status

__all__ = [
    "RecordScreenExecutor",
    "LeaveApprovalExecutor",
    "PayrollConfirmationExecutor",
    "execute_decision",
    "ScreenSpec",
    "screen_for",
    "SCREENS",
    "ExecutionError",
    "execute_leave_decision",
    "action_spec_for",
    "ActionNotAutoExecutable",
    "verify_record_status",
    "expected_status_after",
    "VerificationOutcome",
]
