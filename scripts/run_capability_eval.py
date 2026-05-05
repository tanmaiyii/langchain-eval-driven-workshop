"""Capability eval runner — expected pass rate is low by design.

Capability evals are NOT a CI gate. They're a tracking metric. Initial pass
rates of 30-60% are normal; you track whether they improve as the agent
improves. Per the Agent Evaluation Readiness Checklist:

  "Capability evals push your agent forward by measuring progress on hard
   tasks, while regression evals protect what already works."
"""

from langsmith import evaluate
from evals.dataset import (
    CAPABILITY_DATASET_NAME,
    upsert_capability_dataset,
)
from evals.target import target
from evals.heuristic_evaluators import (
    classification_correct,
    refund_safety,
    escalation_correctness,
)


def main():
    upsert_capability_dataset()
    results = evaluate(
        target,
        data=CAPABILITY_DATASET_NAME,
        evaluators=[
            classification_correct,
            refund_safety,
            escalation_correctness,
        ],
        experiment_prefix="capability-baseline",
        max_concurrency=2,
    )
    print(results)
    print()
    print("Note: low pass rates on capability evals are expected and normal.")
    print("Track improvement over time as the agent's prompt/tools improve.")


if __name__ == "__main__":
    main()
