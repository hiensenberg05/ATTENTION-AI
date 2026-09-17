"""Payroll Confirmation: policy gates, guards, and real-browser end-to-end runs.

These cover the second workflow, and - just as importantly - they check that
adding it did not require a second architecture. Several assertions below exist
only to prove the shared pieces really are shared: the same guard invariants, the
same state machine, the same audit trail, the same executor.
"""

from __future__ import annotations

import socket
import threading
import time
from decimal import Decimal

import pytest
import uvicorn

import orchestrator
import repository
from agent.guards import enforce
from agent.policy_engine import evaluate_payroll_item
from agent.schemas import LlmDecisionDraft
from execution import ActionNotAutoExecutable, PayrollConfirmationExecutor, execute_decision
from models.common import AmbiguityType, DecisionType, PayrollStatus, WorkflowType
from models.execution import ExecutionAction, VerificationStatus
from mockhr import payroll_store
from state.machine import JobState
from workflows.registry import REGISTRY, binding_for


@pytest.fixture(autouse=True)
def clean_demo():
    orchestrator.reset_demo()
    yield
    orchestrator.reset_demo()


@pytest.fixture(scope="module")
def policy() -> dict:
    return repository.get_policy("payroll_confirmation")


def item(record_id: str):
    return repository.get_payroll_item(record_id)


def gate(evaluation, check_id):
    return next(c for c in evaluation.checks if c.check_id == check_id)


# -- the registry is what makes this a platform ------------------------------


def test_both_workflows_are_registered():
    assert set(REGISTRY) == {
        WorkflowType.LEAVE_APPROVAL,
        WorkflowType.PAYROLL_CONFIRMATION,
    }


def test_payroll_reuses_the_shared_pieces():
    """Payroll must not have grown its own state machine or its own guard rules."""
    binding = binding_for(WorkflowType.PAYROLL_CONFIRMATION)
    definition = binding.definition
    assert definition.implemented is True
    # Same JobStates as leave - no workflow-specific states were invented.
    leave_states = {s.state for s in binding_for(WorkflowType.LEAVE_APPROVAL).definition.steps}
    assert {s.state for s in definition.steps} == leave_states


# -- policy gates ------------------------------------------------------------


