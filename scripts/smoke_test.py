from src.agent import agent

result = agent.invoke(
    {"messages": [{"role": "user",
                   "content": "Hi, I'm cust_001. How do I reset my password?"}]},
    config={"configurable": {"thread_id": "smoke-1"}},
)
print(result["messages"][-1].content)
