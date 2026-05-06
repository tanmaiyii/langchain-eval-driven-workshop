"""Run the v1/v2/v3 regression demo end-to-end.

Produces three experiments in LangSmith showing how removing the
"Never refund a free-tier customer" line from the system prompt causes
the agent to start refunding free-tier customers — refund_safety catches
the regression on ex-012, then v3 restores the line and the gate goes green.

This is the workshop's "wow moment" — LangSmith Compare view joins all
three experiments by example UUID for visual side-by-side comparison.

Usage:
    uv run python -m scripts.run_regression_demo
"""

import datetime

from langgraph.types import Command
from langsmith import evaluate

from src.agent import SYSTEM_PROMPT, build_agent
from evals.dataset import DATASET_NAME, upsert_dataset
from evals.heuristic_evaluators import (
    classification_correct,
    refund_safety,
    escalation_correctness,
)
from evals.llm_judge_evaluators import kb_grounding_judge
from evals.trajectory_evaluators import trajectory_superset


# Shared run identifier so the v1/v2/v3 trio is visibly grouped in LangSmith.
# Each invocation of this script gets a single timestamped run_id; all three
# experiments produced in this run share it, both in the experiment name
# (suffix) and in the metadata (filterable in the UI).
RUN_ID = datetime.datetime.now().strftime("%Y%m%d-%H%M")


EVALUATORS = [
    classification_correct,
    refund_safety,
    escalation_correctness,
    kb_grounding_judge,
    trajectory_superset,
]


# v1-baseline: original prompt — expect 100% pass on refund_safety
V1_PROMPT = SYSTEM_PROMPT

# v2-removed-guardrail: the "no free-tier refunds" policy is enforced in
# two prompt lines — the issue_refund rule under "Resolve via one of"
# (paid-plan constraint) and the "Never refund a free-tier customer"
# reminder. v2 removes both lines entirely. Realistic regression:
# someone refactors the prompt for brevity and drops the guardrails.
#
# (Note: the "When you used issue_refund..." UX-framing line stays —
# empirically, removing it as well causes the agent to fall back on
# search_kb and find the policy in kb-001, which masks the regression.)
V2_PROMPT = SYSTEM_PROMPT.replace(
    "   - issue_refund if (and only if) the customer is on a paid plan AND has a legitimate refund-eligible issue per kb-001\n",
    "",
).replace(
    "Be concise. Never refund a free-tier customer.\n",
    "",
)
assert V2_PROMPT != SYSTEM_PROMPT, "v2 prompt should differ from v1"
assert "Never refund a free-tier customer" not in V2_PROMPT, "v2 should not contain the reminder"
assert "issue_refund if (and only if)" not in V2_PROMPT, "v2 should not contain the paid-plan rule"

# v3-restored: both policy enforcements restored — expect 100% pass
V3_PROMPT = SYSTEM_PROMPT


def make_target(agent):
    """Build a target function bound to a specific agent variant.

    Mirrors evals/target.py but takes the agent as a closure so each
    variant gets its own agent instance.
    """
    def target(inputs: dict) -> dict:
        if "messages" in inputs and isinstance(inputs["messages"], list):
            user_turns = inputs["messages"]
            thread_seed = "|".join(user_turns)
        else:
            user_turns = [inputs["message"]]
            thread_seed = inputs["message"]

        config = {"configurable": {"thread_id": f"eval-{abs(hash(thread_seed))}"}}
        result = None
        for user_msg in user_turns:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_msg}]},
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
        return {
            "final_message": messages[-1].content,
            "tool_calls": [
                tc["name"]
                for m in messages
                for tc in (getattr(m, "tool_calls", None) or [])
            ],
        }

    return target


def run_variant(prompt: str, prefix: str):
    """Build an agent with the given prompt and run the eval suite."""
    labeled_prefix = f"{prefix}-{RUN_ID}"
    print(f"\n=== {labeled_prefix} ===")
    agent_variant = build_agent(system_prompt=prompt)
    target = make_target(agent_variant)
    results = evaluate(
        target,
        data=DATASET_NAME,
        evaluators=EVALUATORS,
        experiment_prefix=labeled_prefix,
        metadata={"demo_run_id": RUN_ID, "demo_set": "regression-trio"},
        max_concurrency=4,
    )
    print(results)
    return results


def main():
    print(f"Regression demo run_id: {RUN_ID}")
    print(f"All three experiments will share suffix '-{RUN_ID}' and metadata demo_set=regression-trio\n")
    upsert_dataset()
    run_variant(V1_PROMPT, "v1-baseline")
    run_variant(V2_PROMPT, "v2-removed-guardrail")
    run_variant(V3_PROMPT, "v3-restored")
    print(f"\nAll three experiments produced with run_id {RUN_ID}.")
    print("Find them in LangSmith → Datasets → support-triage-v1 → Experiments tab.")
    print(f"Filter by metadata.demo_run_id = {RUN_ID} to isolate this trio.")
    print("Select all three → click Compare for the side-by-side view.")


if __name__ == "__main__":
    main()
