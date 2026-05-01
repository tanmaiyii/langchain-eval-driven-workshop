from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from src.tools import get_customer_plan, search_kb, issue_refund, escalate

load_dotenv()

SYSTEM_PROMPT = """You are a customer support triage agent for Acme SaaS.

For every customer message, you MUST:
1. Classify the issue as one of: billing, technical, account, other
2. Use get_customer_plan to fetch the customer's plan and details
3. Resolve via one of:
   - search_kb to find a knowledge base answer
   - escalate if the issue is angry, complex, or out of scope
   - issue_refund if (and only if) the customer is on a paid plan AND has a legitimate refund-eligible issue per kb-001

Always cite the KB document ID (e.g., "per kb-001") if you used the knowledge base.
Be concise. Never refund a free-tier customer.

Output your final response in this exact JSON format on the last line:
{"classification": "<billing|technical|account|other>", "answer": "<your answer>"}
"""


def build_agent(checkpointer=None):
    return create_agent(
        model="openai:gpt-4o-mini",
        tools=[get_customer_plan, search_kb, issue_refund, escalate],
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={"issue_refund": True},
            ),
        ],
        checkpointer=checkpointer or InMemorySaver(),
    )


agent = build_agent()
