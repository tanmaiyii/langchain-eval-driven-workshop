from dotenv import load_dotenv
from langsmith import Client
from src.seed_data import SEED_EXAMPLES

load_dotenv()

DATASET_NAME = "support-triage-v1"
CAPABILITY_DATASET_NAME = "support-triage-capability-v1"


def upsert_dataset():
    """Idempotent upsert of the regression dataset to LangSmith.

    Keyed on ``ex_id`` metadata: existing examples are matched by their
    ``ex_id`` and updated in place; new examples are created; examples
    that no longer appear in ``SEED_EXAMPLES`` are removed. The result
    is that example UUIDs stay STABLE across re-runs.

    Why stable UUIDs matter: LangSmith's experiment Compare view joins
    rows across experiments by UUID. If this function deleted and
    recreated examples on every run (the naive approach), each run
    would produce fresh UUIDs and the Compare view would render three
    side-by-side experiments as three disjoint datasets. Idempotent
    upsert preserves the join — and the v1/v2/v3 regression demo
    depends on it.

    Empirically verified: re-running this function reports
    ``N updated, 0 created, 0 removed`` after the first run.
    """
    client = Client()
    try:
        ds = client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        ds = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Customer support triage agent eval dataset (workshop)",
        )

    existing_by_ex_id = {
        ex.metadata.get("ex_id"): ex
        for ex in client.list_examples(dataset_id=ds.id)
        if ex.metadata and ex.metadata.get("ex_id")
    }

    seed_ex_ids = {ex["id"] for ex in SEED_EXAMPLES}

    to_create = []
    updated = 0
    for ex in SEED_EXAMPLES:
        # `split` (LangSmith primitive) tags the canonical trap subset so it's
        # filterable in the dataset UI and can be targeted via evaluate(splits=[...]).
        split = ex.get("split")
        existing = existing_by_ex_id.get(ex["id"])
        if existing is None:
            payload = {
                "inputs": ex["inputs"],
                "outputs": ex["reference_outputs"],
                "metadata": {"ex_id": ex["id"]},
            }
            if split is not None:
                payload["split"] = split
            to_create.append(payload)
        else:
            client.update_example(
                example_id=existing.id,
                inputs=ex["inputs"],
                outputs=ex["reference_outputs"],
                metadata={"ex_id": ex["id"]},
                split=split,
            )
            updated += 1

    if to_create:
        client.create_examples(dataset_id=ds.id, examples=to_create)

    stale_ids = [
        existing.id
        for ex_id, existing in existing_by_ex_id.items()
        if ex_id not in seed_ex_ids
    ]
    if stale_ids:
        client.delete_examples(example_ids=stale_ids)

    print(
        f"Dataset {DATASET_NAME}: {updated} updated, "
        f"{len(to_create)} created, {len(stale_ids)} removed"
    )
    return ds


def upsert_capability_dataset():
    """Idempotent upsert of the capability dataset to LangSmith.

    Same ``ex_id``-keyed idempotency pattern as :func:`upsert_dataset` —
    see that function's docstring for the WHY (stable UUIDs required
    for Compare-view joins). This invariant is shared because capability
    runs also accumulate experiments over time as the agent improves.

    The capability dataset is the complementary suite to regression:
    harder examples where pass rate starts low and tracks improvement,
    per LangChain's Agent Evaluation Readiness Checklist. Kept as a
    SEPARATE dataset (not just a marker on the regression dataset)
    because capability and regression have different gating semantics —
    regression hard-asserts in CI; capability tracks without gating.
    Separate datasets make the boundary structural, not convention.
    """
    from src.seed_data import CAPABILITY_EXAMPLES

    client = Client()
    try:
        ds = client.read_dataset(dataset_name=CAPABILITY_DATASET_NAME)
    except Exception:
        ds = client.create_dataset(
            dataset_name=CAPABILITY_DATASET_NAME,
            description=(
                "Capability eval dataset — harder examples that test what the "
                "agent should eventually do but currently struggles with. Pass "
                "rate starts low and tracks improvement over time. Per LangChain's "
                "Agent Evaluation Readiness Checklist: capability evals are "
                "complementary to regression evals."
            ),
        )

    existing_by_ex_id = {
        ex.metadata.get("ex_id"): ex
        for ex in client.list_examples(dataset_id=ds.id)
        if ex.metadata and ex.metadata.get("ex_id")
    }

    seed_ex_ids = {ex["id"] for ex in CAPABILITY_EXAMPLES}

    to_create = []
    updated = 0
    for ex in CAPABILITY_EXAMPLES:
        existing = existing_by_ex_id.get(ex["id"])
        if existing is None:
            to_create.append(
                {
                    "inputs": ex["inputs"],
                    "outputs": ex["reference_outputs"],
                    "metadata": {"ex_id": ex["id"]},
                }
            )
        else:
            client.update_example(
                example_id=existing.id,
                inputs=ex["inputs"],
                outputs=ex["reference_outputs"],
                metadata={"ex_id": ex["id"]},
            )
            updated += 1

    if to_create:
        client.create_examples(dataset_id=ds.id, examples=to_create)

    stale_ids = [
        existing.id
        for ex_id, existing in existing_by_ex_id.items()
        if ex_id not in seed_ex_ids
    ]
    if stale_ids:
        client.delete_examples(example_ids=stale_ids)

    print(
        f"Dataset {CAPABILITY_DATASET_NAME}: {updated} updated, "
        f"{len(to_create)} created, {len(stale_ids)} removed"
    )
    return ds


if __name__ == "__main__":
    upsert_dataset()
