# agent_loop.py : Multi-role agent loop (Planner -> Executor -> Synthesizer -> Evaluator)

import json
from agent.context import Context
from agent.llm_brain import plan_action, synthesize_answer, evaluate_answer, ToolCall
from agent.fusion import fuse_results, format_fused_for_llm
from utils.knowledge_graph import load_knowledge_graph, lookup_fact

# Import tools
from tools.web_search_tool import web_search
from tools.search_doc_tool import search_docs
from tools.query_tool import query_data

MAX_STEPS = 8

# Load knowledge graph once at module level
_kg = load_knowledge_graph()

def run_agent(question: str):
    print(f"\n>>> Starting Agent for Question: {question}")
    context = Context()
    trace = []
    
    # Phase 0: Knowledge Graph
    kg_result = lookup_fact(_kg, question)
    if kg_result:
        trace.append({"step": 0, "tool": "knowledge_graph", "output": kg_result})
        context.add({"step": 0, "tool": "knowledge_graph", "input": question, "output": kg_result})

    last_feedback = ""

    for step in range(MAX_STEPS):
        step_num = step + 1
        print(f"\n--- Step {step_num} / {MAX_STEPS} ---")

        # [PLAN] Planner decides next steps
        full_context = str(context)
        if last_feedback:
            full_context += f"\n\n--- EVALUATOR FEEDBACK FROM PREVIOUS STEP ---\n{last_feedback}"
            
        decision = plan_action(question, full_context)
        print(f"[PLAN] Action: {decision.action} | Reason: {decision.reason}")

        if decision.action == "chat":
            # Handle simple chat/greetings
            answer = synthesize_answer(question, "User is just chatting or saying hello.")
            return {"answer": answer, "trace": trace, "steps_used": step_num}

        # [ACT] Execute tool(s)
        tool_results = []
        for t in decision.tools:
            if not t.name or t.name == "chat": continue
            print(f"[ACT] Running {t.name}: {t.input}")
            try:
                if t.name == "web_search": result = web_search(t.input)
                elif t.name == "search_docs": result = search_docs(t.input)
                elif t.name == "query_data": result = query_data(t.query_type or "sql", t.input, t.csv_name)
                else: result = {"error": f"Unknown tool: {t.name}"}
            except Exception as e:
                result = {"error": str(e)}
            
            res_entry = {"step": step_num, "tool": t.name, "input": t.input, "output": result}
            trace.append(res_entry)
            context.add(res_entry)
            tool_results.append(result)

        # [FUSE & SYNTHESIZE]
        fused = fuse_results(trace, question)
        fused_text = format_fused_for_llm(fused)
        current_answer = synthesize_answer(question, fused_text)
        print(f"[SYNTHESIZE] Current Answer: {current_answer[:100]}...")

        # [EVALUATE]
        evaluation = evaluate_answer(question, current_answer, fused_text)
        print(f"[EVALUATE] Sufficient: {evaluation.sufficient}")
        if evaluation.feedback:
            print(f"[EVALUATE] Feedback: {evaluation.feedback}")
        if evaluation.correction:
            print(f"[EVALUATE] Correction: {evaluation.correction}")

        if evaluation.sufficient or step_num == MAX_STEPS:
            return {
                "answer": current_answer,
                "trace": trace,
                "steps_used": step_num
            }
        
        last_feedback = f"Feedback: {evaluation.feedback}\nCorrection: {evaluation.correction}"
        
    return {
        "answer": "Failed to find a sufficient answer within max steps.",
        "trace": trace,
        "steps_used": MAX_STEPS
    }