from openevals.llm import create_llm_as_judge

KB_GROUNDING_PROMPT = """You are evaluating whether an AI customer support agent's answer is grounded in the knowledge base.

The agent must cite a KB doc ID (e.g., "kb-001") when it uses information from the knowledge base.

<inputs>
{inputs}
</inputs>

<agent_answer>
{outputs}
</agent_answer>

<expected_kb_doc>
{reference_outputs}
</expected_kb_doc>

Score the answer 0.0 to 1.0:
- 1.0: Cited the expected KB doc and the answer is consistent with it
- 0.5: Cited a KB doc but it was the wrong one, OR cited the right one but the answer is loose
- 0.0: Did not cite any KB doc, or made up information

Respond ONLY with the score as a float. No explanation.
"""


def kb_grounding_judge(inputs: dict, outputs: dict, reference_outputs: dict):
    """LLM-as-judge for KB grounding using o3-mini.

    Skipped when no KB citation is expected (escalations, refund refusals,
    out-of-scope queries) — the rubric has no N/A path so without skipping,
    these rows would all score 0.0 and pull the headline average down.
    """
    if not reference_outputs.get("expected_kb_doc_id"):
        return {
            "key": "kb_grounding",
            "score": None,
            "comment": "skipped: no KB citation expected for this example",
        }

    evaluator = create_llm_as_judge(
        prompt=KB_GROUNDING_PROMPT,
        model="openai:o3-mini",
        feedback_key="kb_grounding",
    )
    return evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )
