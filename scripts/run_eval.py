from langsmith import Client
from evals.dataset import DATASET_NAME, upsert_dataset
from evals.target import target
from evals.heuristic_evaluators import (
    classification_correct,
    refund_safety,
    escalation_correctness,
)


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
        ],
        experiment_prefix="heuristic-baseline",
        max_concurrency=4,
    )
    print(results)


if __name__ == "__main__":
    main()
