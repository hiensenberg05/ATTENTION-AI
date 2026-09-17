"""The PydanticAI + Groq decision agent.

WHAT THE MODEL DOES: reads one already-structured business record together with an
already-evaluated policy gate table, and returns a decision, a justification and a
confidence, as the `LlmDecisionDraft` schema.

WHAT THE MODEL DOES NOT DO - and cannot, structurally:
  * it never sees a browser, a URL, a selector or a page;
  * it has no tools, so it cannot call anything;
  * it does not choose which button to click, or whether to click at all;
  * it does not author the policy check results (Python does, before the call);
  * it cannot de-escalate - `guards.enforce` takes the more conservative of its
    draft and the deterministic evaluation.

The model is the judgement-and-explanation layer of a system whose control flow is
entirely Python. If the model is unavailable, `decide_leave_request` falls back to
the deterministic evaluation and says so in `AgentDecision.decided_by`; the
pipeline keeps working, it just stops having a narrator.

API KEY: read from the `GROQ_API_KEY` environment variable (loaded from the repo
root `.env` if present). It is never hardcoded, never logged and never returned by
any endpoint.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from models.agent import AgentDecision
from models.common import DecisionType
from models.leave import LeaveRequest

from .guards import enforce
from .policy_engine import PolicyEvaluation, evaluate_leave_request
from .schemas import LlmDecisionDraft

logger = logging.getLogger(__name__)

# PydanticAI prints a startup banner to stdout on first agent construction, which
# corrupts uvicorn's log stream and any piped output. Suppress it unless the
# operator has deliberately set the variable themselves.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

#: Small, fast Groq-hosted model. Named here only; the key comes from the env.
MODEL_NAME = "openai/gpt-oss-20b"

#: Repo root is one level above `backend/`.
REPO_ROOT = Path(__file__).resolve().parents[2]

DECIDED_BY_LLM = "llm+policy_guard"
DECIDED_BY_FALLBACK = "policy_engine_fallback"

SYSTEM_PROMPT = """\
You are the decision layer of a back-office automation system for a Japanese HR \
application. You evaluate one leave/attendance request at a time.

YOUR ROLE
You are given (a) a business record that has already been read and structured for \
you, (b) an explicit written policy, and (c) the result of that policy's gates, \
already evaluated deterministically in code. You decide what should happen to the \
record and explain why.

YOU DO NOT CONTROL ANYTHING
You have no tools. You cannot open, navigate, click or read a web page. You do not \
choose UI elements, selectors, or actions. A separate deterministic component \
performs any resulting action. Never describe clicking, navigating, or operating \
software; describe only the business decision.

HOW TO DECIDE
- APPROVE only when every policy gate passed (passed = true). One gate that failed \
or could not be evaluated is enough to stop an approval.
- REVIEW whenever a gate failed, a gate could not be evaluated, a required field is \
unknown, or the policy simply does not cover the case.
- A gate whose result is "not evaluable" is NOT a soft pass and NOT a failure. It \
means a fact is genuinely unknown. Unknown facts must never be assumed in either \
direction - they escalate to a human.
- REJECT is almost never correct here. This deployment has automatic rejection \
disabled, so a record that looks rejectable must go to REVIEW instead.

CONFIDENCE
Report your genuine confidence. Use a value at or above the policy's stated minimum \
only when every gate was evaluated and passed cleanly. Anything unknown, contested \
or unusual belongs below it.

