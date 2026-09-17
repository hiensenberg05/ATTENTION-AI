"""Automation job state machine definitions."""

from .machine import (
    ALLOWED_TRANSITIONS,
    DECISION_ROUTES,
    TERMINAL_STATES,
    InvalidTransition,
    JobState,
    assert_transition,
    can_transition,
    is_terminal,
    next_state_for_decision,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "DECISION_ROUTES",
    "TERMINAL_STATES",
    "InvalidTransition",
    "JobState",
    "assert_transition",
    "can_transition",
    "is_terminal",
    "next_state_for_decision",
]
