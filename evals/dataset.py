from dotenv import load_dotenv
from langsmith import Client
from src.seed_data import SEED_EXAMPLES

load_dotenv()

DATASET_NAME = "support-triage-v1"
CAPABILITY_DATASET_NAME = "support-triage-capability-v1"


def _build_example_payload(ex: dict) -> dict:
    """Convert a SEED_EXAMPLES dict to a LangSmith create_examples payload.

    Threads the optional ``split`` field — LangSmith's primitive for tagging
    subsets so they're filterable in the dataset UI and targetable via
    ``list_examples(splits=[...])``.
    """
    payload = {
        "inputs": ex["inputs"],
        "outputs": ex["reference_outputs"],
        "metadata": {"ex_id": ex["id"]},
    }
    split = ex.get("split")
    if split is not None:
        payload["split"] = split
    return payload


def ensure_dataset():
    """Ensure the regression dataset exists in LangSmith; create + populate if absent.

    Idempotent: if the dataset already exists, this function is a no-op
    (~0.13 sec read check). If absent, the dataset is created and all
    seed examples are inserted in a single batched ``create_examples`` call
    (~0.5 sec for 21 examples).

    Why this pattern (not update-in-place):
    - LangSmith example UUIDs are stable for the lifetime of the example,
      so re-running this function preserves UUIDs automatically — no
      delete-and-recreate, no per-example update calls. The v1/v2/v3
      regression demo's Compare view joins by UUID; that join works as
      long as we don't recreate examples.
    - Single batched ``create_examples`` call is ~14x faster than the
      previous loop of ``update_example`` calls (which incurred one HTTP
      round-trip per example, ~0.4 sec each).
    - This matches the canonical LangSmith Evaluation Quickstart pattern
      (https://docs.langchain.com/langsmith/evaluation-quickstart).

    To push ``SEED_EXAMPLES`` changes after the dataset already exists:
    use :func:`update_existing_example` for in-place edits (preserves
    UUID) or :func:`add_examples_to_dataset` to append new rows
    (preserves existing UUIDs). Avoid recreating the dataset if you can —
    that would mint new UUIDs and break Compare-view joins on past
    experiments. For a workshop/demo where seed data is fixed, this
    function is a no-op on the second-and-subsequent runs.
    """
    client = Client()
    try:
        ds = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset {DATASET_NAME}: exists (no-op, UUIDs preserved)")
        return ds
    except Exception:
        pass

    ds = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Customer support triage agent eval dataset (workshop)",
    )
    payloads = [_build_example_payload(ex) for ex in SEED_EXAMPLES]
    client.create_examples(dataset_id=ds.id, examples=payloads)
    print(f"Dataset {DATASET_NAME}: created with {len(payloads)} examples")
    return ds


def ensure_capability_dataset():
    """Ensure the capability dataset exists in LangSmith; create + populate if absent.

    Same idempotent create-or-skip pattern as :func:`ensure_dataset` —
    see that function's docstring for the canonical-pattern rationale.

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
        print(f"Dataset {CAPABILITY_DATASET_NAME}: exists (no-op, UUIDs preserved)")
        return ds
    except Exception:
        pass

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
    payloads = [_build_example_payload(ex) for ex in CAPABILITY_EXAMPLES]
    client.create_examples(dataset_id=ds.id, examples=payloads)
    print(f"Dataset {CAPABILITY_DATASET_NAME}: created with {len(payloads)} examples")
    return ds


def add_examples_to_dataset(dataset_name: str, examples: list) -> int:
    """Append NEW examples to an existing dataset. UUIDs of existing examples preserved.

    Use this when you want to grow a dataset over time — e.g., after finding
    an edge case in production traces, after a panel review surfaces a new
    failure mode, or after the LLM-judge calibration pass. The new examples
    get fresh UUIDs; ALL existing examples stay byte-identical (same UUIDs,
    same content). Past experiments still join correctly in the Compare view.

    Args:
        dataset_name: existing dataset name (must already be created).
        examples: list of dicts in the SEED_EXAMPLES shape — each dict has
            keys ``id``, ``inputs``, ``reference_outputs``, optional ``split``.

    Returns:
        Number of examples added (which is len(examples) — fails loudly if
        the dataset doesn't exist or any example payload is malformed).

    Notes:
        - The ``id`` field becomes ``metadata.ex_id`` on the LangSmith example,
          mirroring the SEED_EXAMPLES convention.
        - This function does NOT deduplicate against existing ``ex_id`` values.
          If you pass an example whose ``ex_id`` already exists, you'll end
          up with TWO examples sharing that ``ex_id``. Caller's responsibility
          to ensure uniqueness — or use :func:`update_existing_example` to
          edit existing rows instead.
    """
    client = Client()
    ds = client.read_dataset(dataset_name=dataset_name)
    payloads = [_build_example_payload(ex) for ex in examples]
    client.create_examples(dataset_id=ds.id, examples=payloads)
    return len(payloads)


def update_existing_example(dataset_name: str, ex_id: str, **fields):
    """Update an EXISTING example in place by ``ex_id`` metadata. Preserves UUID.

    Use when seed data for an example has changed and you want LangSmith to
    reflect the new ground truth without losing the example's UUID — losing
    the UUID would break Compare-view joins on past experiments that
    referenced this example.

    Args:
        dataset_name: existing dataset name.
        ex_id: the ``metadata.ex_id`` value identifying which example to edit.
        **fields: any of ``inputs``, ``outputs``, ``metadata``, ``split``.
            (``metadata`` is replaced wholesale; if you want to keep ex_id,
            include it in the new metadata dict.)

    Raises:
        LookupError: no example in this dataset has the given ``ex_id``.

    Returns:
        The updated Example object.
    """
    client = Client()
    ds = client.read_dataset(dataset_name=dataset_name)
    target = next(
        (
            ex
            for ex in client.list_examples(dataset_id=ds.id)
            if ex.metadata and ex.metadata.get("ex_id") == ex_id
        ),
        None,
    )
    if target is None:
        raise LookupError(f"No example with ex_id={ex_id!r} in dataset {dataset_name!r}")
    return client.update_example(example_id=target.id, **fields)


if __name__ == "__main__":
    ensure_dataset()
    ensure_capability_dataset()