REASON
Two or three sentences of plain English for an operations reviewer. Name the \
specific gates and record fields that drove the outcome. Do not restate the whole \
policy, do not invent business rules that are not in the policy given to you, and \
do not claim the policy came from observing real operators - it is an explicit \
prototype policy written by hand."""


def _load_api_key() -> Optional[str]:
    """Read GROQ_API_KEY from the environment, loading the repo-root .env first.

    `load_dotenv` does not overwrite variables already set, so a real environment
    variable always wins over the file.
    """
    load_dotenv(REPO_ROOT / ".env")
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key or None


_agent_cache: dict[str, Any] = {}


def _get_agent() -> Optional[Any]:
    """Build (once) the PydanticAI agent, or return None if no key is configured."""
    if "agent" in _agent_cache:
        return _agent_cache["agent"]

    api_key = _load_api_key()
    if not api_key:
        logger.warning(
            "GROQ_API_KEY is not set; the decision layer will run deterministically."
        )
        _agent_cache["agent"] = None
        return None

    # Imported lazily so the whole backend still starts if the optional agent
    # dependencies are not installed.
    from pydantic_ai import Agent
    from pydantic_ai.models.groq import GroqModel
    from pydantic_ai.providers.groq import GroqProvider

    model = GroqModel(MODEL_NAME, provider=GroqProvider(api_key=api_key))
    agent = Agent(
        model,
        output_type=LlmDecisionDraft,
        system_prompt=SYSTEM_PROMPT,
        # No `tools=` argument. The model has no way to act on anything.
        retries=2,
        model_settings={"temperature": 0.0, "groq_reasoning_effort": "low"},
    )
    _agent_cache["agent"] = agent
    return agent


def _record_payload(record: LeaveRequest) -> dict[str, Any]:
    """The record as the model sees it: values plus an explicit unknown marker.

    Serialising `None` as the string "UNKNOWN (not recorded)" matters. A bare null
    in JSON reads to a model like an empty optional; spelling it out keeps the
    three-valued logic visible in the prompt.
    """

    def show(value: Any) -> Any:
        if value is None:
            return "UNKNOWN (not recorded)"
        return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        "record_id": record.record_id,
        "status": record.status.value,
        "employee_id": show(record.employee_id),
        "employee_name": show(record.employee_name),
        "request_type": show(record.request_type),
        "request_date": show(record.request_date),
        "department": show(record.department),
        "prior_approval_required": show(record.prior_approval_required),
        "prior_approval_obtained": show(record.prior_approval_obtained),
        "comment": show(record.comment),
        "data_provenance": record.provenance.value,
    }


def _build_prompt(
    record: LeaveRequest, policy: dict[str, Any], evaluation: PolicyEvaluation
) -> str:
    """Assemble the user message: record, policy, and the pre-evaluated gates."""
    gates = [
        {
            "check_id": c.check_id,
            "rule": c.description,
            "result": (
                "PASSED"
                if c.passed is True
                else "FAILED"
                if c.passed is False
                else "NOT EVALUABLE (the fact this rule needs is unknown)"
            ),
            "detail": c.detail,
        }
        for c in evaluation.checks
    ]

    policy_for_model = {
        "policy_version": evaluation.policy_version,
        "actionable_statuses": policy.get("actionable_statuses"),
        "allowed_request_types": policy.get("allowed_request_types"),
        "required_fields": policy.get("required_fields"),
        "allow_auto_approval": evaluation.allow_auto_approval,
        "allow_auto_rejection": evaluation.allow_auto_rejection,
        "prior_approval_rule": policy.get("prior_approval_rule"),
        "min_confidence_for_auto_execution": evaluation.min_confidence,
    }

    return (
        "LEAVE REQUEST RECORD\n"
        f"{json.dumps(_record_payload(record), ensure_ascii=False, indent=2)}\n\n"
        "POLICY IN FORCE\n"
        f"{json.dumps(policy_for_model, ensure_ascii=False, indent=2)}\n\n"
        "POLICY GATES, ALREADY EVALUATED IN CODE\n"
        f"{json.dumps(gates, ensure_ascii=False, indent=2)}\n\n"
        "Decide what should happen to this record."
    )


def _fallback_draft(evaluation: PolicyEvaluation) -> LlmDecisionDraft:
    """The deterministic evaluation expressed as a draft, for when there is no model.

    Confidence is set to 1.0 for a clean APPROVE because the rules resolved it
    without any judgement being required, and to 0.5 for an escalation so that the
    low-confidence guard is not the thing doing the escalating.
    """
    approve = evaluation.decision is DecisionType.APPROVE
    return LlmDecisionDraft(
        decision=evaluation.decision,
        reason=(
            "Decided by the deterministic policy engine without a language model. "
            + evaluation.reason
        ),
        confidence=1.0 if approve else 0.5,
        human_review_required=not approve,
        ambiguity_type=evaluation.ambiguity_type,
    )


def decide_leave_request(
    record: LeaveRequest, policy: dict[str, Any]
) -> AgentDecision:
    """Evaluate one leave request and return the final, guarded decision.

    Order of operations, which is the whole design in four lines:
        1. Python evaluates the policy gates deterministically.
        2. The model drafts a decision from the record + gates.
        3. Python's guards merge the two, taking the more conservative outcome.
        4. The deterministic gate results become the decision's audit trail.

    A model failure is never fatal: it degrades to step 1's answer and records
    `decided_by='policy_engine_fallback'` so the UI can say so.
    """
    evaluation = evaluate_leave_request(record, policy)

    agent = _get_agent()
    if agent is None:
        return enforce(_fallback_draft(evaluation), evaluation, DECIDED_BY_FALLBACK)

    try:
        result = agent.run_sync(_build_prompt(record, policy, evaluation))
        draft = result.output
        decided_by = DECIDED_BY_LLM
    except Exception as exc:  # noqa: BLE001 - any model failure degrades the same way
        logger.warning(
            "Groq decision call failed for %s (%s: %s); falling back to the "
            "deterministic policy engine.",
            record.record_id,
            type(exc).__name__,
            exc,
        )
        draft = _fallback_draft(evaluation)
        decided_by = DECIDED_BY_FALLBACK

    return enforce(draft, evaluation, decided_by)


def agent_health() -> dict[str, Any]:
    """Is the LLM layer configured? Reports configuration only - never the key."""
    key = _load_api_key()
    try:
        import pydantic_ai

        library = pydantic_ai.__version__
    except Exception:  # noqa: BLE001
        library = None

    return {
        "llm_configured": bool(key) and library is not None,
        "model": MODEL_NAME,
        "provider": "groq",
        "api_key_present": bool(key),
        "pydantic_ai_version": library,
        "fallback": "deterministic policy engine",
    }
