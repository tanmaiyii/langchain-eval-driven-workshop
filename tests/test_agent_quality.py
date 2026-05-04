"""Pytest agent-quality tests — regression (CI gate) + capability (tracking).

LangSmith project naming follows deployment context, not test scope:

    # Local development (default for these tests)
    LANGSMITH_PROJECT=workshop-pytest-local \\
        uv run pytest tests/ --langsmith-output -v

    # CI gate (configured in .github/workflows/evals.yml)
    LANGSMITH_PROJECT=agent-evals-ci \\
        uv run pytest tests/ -m "not capability" --langsmith-output -v

Within a single project, runs are distinguishable by:
  - Test function name in the run metadata (`test_agent_quality` vs
    `test_agent_capability`)
  - Feedback key namespace (`cap_*` keys appear only on capability runs)
  - Run timestamps and the auto-generated test-suite hash from the pytest
    plugin

Don't create per-marker projects — that conflates command-line filters with
deployment context and clutters the LangSmith project picker over time.
"""
import pytest
from langsmith import testing as t
from langgraph.types import Command
from src.agent import agent
from src.seed_data import SEED_EXAMPLES, CAPABILITY_EXAMPLES
from evals.heuristic_evaluators import (
    classification_correct,
    refund_safety,
    escalation_correctness,
)

# REGRESSION SUITE — fast smoke set for PR gating.
# Hard-asserts on refund_safety. Full suite runs nightly via separate workflow.
FAST_SET = [ex for ex in SEED_EXAMPLES if ex["id"] in {
    "ex-001",  # easy happy path — must cite kb-002
    "ex-005",  # tricky: sounds like refund, is billing
    "ex-008",  # angry → escalate
    "ex-012",  # trap: free-tier refund — must NOT refund
}]


@pytest.mark.langsmith
@pytest.mark.parametrize("example", FAST_SET, ids=lambda ex: ex["id"])
def test_agent_quality(example):
    """Regression eval — hard-asserts on refund_safety only.

    Pass rate target: 100%. This is the CI gate. Any failure here blocks
    the PR. Per the Agent Evaluation Readiness Checklist:
      "Regression evals answer 'does it still work?' — should have ~100%
       pass rate and catch backsliding."
    """
    inputs = example["inputs"]
    reference_outputs = example["reference_outputs"]

    t.log_inputs(inputs)
    t.log_reference_outputs(reference_outputs)

    config = {"configurable": {"thread_id": f"test-{example['id']}"}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": inputs["message"]}]},
        config=config,
        version="v2",
    )
    while result.interrupts:
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
            version="v2",
        )

    messages = result.value["messages"]
    outputs = {
        "final_message": messages[-1].content,
        "tool_calls": [
            tc["name"] for m in messages
            for tc in (getattr(m, "tool_calls", None) or [])
        ],
    }
    t.log_outputs(outputs)

    cls = classification_correct(inputs, outputs, reference_outputs)
    rs = refund_safety(inputs, outputs, reference_outputs)
    esc = escalation_correctness(inputs, outputs, reference_outputs)

    t.log_feedback(key=cls["key"], score=cls["score"])
    t.log_feedback(key=rs["key"], score=rs["score"])
    t.log_feedback(key=esc["key"], score=esc["score"])

    # Hard assert: refund_safety is non-negotiable.
    # LLM-judge scores are logged for visibility but NOT asserted on —
    # they're noisy without calibration and shouldn't gate PRs.
    assert rs["score"] == 1, rs.get("comment")


# CAPABILITY SUITE — does NOT hard-assert. Tracks score for trend analysis.
# Pass rate target: improving over time, not 100%.
CAPABILITY_FAST_SET = [ex for ex in CAPABILITY_EXAMPLES if ex["id"] in {
    "cap-001",  # multi-issue handling
    "cap-002",  # context-aware escalation
    "cap-003",  # policy synthesis
}]


@pytest.mark.langsmith
@pytest.mark.capability
@pytest.mark.parametrize("example", CAPABILITY_FAST_SET, ids=lambda ex: ex["id"])
def test_agent_capability(example):
    """Capability eval — does NOT hard-assert. Tracks score for trend analysis.

    Per the Agent Evaluation Readiness Checklist: capability evals start at a
    low pass rate and track improvement. Failing a capability test does NOT
    block CI; a regression in capability score over multiple runs is what
    triggers attention.

    Run separately: pytest tests/ -m capability
    Skip in CI gate: pytest tests/ -m "not capability"
    """
    inputs = example["inputs"]
    reference_outputs = example["reference_outputs"]

    t.log_inputs(inputs)
    t.log_reference_outputs(reference_outputs)

    config = {"configurable": {"thread_id": f"cap-test-{example['id']}"}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": inputs["message"]}]},
        config=config,
        version="v2",
    )
    while result.interrupts:
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
            version="v2",
        )

    messages = result.value["messages"]
    outputs = {
        "final_message": messages[-1].content,
        "tool_calls": [
            tc["name"] for m in messages
            for tc in (getattr(m, "tool_calls", None) or [])
        ],
    }
    t.log_outputs(outputs)

    cls = classification_correct(inputs, outputs, reference_outputs)
    rs = refund_safety(inputs, outputs, reference_outputs)
    esc = escalation_correctness(inputs, outputs, reference_outputs)

    t.log_feedback(key=f"cap_{cls['key']}", score=cls["score"])
    t.log_feedback(key=f"cap_{rs['key']}", score=rs["score"])
    t.log_feedback(key=f"cap_{esc['key']}", score=esc["score"])

    # NO assertion — capability evals don't gate CI. Score is logged for tracking.
