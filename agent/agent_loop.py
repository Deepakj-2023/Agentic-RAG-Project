from agent.context import Context
from agent.llm_brain import plan_action, synthesize_answer, evaluate_answer, ToolCall
from agent.fusion import fuse_results, format_fused_for_llm

from tools.web_search_tool import web_search
from tools.search_doc_tool import search_docs
from tools.query_tool import query_data

MAX_STEPS = 8


def run_agent(question: str):
    print(f"\n>>> Question: {question}")

    context = Context()
    run_id = context.create_run()   #  FIX: session-based memory

    trace = []
    last_feedback = ""

    for step in range(MAX_STEPS):
        print(f"\n--- Step {step+1} ---")

        #  Use session context
        full_context = context.to_string(run_id)

        if last_feedback:
            full_context += f"\n\nEvaluator Feedback:\n{last_feedback}"

        decision = plan_action(question, full_context)

        print(f"[THOUGHT] {decision.thought}")
        print(f"[ACTION] {decision.action}")

        #  FIX: avoid ungrounded chat
        if decision.action == "chat":
            answer = synthesize_answer(question, full_context)
            return {"answer": answer, "trace": trace}

        # FIX: prevent empty tool list dead loop
        if not decision.tools:
            print("[WARNING] No tools selected, forcing web_search")
            decision.tools = [ToolCall(name="web_search", input=question)]

        # ---- TOOL EXECUTION ----
        for t in decision.tools:

            #  Better duplicate detection
            if any(
                t.name == prev["tool"] and
                t.input.strip().lower() == prev["input"].strip().lower()
                for prev in trace
            ):
                print(f"[SKIP] Duplicate {t.name}: {t.input}")
                continue

            print(f"[RUN] {t.name}: {t.input}")

            try:
                if t.name == "web_search":
                    result = web_search(t.input)

                elif t.name == "search_docs":
                    result = search_docs(t.input)

                elif t.name == "query_data":
                    result = query_data(
                        t.query_type or "sql",
                        t.input,
                        t.csv_name
                    )

                else:
                    result = {"error": "Unknown tool"}

            except Exception as e:
                result = {"error": str(e)}

            entry = {
                "step": step + 1,
                "tool": t.name,
                "input": t.input,
                "output": result
            }

            trace.append(entry)
            context.add(run_id, entry)

        # ----  (ONLY RECENT STEPS) ----
        recent_trace = trace[-5:]   #  FIX: reduce noise
        fused = fuse_results(recent_trace, question)
        fused_text = format_fused_for_llm(fused)

        # ---- SYNTHESIS ----
        answer = synthesize_answer(question, fused_text)
        print(f"[ANSWER] {answer[:120]}...")

        # ---- EVALUATION ----
        evaluation = evaluate_answer(question, answer, fused_text)

        print(f"[EVAL] {evaluation.sufficient}")
        print(f"[FEEDBACK] {evaluation.feedback}")

        #  STOP if good
        if evaluation.sufficient:
            return {
                "answer": answer,
                "confidence": "high",
                "trace": trace
            }

        # STOP if no progress
        if step > 2 and last_feedback == evaluation.feedback:
            print("[STOP] No progress detected")
            break

        last_feedback = evaluation.feedback

    return {
        "answer": "Could not complete reasoning in steps",
        "confidence": "low",
        "trace": trace
    }