def fuse_results(trace: list, question: str) -> dict:
    merged_data = []
    seen = set()
    sources = []
    conflicts = []

    question_words = set(question.lower().split())

    for step in trace:
        tool = step.get("tool")
        output = step.get("output", {})

        if not isinstance(output, dict):
            continue

        source = output.get("source", tool)
        if source not in sources:
            sources.append(source)

        # -------- STRUCTURED --------
        if "rows" in output and "columns" in output:
            for row in output["rows"]:
                row_dict = dict(zip(output["columns"], row))
                text = str(row_dict).lower()

                if not any(word in text for word in question_words):
                    continue

                key = str(row_dict)
                if key not in seen:
                    seen.add(key)
                    merged_data.append({
                        "type": "structured",
                        "data": row_dict
                    })

        # -------- DOC --------
        if tool == "search_docs":
            for doc in output.get("results", []):
                text = doc.get("text", "")
                if any(word in text.lower() for word in question_words):
                    if text not in seen:
                        seen.add(text)
                        merged_data.append({
                            "type": "doc",
                            "text": text[:200]
                        })

        # -------- WEB --------
        if tool == "web_search":
            for item in output.get("results", []):
                snippet = item.get("snippet", "")
                if any(word in snippet.lower() for word in question_words):
                    if snippet not in seen:
                        seen.add(snippet)
                        merged_data.append({
                            "type": "web",
                            "text": snippet[:200]
                        })

    # LIMIT SIZE (🔥 IMPORTANT)
    merged_data = merged_data[:10]

    if not merged_data:
        conflicts.append("No relevant data")

    return {
        "merged_data": merged_data,
        "sources": sources,
        "conflicts": conflicts,
        "total_items": len(merged_data)
    }


def format_fused_for_llm(fused: dict) -> str:
    lines = [
        "=== FUSED DATA ===",
        f"Sources: {', '.join(fused['sources'])}",
        f"Items: {fused['total_items']}"
    ]

    if fused["conflicts"]:
        lines.append(f"Conflicts: {', '.join(fused['conflicts'])}")

    lines.append("")

    for i, item in enumerate(fused["merged_data"], 1):
        if item["type"] == "structured":
            content = ", ".join(f"{k}: {v}" for k, v in item["data"].items())
        else:
            content = item["text"]

        lines.append(f"{i}. {content}")

    return "\n".join(lines)