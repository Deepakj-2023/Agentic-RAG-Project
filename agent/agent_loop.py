# agent_loop.py : Main loop for the agent, orchestrating LLM decisions and tool executions

from context import Context
from llm_brain import call_llm

# import your tools
from tools.web_search_tool import web_search
from tools.search_doc_tool import search_docs
from tools.query_tool import query_data

MAX_STEPS = 8


def run_agent(question: str):
    context = Context()
    trace = []

    for step in range(MAX_STEPS):

        print(f"\n--- Step {step+1} ---")

        decision = call_llm(question, str(context))

        action = decision.action
        tool_input = decision.input

        print(f"Decision: {action}")
        print(f"Input: {tool_input}")

        if action == "final":
            return {
                "answer": tool_input,
                "trace": trace
            }

        #  Tool Execution Logic
        if action == "web_search":
            result = web_search(tool_input)

        elif action == "search_docs":
            result = search_docs(tool_input)

        elif action == "query_data":
            result = query_data(tool_input)

        else:
            return {
                "answer": "Invalid tool selected",
                "trace": trace
            }

        print(f"Result: {result}")

        #  Update in context
        step_data = {
            "step": step + 1,
            "tool": action,
            "input": tool_input,
            "output": result
        }

        context.add(step_data)
        trace.append(step_data)

    return {
        "answer": "I cannot answer within 8 steps",
        "trace": trace
    } 