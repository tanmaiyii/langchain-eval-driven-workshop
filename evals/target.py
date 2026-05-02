from langgraph.types import Command
from src.agent import agent


def target(inputs: dict) -> dict:
    """Run the agent on a dataset input. Returns a normalized output dict.

    The HITL middleware will interrupt on issue_refund. For evals, we
    auto-approve so we measure what the agent WANTED to do.
    """
    config = {"configurable": {"thread_id": f"eval-{abs(hash(inputs['message']))}"}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": inputs["message"]}]},
        config=config,
    )
    while result.get("__interrupt__"):
        result = agent.invoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
        )

    return {
        "final_message": result["messages"][-1].content,
        "tool_calls": [
            tc["name"]
            for m in result["messages"]
            for tc in (getattr(m, "tool_calls", None) or [])
        ],
    }
