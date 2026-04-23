import os
from agent.llm_brain import plan_action

question = "Who scored the most runs in PSL history?"
context = ""

decision = plan_action(question, context)
print("Thought:", decision.thought)
print("Action:", decision.action)
print("Tools:", decision.tools)
