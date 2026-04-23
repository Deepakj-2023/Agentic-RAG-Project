from agent.context import Context
from agent.llm_brain import plan_action, synthesize_answer, evaluate_answer, ToolCall
from agent.fusion import fuse_results, format_fused_for_llm, extract_raw_tool_data

from tools.web_search_tool import web_search
from tools.search_doc_tool import search_docs
from tools.query_tool import query_data

MAX_STEPS = 8


# ────────────────────────────────────────
# TOOL EXECUTION
# ────────────────────────────────────────
def _execute_tool(tool_call: ToolCall) -> dict:
    try:
        if tool_call.name == "web_search":
            return web_search(tool_call.input)

        elif tool_call.name == "search_docs":
            return search_docs(tool_call.input)

        elif tool_call.name == "query_data":
            return query_data(
                tool_call.query_type,
                tool_call.input,
                tool_call.csv_name
            )

        return {"error": "Unknown tool"}

    except Exception as e:
        return {"error": str(e)}


# ────────────────────────────────────────
# DUPLICATE CHECK
# ────────────────────────────────────────
def _is_duplicate(tool_call: ToolCall, trace: list) -> bool:
    for prev in trace:
        if (
            tool_call.name == prev["tool"] and
            tool_call.input.strip().lower() == prev["input"].strip().lower()
        ):
            return True
    return False


# ────────────────────────────────────────
# AGENT LOOP
# ────────────────────────────────────────
def run_agent(question: str):
    print(f"\n>>> Question: {question}")

    context = Context()
    run_id = context.create_run()

    trace = []
    last_feedback = ""

    for step in range(MAX_STEPS):
        print(f"\n--- Step {step+1} ---")

        full_context = context.to_string(run_id)
        if last_feedback:
            full_context += f"\nFix this:\n{last_feedback}"

        decision = plan_action(question, full_context)

        print(f"[THOUGHT] {decision.thought}")
        print(f"[ACTION] {decision.action}")

        # ── CHAT MODE ──
        if decision.action == "chat":
            raw = extract_raw_tool_data(trace)
            answer = synthesize_answer(question, raw or full_context)
            return {"answer": answer, "trace": trace, "steps_used": step + 1}

        # ── TOOL FALLBACK ──
        if not decision.tools:
            decision.tools = [ToolCall(name="web_search", input=question)]

        executed_any = False

        # ── EXECUTE TOOLS ──
        for t in decision.tools:

            if _is_duplicate(t, trace):
                print(f"[SKIP] Duplicate → forcing web_search")
                t = ToolCall(name="web_search", input=question)

            print(f"[TOOL] {t.name}")
            print(f"  Intent: {t.input}")
            if t.query_type:
                print(f"  Type: {t.query_type}")

            result = _execute_tool(t)

            print(f"  Result: {str(result)[:120]}")

            trace.append({
                "step": step + 1,
                "tool": t.name,
                "input": t.input,
                "output": result
            })

            context.add(run_id, trace[-1])
            executed_any = True

        if not executed_any:
            print("[STOP] No tool executed")
            break

        # ── FUSION ──
        recent = trace[-6:]
        fused = fuse_results(recent, question)

        fused_text = format_fused_for_llm(fused)
        raw_text = extract_raw_tool_data(recent)

        combined = fused_text + "\n\n" + raw_text

        # ── SYNTHESIS ──
        answer = synthesize_answer(question, combined)
        print(f"[ANSWER] {answer[:150]}")

        # ── EVALUATION ──
        evaluation = evaluate_answer(question, answer, combined)

        print(f"[EVAL] {evaluation.sufficient}")
        print(f"[FEEDBACK] {evaluation.feedback}")

        if evaluation.sufficient:
            return {
                "answer": evaluation.output or answer,
                "trace": trace,
                "confidence": "high",
                "steps_used": step + 1
            }

        # Stop if stuck
        if last_feedback == evaluation.feedback:
            print("[STOP] No improvement")
            return {
                "answer": answer,
                "trace": trace,
                "confidence": "medium",
                "steps_used": step + 1
            }

        last_feedback = evaluation.feedback

    return {
        "answer": "Failed to solve within steps",
        "trace": trace,
        "confidence": "low",
        "steps_used": MAX_STEPS
    }