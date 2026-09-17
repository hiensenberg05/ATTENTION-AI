"""The automation job state machine: state definitions and legal transitions.

DEFINITIONS ONLY. There is no runner, no orchestrator loop and no LLM call here -
later layers will drive transitions; this module just says which states exist and
which moves between them are legal, so that illegal moves fail loudly.

THE CENTRAL RULE: STATE != DECISION.
    state    = where the job is in the pipeline  (JobState, this module)
    decision = what the policy concluded         (DecisionType, models.common)
A job can be in state EXECUTING while carrying decision APPROVE. They are two
independent axes and are never collapsed into one enum.

Naming: the conceptual diagram uses verb-phrase node names; the enum uses the
canonical state names. The mapping is:

    diagram node       JobState
    ----------------   --------------
    START              START
    LOAD_REQUEST       LOADING
    VALIDATE_REQUEST   VALIDATING
    ANALYZE            ANALYZING
    POLICY_CHECK       POLICY_CHECK
    HUMAN_REVIEW       HUMAN_REVIEW
    EXECUTE            EXECUTING
    VERIFY             VERIFYING
    COMPLETED          COMPLETED
    FAILED             FAILED

The diagram's VERIFIED/FAILED fork under VERIFY is NOT a job state - it is the
`verification_status` field on ExecutionResult. A verified job moves VERIFYING ->
COMPLETED; an unverified one moves VERIFYING -> FAILED.
"""

from __future__ import annotations

from enum import Enum

from models.common import DecisionType


class JobState(str, Enum):
    """Where an automation job currently is in the pipeline."""

    START = "START"
    LOADING = "LOADING"
    VALIDATING = "VALIDATING"
    ANALYZING = "ANALYZING"
    POLICY_CHECK = "POLICY_CHECK"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_STATES: frozenset[JobState] = frozenset({JobState.COMPLETED, JobState.FAILED})

#: Legal moves. Every state can move to FAILED (an unrecoverable error can happen
#: at any step); terminal states move nowhere.
ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.START: frozenset({JobState.LOADING, JobState.FAILED}),
    JobState.LOADING: frozenset({JobState.VALIDATING, JobState.FAILED}),
    # A record that is merely INCOMPLETE goes to human review, not to FAILED.
    # FAILED is for records that cannot be processed at all (e.g. unreadable).
    JobState.VALIDATING: frozenset(
        {JobState.ANALYZING, JobState.HUMAN_REVIEW, JobState.FAILED}
    ),
    JobState.ANALYZING: frozenset({JobState.POLICY_CHECK, JobState.FAILED}),
    # POLICY_CHECK routes by DECISION - see DECISION_ROUTES below.
    JobState.POLICY_CHECK: frozenset(
        {JobState.EXECUTING, JobState.HUMAN_REVIEW, JobState.FAILED}
    ),
    # OPEN DESIGN QUESTION (deliberately left open at foundation level):
    # after a human decides in the review queue, does the platform still perform
    # the browser action (HUMAN_REVIEW -> EXECUTING), or did the human already act
    # in the real system and we only record the outcome (HUMAN_REVIEW -> COMPLETED)?
    # Both moves are legal here so the foundation does not silently pick one.
    JobState.HUMAN_REVIEW: frozenset(
        {JobState.EXECUTING, JobState.COMPLETED, JobState.FAILED}
    ),
    JobState.EXECUTING: frozenset({JobState.VERIFYING, JobState.FAILED}),
    JobState.VERIFYING: frozenset({JobState.COMPLETED, JobState.FAILED}),
    JobState.COMPLETED: frozenset(),
    JobState.FAILED: frozenset(),
}

#: Where POLICY_CHECK sends a job, given the decision it produced.
#: Note both APPROVE and REJECT route to EXECUTING - the decision travels with the
#: job and tells the executor WHICH action to perform.
DECISION_ROUTES: dict[DecisionType, JobState] = {
    DecisionType.APPROVE: JobState.EXECUTING,
    DecisionType.REJECT: JobState.EXECUTING,
    DecisionType.REVIEW: JobState.HUMAN_REVIEW,
}


class InvalidTransition(ValueError):
    """Raised when code attempts a move the state machine does not allow."""


def can_transition(current: JobState, target: JobState) -> bool:
    """Is moving from `current` to `target` legal?"""
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: JobState, target: JobState) -> None:
    """Raise InvalidTransition unless the move is legal."""
    if not can_transition(current, target):
        allowed = sorted(s.value for s in ALLOWED_TRANSITIONS[current])
        raise InvalidTransition(
            f"{current.value} -> {target.value} is not allowed. "
            f"Allowed from {current.value}: {allowed or ['(terminal)']}"
        )


def is_terminal(state: JobState) -> bool:
    """Has the job finished, successfully or not?"""
    return state in TERMINAL_STATES


def next_state_for_decision(decision: DecisionType) -> JobState:
    """Which state POLICY_CHECK routes to for a given decision."""
    return DECISION_ROUTES[decision]
