"""End-to-end tests: the state machine, the mock HR system, and a real browser run.

The browser tests start a real uvicorn server in a background thread and drive a
real Chromium against it. They are the only place the prototype's central claim -
that the record actually changes, and that a second independent read proves it -
can be checked rather than asserted.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn

import orchestrator
import repository
from execution import ActionNotAutoExecutable, LeaveApprovalExecutor, execute_leave_decision
from models.common import DecisionType, LeaveStatus, WorkflowType
from models.execution import VerificationStatus
from mockhr import store as hr_store
from state.machine import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    JobState,
    assert_transition,
    next_state_for_decision,
)


@pytest.fixture(autouse=True)
def clean_demo():
    """Every test starts from the seed data and an empty job store."""
    orchestrator.reset_demo()
    yield
    orchestrator.reset_demo()


# -- state machine -----------------------------------------------------------


def test_decision_routing_is_a_table_not_a_model_output():
    assert next_state_for_decision(DecisionType.APPROVE) is JobState.EXECUTING
    assert next_state_for_decision(DecisionType.REJECT) is JobState.EXECUTING
    assert next_state_for_decision(DecisionType.REVIEW) is JobState.HUMAN_REVIEW


def test_illegal_transitions_raise():
    with pytest.raises(InvalidTransition):
        assert_transition(JobState.START, JobState.COMPLETED)
    with pytest.raises(InvalidTransition):
        assert_transition(JobState.COMPLETED, JobState.EXECUTING)


def test_every_non_terminal_state_can_fail():
    for state, targets in ALLOWED_TRANSITIONS.items():
        if state in (JobState.COMPLETED, JobState.FAILED):
            assert targets == frozenset()
        else:
            assert JobState.FAILED in targets, state


# -- the mock HR system ------------------------------------------------------


def test_action_changes_status_and_is_not_replayable():
    hr_store.apply_action("DEMO-LV-001", "approve", "ok")
    assert hr_store.get("DEMO-LV-001").status is LeaveStatus.APPROVED
    with pytest.raises(Exception):
        hr_store.apply_action("DEMO-LV-001", "approve")


def test_mutating_the_hr_system_never_corrupts_the_seed():
    hr_store.apply_action("DEMO-LV-001", "approve")
    assert repository.get_leave_request("DEMO-LV-001").status is LeaveStatus.PENDING


# -- orchestration without a browser ----------------------------------------


def test_escalated_job_stops_before_execution():
    job = orchestrator.start_leave_job("P2-07048822-006")
    assert job.state is JobState.HUMAN_REVIEW
    assert job.decision is not None
    assert job.decision.human_review_required is True
    assert job.execution is None, "an escalated job must never reach the browser"
    assert hr_store.get("P2-07048822-006").status is LeaveStatus.PENDING


def test_decision_only_run_touches_nothing():
    job = orchestrator.start_leave_job("DEMO-LV-001", run_execution=False)
    assert job.decision is not None
    assert job.execution is None
    assert hr_store.get("DEMO-LV-001").status is LeaveStatus.PENDING


def test_state_history_records_the_whole_path():
    job = orchestrator.start_leave_job("P2-07048822-006")
    path = [job.state_history[0].from_state] + [t.to_state for t in job.state_history]
    assert path == [
        JobState.START,
        JobState.LOADING,
        JobState.VALIDATING,
        JobState.ANALYZING,
        JobState.POLICY_CHECK,
        JobState.HUMAN_REVIEW,
    ]


def test_human_decision_is_refused_for_a_job_not_in_review():
    job = orchestrator.start_leave_job("DEMO-LV-001", run_execution=False)
    with pytest.raises(orchestrator.JobNotInReview):
        orchestrator.submit_human_decision(
            job.job_id, DecisionType.APPROVE, "op", "note", run_execution=False
        )


def test_state_and_decision_stay_independent():
    job = orchestrator.start_leave_job("P2-07048822-006")
    assert job.state is JobState.HUMAN_REVIEW
    resolved = orchestrator.submit_human_decision(
        job.job_id, DecisionType.APPROVE, "op", "checked", run_execution=False
    )
    # The agent's REVIEW is preserved; the human's APPROVE sits beside it.
    assert resolved.decision.decision is DecisionType.REVIEW
    assert resolved.human_decision.decision is DecisionType.APPROVE
    assert resolved.state is JobState.COMPLETED


def test_rejection_is_never_auto_executable():
    workflow = repository.get_workflow(WorkflowType.LEAVE_APPROVAL)
    with pytest.raises(ActionNotAutoExecutable):
        execute_leave_decision(
            repository.get_leave_request("DEMO-LV-001"), DecisionType.REJECT, workflow
        )


# -- real browser ------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """A real uvicorn server, so Playwright has something real to drive."""
    from main import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 30
    while not server.started and time.time() < deadline:
        time.sleep(0.1)
    if not server.started:
        pytest.fail("the test server did not start")

    yield f"http://127.0.0.1:{port}/mock-hr"

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def hr_url(live_server, monkeypatch):
    """Point the orchestrator's executor at the test server, via the environment.

    This is exactly how an operator retargets the executor in production, so the
    test configures it the same way rather than reaching inside the module.
    """
    monkeypatch.setenv("MOCK_HR_BASE_URL", live_server)
    return live_server


@pytest.fixture
def executor(live_server):
    with LeaveApprovalExecutor(base_url=live_server, headless=True) as ex:
        yield ex


def test_executor_reads_the_fields_off_the_screen(executor):
    executor.open_request("P2-07048822-006")
    details = executor.get_request_details()
    assert details["record_id"] == "P2-07048822-006"
    assert details["employee_id"] == "E2001"
    assert details["employee_name"] == "青木 拓也"
    assert details["request_type"] == "代休申請"
    assert details["status"] == LeaveStatus.PENDING.value


def test_executor_refuses_to_open_a_record_that_does_not_exist(executor):
    with pytest.raises(Exception):
        executor.open_request("NO-SUCH-RECORD")


def test_approval_changes_the_record_and_is_independently_visible(executor):
    assert executor.get_current_status("DEMO-LV-003") == LeaveStatus.PENDING.value
    executor.open_request("DEMO-LV-003")
    executor.approve_request("approved by test")
    # Read back from the LIST screen, not the page that submitted the action.
    assert executor.get_current_status("DEMO-LV-003") == LeaveStatus.APPROVED.value


def test_full_run_completes_and_verifies(hr_url):
    job = orchestrator.start_leave_job("DEMO-LV-004")
    assert job.state is JobState.COMPLETED
    assert job.decision.decision is DecisionType.APPROVE
    assert job.execution.success is True
    assert job.execution.verification_status is VerificationStatus.VERIFIED
    assert job.execution.status_before == LeaveStatus.PENDING.value
    assert job.execution.status_after == LeaveStatus.APPROVED.value
    assert job.execution.duration_seconds > 0
    assert hr_store.get("DEMO-LV-004").status is LeaveStatus.APPROVED


def test_human_authorised_rejection_reaches_the_browser(hr_url):
    job = orchestrator.start_leave_job("DEMO-LV-006")
    assert job.state is JobState.HUMAN_REVIEW

    resolved = orchestrator.submit_human_decision(
        job.job_id,
        DecisionType.REJECT,
        operator="ops.test",
        note="Wrong system for this request type.",
    )
    assert resolved.state is JobState.COMPLETED
    assert resolved.execution.verification_status is VerificationStatus.VERIFIED
    assert resolved.execution.status_after == LeaveStatus.RETURNED.value
    assert resolved.execution.executed_by == "human:ops.test"
    assert hr_store.get("DEMO-LV-006").status is LeaveStatus.RETURNED


def test_a_run_on_an_already_processed_record_does_not_silently_redo_it(hr_url):
    first = orchestrator.start_leave_job("DEMO-LV-002")
    assert first.state is JobState.COMPLETED

    second = orchestrator.start_leave_job("DEMO-LV-002")
    assert second.state is JobState.HUMAN_REVIEW
    assert second.execution is None
    statuses = [c.passed for c in second.decision.policy_checks]
    assert statuses[0] is False, "status_actionable should have failed"
