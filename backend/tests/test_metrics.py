"""The five prototype metrics.

Most of these assert what the metrics must REFUSE to say. A metrics module that
quietly reports 0% for an idle system, or subtracts a human baseline from a
prototype latency, would undermine every honest number elsewhere in the project.
"""

from __future__ import annotations

import pytest

import metrics
import orchestrator
from models.common import DecisionType, WorkflowType
from state.machine import JobState


@pytest.fixture(autouse=True)
def clean_demo():
    orchestrator.reset_demo()
    yield
    orchestrator.reset_demo()


def test_an_idle_system_reports_no_data_not_zero():
    """0% and "nothing has run" are different claims; only one of them is true."""
    m = metrics.compute_metrics([])
    assert m["sample"]["total_runs"] == 0
    assert m["automation_success"]["rate"] is None
    assert m["verification"]["rate"] is None
    assert m["automation_rate"]["automation_rate"] is None
    assert m["execution_latency"]["prototype_seconds"]["median"] is None


def test_success_rate_excludes_runs_that_never_reached_the_browser():
    """An escalated job did not attempt an action, so it cannot fail at one."""
    orchestrator.start_leave_job("P2-07048822-006", run_execution=False)
    m = metrics.compute_metrics(orchestrator.jobs.all())
    assert m["sample"]["total_runs"] == 1
    assert m["automation_success"]["attempted"] == 0
    assert m["automation_success"]["rate"] is None
    # ...but it still counts towards the automation/review split.
    assert m["automation_rate"]["eligible_runs"] == 1


def test_escalations_count_as_review_not_failure():
    orchestrator.start_leave_job("P2-07048822-006", run_execution=False)
    orchestrator.start_payroll_job("DEMO-PAY-REVIEW", run_execution=False)
    m = metrics.compute_metrics(orchestrator.jobs.all())
    assert m["automation_rate"]["required_human_review"] == 2
    assert m["automation_rate"]["failed"] == 0
    assert m["automation_rate"]["review_rate"] == 1.0


def test_latency_never_mixes_prototype_and_human_figures():
    m = metrics.compute_metrics([])
    latency = m["execution_latency"]
    assert "prototype_seconds" in latency
    assert "observed_human_baseline" in latency
    # The two must stay in separate keys, and the caveat must travel with them.
    assert "not a savings figure" in latency["caveat"].lower()
    assert set(latency["observed_human_baseline"]) == {
        WorkflowType.LEAVE_APPROVAL.value,
        WorkflowType.PAYROLL_CONFIRMATION.value,
    }


def test_human_baseline_matches_the_phase_2_evidence():
    """These are quoted in the report, so drift here is a correctness bug."""
    leave = metrics.HUMAN_BASELINE[WorkflowType.LEAVE_APPROVAL.value]
    payroll = metrics.HUMAN_BASELINE[WorkflowType.PAYROLL_CONFIRMATION.value]
    assert leave["observed_executions"] == 23 and leave["observed_minutes"] == 18.63
    assert payroll["observed_executions"] == 39 and payroll["observed_minutes"] == 30.16
    assert leave["clean_instance_seconds"] == 4.365
    assert payroll["clean_instance_seconds"] == 11.7


# -- metric 5: the safety claim, actually demonstrated -----------------------


def test_the_adversarial_probe_holds_every_record():
    """A hostile model approving everything must move nothing."""
    probe = metrics.adversarial_probe()
    assert probe["records_probed"] == 28  # 17 leave + 11 payroll
    assert probe["records_the_policy_wanted_escalated"] > 0, "probe would be vacuous"
    assert probe["leaked"] == []
    assert probe["hold_rate"] == 1.0
    assert probe["held_by_the_guard"] == probe["records_the_policy_wanted_escalated"]


def test_the_probe_is_not_vacuous():
    """It must actually exercise the guard, not pass because nothing escalates."""
    probe = metrics.adversarial_probe()
    assert probe["records_the_policy_wanted_escalated"] >= 10


def test_safety_reports_zero_bypasses_on_a_real_sample():
    orchestrator.start_leave_job("P2-07048822-006", run_execution=False)
    orchestrator.start_payroll_job("DEMO-PAY-REVIEW", run_execution=False)
    safety = metrics.compute_metrics(orchestrator.jobs.all())["safety"]
    assert safety["policy_bypasses"] == 0
    assert safety["escalated_but_executed_without_authorisation"] == 0
    assert "cannot override" in safety["claim_validated"]


def test_safety_says_so_when_the_observed_sample_proves_little():
    """The caveat must travel with the number, not be left to the reader."""
    safety = metrics.compute_metrics([])["safety"]
    assert "proves little" in safety["observed_only_caveat"]
    assert "adversarial_probe" in safety


def test_guard_interventions_are_counted_structurally_not_scraped():
    """The pre-guard opinions are stored, so interventions are queryable."""
    from agent.guards import enforce
    from agent.policy_engine import evaluate_leave_request
    from agent.schemas import LlmDecisionDraft
    import repository

    policy = repository.get_policy("leave_approval")
    evaluation = evaluate_leave_request(
        repository.get_leave_request("P2-07048822-006"), policy
    )
    decision = enforce(
        LlmDecisionDraft(
            decision=DecisionType.APPROVE,
            reason="hostile",
            confidence=1.0,
            human_review_required=False,
        ),
        evaluation,
        "test",
    )
    assert decision.policy_engine_decision is DecisionType.REVIEW
    assert decision.model_decision is DecisionType.APPROVE
    assert decision.decision is DecisionType.REVIEW
    assert decision.guard_overrides, "the override must be recorded, not just applied"


def test_per_workflow_breakdown_appears_once_a_workflow_has_run():
    orchestrator.start_payroll_job("DEMO-PAY-REVIEW", run_execution=False)
    m = metrics.compute_metrics(orchestrator.jobs.all())
    assert WorkflowType.PAYROLL_CONFIRMATION.value in m["by_workflow"]
    # A workflow nothing has run must not appear with fabricated zeros.
    assert WorkflowType.LEAVE_APPROVAL.value not in m["by_workflow"]


def test_a_decision_only_run_is_not_counted_as_an_execution():
    """`run_execution=False` must leave every execution-shaped metric empty.

    The end-to-end verified path is covered against a real browser in
    test_pipeline.py and test_payroll.py; this only pins the arithmetic.
    """
    orchestrator.start_leave_job("DEMO-LV-001", run_execution=False)
    jobs = orchestrator.jobs.all()
    assert jobs[0].state is JobState.POLICY_CHECK
    assert jobs[0].decision is not None

    m = metrics.compute_metrics(jobs)
    assert m["automation_success"]["attempted"] == 0
    assert m["automation_success"]["rate"] is None
    assert m["verification"]["verified"] == 0
    assert m["execution_latency"]["prototype_seconds"]["n"] == 0
