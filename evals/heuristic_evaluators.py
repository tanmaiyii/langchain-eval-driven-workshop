import json
import re


def _extract_classification(output_text: str) -> str | None:
    """Pull the JSON block from the agent's final message."""
    if not output_text:
        return None
    match = re.search(r'\{[^}]*"classification"[^}]*\}', output_text)
    if not match:
        return None
    try:
        return json.loads(match.group(0)).get("classification")
    except json.JSONDecodeError:
        return None


def classification_correct(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    pred = _extract_classification(outputs.get("final_message", ""))
    expected = reference_outputs.get("expected_classification")
    score = 1 if pred == expected else 0
    return {
        "key": "classification_correct",
        "score": score,
        "comment": f"predicted={pred} expected={expected}",
    }


def refund_safety(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Refund safety: should_refund must match the actual refund call."""
    tools_called = outputs.get("tool_calls", [])
    refunded = "issue_refund" in tools_called
    should_refund = reference_outputs.get("should_refund", False)

    if refunded and not should_refund:
        return {
            "key": "refund_safety",
            "score": 0,
            "comment": "Agent issued refund when it should not have",
        }
    if not refunded and should_refund:
        return {
            "key": "refund_safety",
            "score": 0,
            "comment": "Agent failed to issue refund when it should have",
        }
    return {"key": "refund_safety", "score": 1}


def escalation_correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    tools_called = outputs.get("tool_calls", [])
    escalated = "escalate" in tools_called
    should = reference_outputs.get("should_escalate", False)
    score = 1 if escalated == should else 0
    return {"key": "escalation_correctness", "score": score}
