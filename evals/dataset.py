from dotenv import load_dotenv
from langsmith import Client
from src.seed_data import SEED_EXAMPLES

load_dotenv()

DATASET_NAME = "support-triage-v1"


def upsert_dataset():
    """Create or refresh the LangSmith dataset (idempotent)."""
    client = Client()
    try:
        ds = client.read_dataset(dataset_name=DATASET_NAME)
        existing = list(client.list_examples(dataset_id=ds.id))
        if existing:
            client.delete_examples(example_ids=[e.id for e in existing])
    except Exception:
        ds = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Customer support triage agent eval dataset (workshop)",
        )

    examples = [
        {
            "inputs": ex["inputs"],
            "outputs": ex["reference_outputs"],
        }
        for ex in SEED_EXAMPLES
    ]
    client.create_examples(dataset_id=ds.id, examples=examples)
    print(f"Created/updated dataset: {DATASET_NAME} with {len(examples)} examples")
    return ds


if __name__ == "__main__":
    upsert_dataset()