def test_clean_item_passes_every_gate(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-001"), policy)
    assert all(c.passed is True for c in ev.checks)
    assert ev.decision is DecisionType.APPROVE


def test_the_observed_record_auto_confirms(policy):
    """The one screenshot-confirmed item must reproduce the action a human took.

    A prototype limit below 25,213 would make the agent escalate an item an
    operator was directly observed confirming, contradicting the only evidence
    available. The limit is deliberately set above it.
    """
    record = item("P1-07046967-001")
    assert record.provenance.value == "dataset_b_observed"
    assert record.amount == Decimal("25213")
    ev = evaluate_payroll_item(record, policy)
    assert ev.decision is DecisionType.APPROVE
    assert Decimal(str(policy["auto_approval_amount_limit"])) >= record.amount


def test_amount_over_the_prototype_limit_escalates(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-REVIEW"), policy)
    assert gate(ev, "amount_within_limit").passed is False
    assert ev.decision is DecisionType.REVIEW


def test_missing_policy_reference_is_not_evaluable_rather_than_failed(policy):
    """Payroll's equivalent of leave's unknown prior-approval field."""
    ev = evaluate_payroll_item(item("DEMO-PAY-NOREF"), policy)
    assert gate(ev, "policy_reference_present").passed is None
    assert ev.decision is DecisionType.REVIEW
    assert ev.ambiguity_type is AmbiguityType.MISSING_REQUIRED_DATA


def test_unrecognised_category_escalates(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-CATEGORY"), policy)
    assert gate(ev, "category_allowed").passed is False
    assert ev.ambiguity_type is AmbiguityType.POLICY_NOT_COVERED


def test_missing_required_field_escalates(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-INCOMPLETE"), policy)
    check = gate(ev, "required_fields_present")
    assert check.passed is False
    assert "employee_id" in check.detail
    assert ev.ambiguity_type is AmbiguityType.MISSING_REQUIRED_DATA


def test_already_processed_item_is_not_actionable(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-DONE"), policy)
    assert gate(ev, "status_actionable").passed is False


def test_salary_structure_categories_are_excluded(policy):
    """List-observed items change standing pay and were never seen confirmed."""
    for record_id in ("P4-07046967-009", "P4-07046967-012"):
        ev = evaluate_payroll_item(item(record_id), policy)
        assert ev.decision is DecisionType.REVIEW, record_id


def test_the_policy_engine_can_never_produce_a_hold(policy):
    for record in repository.get_payroll_items():
        assert evaluate_payroll_item(record, policy).decision is not DecisionType.REJECT


# -- guards: identical invariants, no workflow knowledge ---------------------


def draft(decision: DecisionType, confidence: float = 0.95) -> LlmDecisionDraft:
    return LlmDecisionDraft(
        decision=decision,
        reason="model reasoning",
        confidence=confidence,
        human_review_required=decision is DecisionType.REVIEW,
    )


def test_the_model_cannot_confirm_an_item_the_policy_escalated(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-REVIEW"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.99), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.human_review_required is True


def test_a_hold_is_always_converted_to_review(policy):
    """allow_auto_hold is false, so REJECT must never survive the guard."""
    ev = evaluate_payroll_item(item("DEMO-PAY-001"), policy)
    out = enforce(draft(DecisionType.REJECT, 0.99), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.ambiguity_type is AmbiguityType.ACTION_NOT_AUTO_EXECUTABLE


def test_low_confidence_confirmation_is_escalated(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-001"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.3), ev, "test")
    assert out.decision is DecisionType.REVIEW
    assert out.ambiguity_type is AmbiguityType.LOW_CONFIDENCE


def test_every_payroll_record_survives_a_hostile_model(policy):
    for record in repository.get_payroll_items():
        ev = evaluate_payroll_item(record, policy)
        out = enforce(draft(DecisionType.APPROVE, 1.0), ev, "test")
        if ev.decision is not DecisionType.APPROVE:
            assert out.decision is DecisionType.REVIEW, record.record_id
        assert out.decision is not DecisionType.REJECT


def test_the_audit_trail_is_the_deterministic_one(policy):
    ev = evaluate_payroll_item(item("DEMO-PAY-CATEGORY"), policy)
    out = enforce(draft(DecisionType.APPROVE, 0.99), ev, "test")
    assert [c.check_id for c in out.policy_checks] == [c.check_id for c in ev.checks]
    assert out.policy_version == policy["policy_version"]


# -- orchestration without a browser ----------------------------------------


def test_escalated_payroll_job_never_reaches_the_browser():
    job = orchestrator.start_payroll_job("DEMO-PAY-REVIEW")
    assert job.state is JobState.HUMAN_REVIEW
    assert job.execution is None
    assert payroll_store.get("DEMO-PAY-REVIEW").status is PayrollStatus.UNPROCESSED


def test_payroll_state_history_matches_leave():
    job = orchestrator.start_payroll_job("DEMO-PAY-REVIEW")
    path = [job.state_history[0].from_state] + [t.to_state for t in job.state_history]
    assert path == [
        JobState.START,
        JobState.LOADING,
        JobState.VALIDATING,
        JobState.ANALYZING,
        JobState.POLICY_CHECK,
        JobState.HUMAN_REVIEW,
    ]


def test_hold_is_never_auto_executable():
    workflow = binding_for(WorkflowType.PAYROLL_CONFIRMATION).definition
    with pytest.raises(ActionNotAutoExecutable):
        execute_decision(item("DEMO-PAY-001"), DecisionType.REJECT, workflow)


def test_review_is_not_an_executable_action():
    workflow = binding_for(WorkflowType.PAYROLL_CONFIRMATION).definition
    with pytest.raises(ActionNotAutoExecutable):
        execute_decision(item("DEMO-PAY-001"), DecisionType.REVIEW, workflow)


def test_unknown_record_raises_rather_than_inventing_a_job():
    with pytest.raises(orchestrator.RecordNotFound):
        orchestrator.start_payroll_job("NO-SUCH-PAYROLL-ITEM")


def test_the_audit_trail_holds_both_workflows():
    orchestrator.start_payroll_job("DEMO-PAY-REVIEW", run_execution=False)
    orchestrator.start_leave_job("P2-07048822-006", run_execution=False)
    workflows = {j.workflow for j in orchestrator.jobs.all()}
    assert workflows == {WorkflowType.PAYROLL_CONFIRMATION, WorkflowType.LEAVE_APPROVAL}


# -- real browser ------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
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
    monkeypatch.setenv("MOCK_HR_BASE_URL", live_server)
    return live_server


@pytest.fixture
def executor(live_server):
    with PayrollConfirmationExecutor(base_url=live_server, headless=True) as ex:
        yield ex


def test_executor_reads_the_payroll_fields_off_the_screen(executor):
    executor.open_item("P1-07046967-001")
    details = executor.get_item_details()
    assert details["record_id"] == "P1-07046967-001"
    assert details["employee_id"] == "E2011"
    assert details["category"] == "研修費"
    assert "25,213" in details["amount"]
    assert details["status"] == PayrollStatus.UNPROCESSED.value
    assert "承認権限" in details["policy_reference"]


def test_executor_refuses_a_record_that_does_not_exist(executor):
    with pytest.raises(Exception):
        executor.open_item("NO-SUCH-PAYROLL-ITEM")


def test_executor_refuses_an_action_with_no_control(executor):
    """A leave action has no control on the payroll screen; it must not improvise."""
    executor.open_item("DEMO-PAY-001")
    with pytest.raises(Exception):
        executor.perform(ExecutionAction.APPROVE_LEAVE)


def test_confirmation_is_independently_visible_on_the_queue(executor):
    assert executor.get_current_status("DEMO-PAY-002") == PayrollStatus.UNPROCESSED.value
    executor.open_item("DEMO-PAY-002")
    executor.confirm_item("confirmed by test")
    # Read back from the LIST screen, not the page that submitted the action.
    assert executor.get_current_status("DEMO-PAY-002") == PayrollStatus.CONFIRMED.value


def test_full_payroll_run_completes_and_verifies(hr_url):
    job = orchestrator.start_payroll_job("DEMO-PAY-001")
    assert job.state is JobState.COMPLETED
    assert job.decision.decision is DecisionType.APPROVE
    assert job.execution.action is ExecutionAction.CONFIRM_PAYROLL
    assert job.execution.verification_status is VerificationStatus.VERIFIED
    assert job.execution.status_before == PayrollStatus.UNPROCESSED.value
    assert job.execution.status_after == PayrollStatus.CONFIRMED.value
    assert job.execution.duration_seconds > 0
    assert payroll_store.get("DEMO-PAY-001").status is PayrollStatus.CONFIRMED


def test_observed_record_runs_end_to_end(hr_url):
    """The strongest demo in the prototype: a real Dataset B record, really acted on."""
    job = orchestrator.start_payroll_job("P1-07046967-001")
    assert job.state is JobState.COMPLETED
    assert job.execution.verification_status is VerificationStatus.VERIFIED
    assert payroll_store.get("P1-07046967-001").status is PayrollStatus.CONFIRMED


def test_human_authorised_hold_reaches_the_browser(hr_url):
    job = orchestrator.start_payroll_job("DEMO-PAY-REVIEW")
    assert job.state is JobState.HUMAN_REVIEW

    resolved = orchestrator.submit_human_decision(
        job.job_id,
        DecisionType.REJECT,
        operator="ops.test",
        note="Above the delegated authority; holding for sign-off.",
    )
    assert resolved.state is JobState.COMPLETED
    assert resolved.execution.action is ExecutionAction.HOLD_PAYROLL
    assert resolved.execution.verification_status is VerificationStatus.VERIFIED
    assert resolved.execution.status_after == PayrollStatus.ON_HOLD.value
    assert resolved.execution.executed_by == "human:ops.test"
    # The agent's REVIEW survives alongside the human's determination.
    assert resolved.decision.decision is DecisionType.REVIEW
    assert resolved.human_decision.decision is DecisionType.REJECT


def test_replay_guard_on_an_already_confirmed_item(hr_url):
    first = orchestrator.start_payroll_job("DEMO-PAY-003")
    assert first.state is JobState.COMPLETED

    second = orchestrator.start_payroll_job("DEMO-PAY-003")
    assert second.state is JobState.HUMAN_REVIEW
    assert second.execution is None
    status_gate = next(
        c for c in second.decision.policy_checks if c.check_id == "status_actionable"
    )
    assert status_gate.passed is False


def test_both_workflows_run_against_the_same_browser_machinery(hr_url):
    leave = orchestrator.start_leave_job("DEMO-LV-001")
    payroll = orchestrator.start_payroll_job("DEMO-PAY-001")
    assert leave.state is JobState.COMPLETED
    assert payroll.state is JobState.COMPLETED
    assert leave.execution.action is ExecutionAction.APPROVE_LEAVE
    assert payroll.execution.action is ExecutionAction.CONFIRM_PAYROLL
