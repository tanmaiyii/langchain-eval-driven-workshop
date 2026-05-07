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
import uuid

from langgraph.types import Command
from langsmith import Client, evaluate

from src.agent import SYSTEM_PROMPT, build_agent
from evals.dataset import DATASET_NAME, ensure_dataset
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
        else:
            user_turns = [inputs["message"]]

        # Fresh thread per call — required for num_repetitions to give
        # genuinely independent trials (no message-history leakage between reps).
        config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
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


def run_variant(prompt: str, prefix: str, data, num_repetitions: int = 1):
    """Build an agent with the given prompt and run the eval suite.

    `num_repetitions=N` runs each example N times in the same experiment.
    Aggregated scoring surfaces non-determinism: an example that passes on
    rep 1 may fail on rep 3 due to LLM stochasticity. Default 1 (single
    trial); v2 uses 3 to make the regression catch reliable on ex-012,
    where the agent has a ~40% chance of rescuing via search_kb reading
    kb-001 even after the policy line is removed.
    """
    labeled_prefix = f"{prefix}-{RUN_ID}"
    print(f"\n=== {labeled_prefix} ===")
    agent_variant = build_agent(system_prompt=prompt)
    target = make_target(agent_variant)
    results = evaluate(
        target,
        data=data,
        evaluators=EVALUATORS,
        experiment_prefix=labeled_prefix,
        metadata={"demo_run_id": RUN_ID, "demo_set": "regression-trio"},
        max_concurrency=4,
        num_repetitions=num_repetitions,
    )
    print(results)
    return results


def main():
    print(f"Regression demo run_id: {RUN_ID}")
    print(f"All three experiments will share suffix '-{RUN_ID}' and metadata demo_set=regression-trio\n")
    ensure_dataset()

    # Target the `regression` split (4 examples) — same set the build-along
    # notebook and pytest CI gate run on. Single source of truth.
    client = Client()
    data = list(client.list_examples(dataset_name=DATASET_NAME, splits=["regression"]))
    ex_ids = sorted(e.metadata.get("ex_id") for e in data)
    print(f"Regression split has {len(data)} examples: {ex_ids}\n")

    # All three variants use num_repetitions=3 for symmetric Compare-view
    # rows (4 examples × 3 reps = 12 rows per experiment, side-by-side).
    # Why 3 reps matters most for v2: the regression catch on ex-012 is
    # non-deterministic — the agent has ~30% chance per trial of rescuing
    # via search_kb reading kb-001 even after the policy line is removed.
    # 3 reps × ~70% per-trial catch ≈ 97% chance of seeing at least one
    # refund_safety=0 in the Compare view — the canonical num_repetitions
    # use case (measure variance, don't trust a single snapshot).
    run_variant(V1_PROMPT, "v1-baseline", data, num_repetitions=3)
    run_variant(V2_PROMPT, "v2-removed-guardrail", data, num_repetitions=3)
    run_variant(V3_PROMPT, "v3-restored", data, num_repetitions=3)
    print(f"\nAll three experiments produced with run_id {RUN_ID}.")
    print("Find them in LangSmith → Datasets → support-triage-v1 → Experiments tab.")
    print(f"Filter by metadata.demo_run_id = {RUN_ID} to isolate this trio.")
    print("Select all three → click Compare for the side-by-side view.")


if __name__ == "__main__":
    main()
