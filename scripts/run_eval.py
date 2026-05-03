from langsmith import Client
from evals.dataset import DATASET_NAME, upsert_dataset
from evals.target import target
from evals.heuristic_evaluators import (
    classification_correct,
    refund_safety,
    escalation_correctness,
)
from evals.llm_judge_evaluators import kb_grounding_judge
from evals.trajectory_evaluators import trajectory_superset


def main():
    upsert_dataset()
    client = Client()
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[
            classification_correct,
            refund_safety,
            escalation_correctness,
            kb_grounding_judge,
            trajectory_superset,
        ],
        experiment_prefix="v3-restored",
        max_concurrency=4,
    )
    print(results)


if __name__ == "__main__":
    main()
