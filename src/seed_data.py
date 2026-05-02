SEED_EXAMPLES = [
    # Easy: free-tier password reset
    {
        "id": "ex-001",
        "inputs": {"message": "Hi, I'm cust_002. I forgot my password."},
        "reference_outputs": {
            "expected_classification": "account",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-002",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: pro asks about API rate limit
    {
        "id": "ex-002",
        "inputs": {"message": "Hi, this is cust_001. What's the API rate limit on my plan?"},
        "reference_outputs": {
            "expected_classification": "technical",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-003",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: pro asks how to set up 2FA
    {
        "id": "ex-003",
        "inputs": {"message": "I'm cust_001 and I want to enable two-factor authentication on my account. How do I do that?"},
        "reference_outputs": {
            "expected_classification": "account",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-005",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: free customer asks about plan upgrade timing
    {
        "id": "ex-004",
        "inputs": {"message": "Hey, this is cust_002. If I upgrade from free to pro, when does the new plan kick in?"},
        "reference_outputs": {
            "expected_classification": "billing",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-006",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Tricky: sounds like refund but is actually billing question
    {
        "id": "ex-005",
        "inputs": {"message": "I'm cust_001. When does my next billing cycle start? I want to know before I'm charged again."},
        "reference_outputs": {
            "expected_classification": "billing",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-004",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: enterprise customer asks about refund policy (asking, not requesting)
    {
        "id": "ex-006",
        "inputs": {"message": "Hi, I'm cust_003. Could you remind me of your refund policy?"},
        "reference_outputs": {
            "expected_classification": "billing",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-001",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: free customer asks about billing cycle
    {
        "id": "ex-007",
        "inputs": {"message": "I'm cust_002. When do subscriptions renew?"},
        "reference_outputs": {
            "expected_classification": "billing",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-004",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Angry — should escalate regardless of issue type
    {
        "id": "ex-008",
        "inputs": {"message": "This is RIDICULOUS. I'm cust_003 and your service has been down for 3 hours. I'm furious."},
        "reference_outputs": {
            "expected_classification": "technical",
            "should_escalate": True,
            "should_refund": False,
        },
    },
    # Happy: enterprise password reset
    {
        "id": "ex-009",
        "inputs": {"message": "Hi this is cust_003. I need to reset my password for my account."},
        "reference_outputs": {
            "expected_classification": "account",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-002",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Happy: enterprise asks about API rate limits
    {
        "id": "ex-010",
        "inputs": {"message": "I'm cust_003. What's the rate limit on the enterprise plan?"},
        "reference_outputs": {
            "expected_classification": "technical",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-003",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Complex multi-issue → escalate (out of scope for single KB lookup)
    {
        "id": "ex-011",
        "inputs": {"message": "Hi, this is cust_001. I've got three things — first my API key isn't working, second I think I was billed twice this month, and third I need to add five new users to my account today. Can you help with all of these?"},
        "reference_outputs": {
            "expected_classification": "other",
            "should_escalate": True,
            "should_refund": False,
        },
    },
    # Trap: free tier asking for refund (must NOT refund)
    {
        "id": "ex-012",
        "inputs": {"message": "I'm cust_002 and I want a refund for last month."},
        "reference_outputs": {
            "expected_classification": "billing",
            "should_refund": False,
            "expected_kb_doc_id": "kb-001",
        },
    },
    # Out of scope: regulatory/legal request → escalate
    {
        "id": "ex-013",
        "inputs": {"message": "I'm cust_002. Can you delete all my account data permanently and confirm in writing within 24 hours? It's for a regulatory request."},
        "reference_outputs": {
            "expected_classification": "account",
            "should_escalate": True,
            "should_refund": False,
        },
    },
    # Complex contract/legal → escalate
    {
        "id": "ex-014",
        "inputs": {"message": "I'm cust_001. My company is being acquired and we need to migrate the contract to a new entity by month-end. Who should I talk to?"},
        "reference_outputs": {
            "expected_classification": "billing",
            "should_escalate": True,
            "should_refund": False,
        },
    },
    # Legitimate enterprise refund (SHOULD refund after HITL)
    {
        "id": "ex-015",
        "inputs": {"message": "Hi, I'm cust_003. We were billed $2000 last week for an extra seat that we never added. Can I get a refund for that?"},
        "reference_outputs": {
            "expected_classification": "billing",
            "should_refund": True,
            "expected_kb_doc_id": "kb-001",
        },
    },
    # Trap: free tier general unhappiness → must NOT refund (different framing from ex-012)
    {
        "id": "ex-016",
        "inputs": {"message": "I'm cust_002 and I'm really unhappy with the service. I'd like my money back please."},
        "reference_outputs": {
            "expected_classification": "billing",
            "should_refund": False,
            "expected_kb_doc_id": "kb-001",
        },
    },
    # Tricky: looks like password issue but is actually 2FA (SMS code not arriving)
    {
        "id": "ex-017",
        "inputs": {"message": "Hi I'm cust_001. I'm trying to log in but my SMS code isn't arriving. Can you help?"},
        "reference_outputs": {
            "expected_classification": "account",
            "expected_tools": ["get_customer_plan", "search_kb"],
            "expected_kb_doc_id": "kb-005",
            "should_escalate": False,
            "should_refund": False,
        },
    },
    # Tricky: KB miss — feature not in our knowledge base → escalate / "other"
    {
        "id": "ex-018",
        "inputs": {"message": "Hi, I'm cust_001. Do you have a Slack integration available?"},
        "reference_outputs": {
            "expected_classification": "other",
            "should_escalate": True,
            "should_refund": False,
        },
    },
    # Legitimate Pro refund (SHOULD refund after HITL)
    {
        "id": "ex-019",
        "inputs": {"message": "I'm cust_001. I was double-charged $50 last week and I'd like a refund."},
        "reference_outputs": {
            "expected_classification": "billing",
            "should_refund": True,
            "expected_kb_doc_id": "kb-001",
        },
    },
    # Tricky: malformed/unknown customer ID — get_customer_plan returns error → escalate
    {
        "id": "ex-020",
        "inputs": {"message": "Hi, I'm cust_999. I forgot my password and need help."},
        "reference_outputs": {
            "expected_classification": "account",
            "should_escalate": True,
            "should_refund": False,
        },
    },
]
