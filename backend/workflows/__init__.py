"""Declarative workflow definitions."""

from .base import (
    ExecutionActionSpec,
    VerificationSpec,
    WorkflowDefinition,
    WorkflowEvidence,
    WorkflowStepSpec,
)
from .leave_approval import LEAVE_APPROVAL_WORKFLOW

__all__ = [
    "ExecutionActionSpec",
    "LEAVE_APPROVAL_WORKFLOW",
    "VerificationSpec",
    "WorkflowDefinition",
    "WorkflowEvidence",
    "WorkflowStepSpec",
]
