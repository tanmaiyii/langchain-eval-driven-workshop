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
