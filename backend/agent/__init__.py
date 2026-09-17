"""The agent decision layer: explicit policy evaluation + a bounded LLM.

Three modules, in the order they run:

    policy_engine.py  deterministic evaluation of data/policies.json -> PolicyCheck[]
    decision_agent.py the PydanticAI/Groq call that produces a decision DRAFT
    guards.py         Python invariants that the draft cannot override

The LLM never touches a browser, never picks a selector, never decides an action,
and never writes the policy check results. It reads an already-structured record
and an already-evaluated rule table, and produces a decision, a justification and
a confidence. Everything it returns then passes through `guards.enforce`, which
can only ever make the outcome MORE conservative.
"""

from .policy_engine import PolicyEvaluation, evaluate_leave_request
from .guards import enforce
from .decision_agent import decide_leave_request, agent_health

__all__ = [
    "PolicyEvaluation",
    "evaluate_leave_request",
    "enforce",
    "decide_leave_request",
    "agent_health",
]
