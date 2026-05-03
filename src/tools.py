from langchain_core.tools import tool
from src.kb import KB_DOCS, CUSTOMER_DB


@tool
def get_customer_plan(customer_id: str) -> dict:
    """Look up a customer's plan and account details."""
    if customer_id not in CUSTOMER_DB:
        return {"error": f"Customer {customer_id} not found"}
    return CUSTOMER_DB[customer_id]


@tool
def search_kb(query: str) -> list[dict]:
    """Search the knowledge base. Returns matching docs with their IDs."""
    results = []
    q = query.lower()
    for doc_id, doc in KB_DOCS.items():
        haystack = (doc["title"] + " " + doc["content"]).lower()
        if any(word in haystack for word in q.split()):
            results.append({"id": doc_id, "title": doc["title"], "content": doc["content"]})
    return results[:3]


@tool
def issue_refund(customer_id: str, amount: float, reason: str) -> str:
    """Submit a refund request for review. The refund is NOT executed immediately —
    it is queued and processed only after a human reviewer approves it. Tell the
    customer their request has been submitted; do NOT tell them the refund has
    been issued."""
    return (
        f"Refund request submitted for {customer_id}: ${amount} for '{reason}'. "
        f"Customer will be emailed once review is complete."
    )


@tool
def escalate(customer_id: str, summary: str) -> str:
    """Escalate the case to a human support agent."""
    return f"Case escalated for {customer_id}: {summary}"
