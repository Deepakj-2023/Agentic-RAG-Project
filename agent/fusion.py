def fuse_results(trace: list, question: str) -> dict:
    """
    Fuse all tool outputs into a structured data block.
    
    NO keyword filtering — ALL tool data passes through.
    The LLM synthesizer decides what's relevant, not this function.
    
    Priority order: structured DB data > doc results > web results
    """
    structured_data = []
    doc_data = []
    web_data = []
    seen = set()
    sources = []
    conflicts = []

    for step in trace:
        tool = step.get("tool")
        output = step.get("output", {})

        if not isinstance(output, dict):
            continue

        # Track errors
        if "error" in output:
            conflicts.append(f"{tool}: {output['error'][:100]}")
            continue

        # Track empty results
        if "message" in output and output.get("row_count", -1) == 0:
            conflicts.append(f"{tool}: {output['message']}")
            continue

        source = output.get("source", tool)
        if source not in sources:
            sources.append(source)

        # ── STRUCTURED DATA (SQL / Pandas results) ──
        if "rows" in output and "columns" in output:
            for row in output["rows"]:
                row_dict = dict(zip(output["columns"], row))
                key = str(sorted(row_dict.items()))
                if key not in seen:
                    seen.add(key)
                    structured_data.append({
                        "type": "structured",
                        "source": source,
                        "data": row_dict
                    })

        # ── DOCUMENT RESULTS ──
        if tool == "search_docs":
            for doc in output.get("results", []):
                text = doc.get("text", "")
                if text:
                    key = text[:80]
                    if key not in seen:
                        seen.add(key)
                        doc_data.append({
                            "type": "doc",
                            "source": doc.get("source", "local_docs"),
                            "text": text[:800]
                        })

        # ── WEB RESULTS ──
        if tool == "web_search":
            for item in output.get("results", []):
                snippet = item.get("snippet", "")
                if snippet:
                    key = snippet[:80]
                    if key not in seen:
                        seen.add(key)
                        web_data.append({
                            "type": "web",
                            "title": item.get("title", ""),
                            "text": snippet[:800]
                        })

    # Priority merge: DB first, then docs, then web
    merged_data = structured_data + doc_data + web_data
    merged_data = merged_data[:20]

    if not merged_data:
        conflicts.append("No data found from any tool")

    return {
        "merged_data": merged_data,
        "sources": sources,
        "conflicts": conflicts,
        "total_items": len(merged_data),
        "breakdown": {
            "structured": len(structured_data),
            "docs": len(doc_data),
            "web": len(web_data)
        }
    }


def format_fused_for_llm(fused: dict) -> str:
    """Format fused data for the synthesizer LLM."""
    lines = [
        "=== FUSED EVIDENCE ===",
        f"Sources: {', '.join(fused['sources'])}",
        f"Items: {fused['total_items']} "
        f"(DB: {fused['breakdown']['structured']}, "
        f"Docs: {fused['breakdown']['docs']}, "
        f"Web: {fused['breakdown']['web']})"
    ]

    if fused["conflicts"]:
        lines.append(f"Issues: {'; '.join(fused['conflicts'])}")

    lines.append("")

    # DB results section
    structured = [d for d in fused["merged_data"] if d["type"] == "structured"]
    if structured:
        lines.append("--- DATABASE RESULTS (High Reliability) ---")
        for i, item in enumerate(structured, 1):
            row_str = ", ".join(f"{k}: {v}" for k, v in item["data"].items())
            lines.append(f"  {i}. {row_str}")
        lines.append("")

    # Doc results section
    docs = [d for d in fused["merged_data"] if d["type"] == "doc"]
    if docs:
        lines.append("--- DOCUMENT RESULTS (Medium Reliability) ---")
        for i, item in enumerate(docs, 1):
            lines.append(f"  {i}. {item['text']}")
        lines.append("")

    # Web results section
    webs = [d for d in fused["merged_data"] if d["type"] == "web"]
    if webs:
        lines.append("--- WEB RESULTS (Low Reliability) ---")
        for i, item in enumerate(webs, 1):
            lines.append(f"  {i}. [{item.get('title', '')}] {item['text']}")
        lines.append("")

    return "\n".join(lines)


def extract_raw_tool_data(trace: list) -> str:
    """
    Extract raw unfiltered tool outputs for ground-truth checking.
    Gives the LLM direct access to what tools actually returned.
    """
    lines = ["=== RAW TOOL OUTPUTS ==="]

    for step in trace[-6:]:
        tool = step.get("tool", "unknown")
        inp = step.get("input", "")
        output = step.get("output", {})

        lines.append(f"\n[{tool}] Input: {inp}")

        if not isinstance(output, dict):
            lines.append(f"  Result: {str(output)[:300]}")
            continue

        if "error" in output:
            lines.append(f"  ERROR: {output['error'][:200]}")
            continue

        if "rows" in output and "columns" in output:
            lines.append(f"  Columns: {output['columns']}")
            for row in output["rows"][:8]:
                row_dict = dict(zip(output["columns"], row))
                lines.append(f"  -> {row_dict}")
            total = output.get("row_count", 0)
            if total > 8:
                lines.append(f"  ... ({total} total rows)")

        elif "results" in output:
            for item in output["results"][:5]:
                if "text" in item:
                    lines.append(f"  -> {item['text'][:250]}")
                elif "snippet" in item:
                    lines.append(f"  -> [{item.get('title', '')}] {item['snippet'][:250]}")

        elif "message" in output:
            lines.append(f"  -> {output['message']}")

    return "\n".join(lines)