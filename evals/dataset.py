from dotenv import load_dotenv
from langsmith import Client
from src.seed_data import SEED_EXAMPLES

load_dotenv()

DATASET_NAME = "support-triage-v1"


def upsert_dataset():
    """Create or refresh the LangSmith dataset (idempotent on ex_id metadata).

    Existing examples are matched by their `ex_id` metadata and updated in
    place so their UUIDs stay stable across runs — required for the
    Compare view to join experiments correctly.
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
        f"Dataset {DATASET_NAME}: {updated} updated, "
        f"{len(to_create)} created, {len(stale_ids)} removed"
    )
    return ds


if __name__ == "__main__":
    upsert_dataset()
