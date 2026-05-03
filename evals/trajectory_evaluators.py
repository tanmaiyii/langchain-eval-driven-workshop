from agentevals.trajectory.llm import create_trajectory_llm_as_judge


def trajectory_superset(inputs: dict, outputs: dict, reference_outputs: dict):
    """Heuristic: every expected tool must appear in the actual tool sequence."""
    expected_tools = reference_outputs.get("expected_tools", [])
    if not expected_tools:
        return {"key": "trajectory_superset", "score": None, "comment": "no reference"}

    actual = outputs.get("tool_calls", [])
    score = 1 if all(t in actual for t in expected_tools) else 0
    return {
        "key": "trajectory_superset",
        "score": score,
        "comment": f"expected={expected_tools} actual={actual}",
    }


def trajectory_judge(inputs: dict, outputs: dict, reference_outputs: dict):
    """LLM-as-judge for trajectory plausibility using o3-mini."""
    judge = create_trajectory_llm_as_judge(
        model="openai:o3-mini",
    )
    return judge(
        inputs=inputs,
        outputs={"trajectory": outputs.get("tool_calls", [])},
        reference_outputs=reference_outputs,
    )
