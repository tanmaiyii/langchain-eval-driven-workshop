import uuid

from langgraph.types import Command
from src.agent import agent


def target(inputs: dict) -> dict:
    """Run the agent on a dataset input. Returns a normalized output dict.

    Accepts either a single-turn input (`inputs["message"]: str`) or a
    multi-turn input (`inputs["messages"]: list[str]`). Multi-turn examples
    feed each user message through the same thread_id so the checkpointer
    carries state across turns. Most examples are single-turn; multi-turn
    is exercised by `ex-021` to demonstrate that the eval infrastructure
    handles both shapes.

    Each invocation of `target()` gets a fresh thread_id (UUID) so that
    `num_repetitions` in `evaluate()` produces genuinely independent trials
    — no message-history leakage between repetitions of the same example.

    The HITL middleware will interrupt on issue_refund. For evals, we
    auto-approve so we measure what the agent WANTED to do.
    """
    if "messages" in inputs and isinstance(inputs["messages"], list):
        user_turns = inputs["messages"]
    else:
        user_turns = [inputs["message"]]

    config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
    result = None
    for user_msg in user_turns:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_msg}]},
            config=config,
            version="v2",
        )
        while result.interrupts:
            result = agent.invoke(
                Command(resume={"decisions": [{"type": "approve"}]}),
                config=config,
                version="v2",
            )

    messages = result.value["messages"]
    return {
        "final_message": messages[-1].content,
        "tool_calls": [
            tc["name"]
            for m in messages
            for tc in (getattr(m, "tool_calls", None) or [])
        ],
    }
