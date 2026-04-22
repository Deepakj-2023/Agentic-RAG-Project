# fusion.py : Merge, deduplicate, and rank results from multiple tools/sources

import json


def fuse_results(trace: list, question: str) -> dict:
    """
    Take all collected tool outputs from the trace and produce
    a merged, deduplicated summary for the LLM to use in its final answer.
    
    Returns a dict with:
      - merged_data: combined key findings
      - sources: list of sources used
      - conflicts: any conflicting info detected
    """
    merged_data = []
    sources = []
    conflicts = []
    seen_values = set()

    for step in trace:
        tool = step.get("tool", "")
        output = step.get("output", {})

        if isinstance(output, str):
            # Error or plain text
            if "error" not in output.lower():
                merged_data.append({"tool": tool, "data": output})
            continue

        if not isinstance(output, dict):
            continue

        # Track source
        source = output.get("source", tool)
        if source not in sources:
            sources.append(source)

        # Handle SQL/Pandas results
        if "rows" in output and "columns" in output:
            columns = output["columns"]
            rows = output["rows"]
            row_count = output.get("row_count", len(rows))

            for row in rows:
                row_key = str(row)
                if row_key not in seen_values:
                    seen_values.add(row_key)
                    row_dict = dict(zip(columns, row)) if len(columns) == len(row) else {"data": row}
                    row_dict["_source"] = source
                    merged_data.append(row_dict)

        # Handle search_docs results
        if "results" in output and isinstance(output["results"], list):
            for doc in output["results"]:
                if isinstance(doc, dict):
                    text = doc.get("text", "")
                    doc_source = doc.get("source", "document")
                    if text and text not in seen_values:
                        seen_values.add(text)
                        merged_data.append({
                            "tool": "search_docs",
                            "text": text[:300],
                            "_source": doc_source
                        })
                elif isinstance(doc, str) and doc not in seen_values:
                    seen_values.add(doc)
                    merged_data.append({"tool": "search_docs", "text": doc[:300]})

        # Handle web_search results
        if "results" in output and tool == "web_search":
            for item in output["results"]:
                if isinstance(item, dict):
                    snippet = item.get("snippet", "")
                    if snippet and snippet not in seen_values:
                        seen_values.add(snippet)
                        merged_data.append({
                            "tool": "web_search",
                            "title": item.get("title", ""),
                            "text": snippet[:300],
                            "url": item.get("url", ""),
                            "_source": "web"
                        })

    return {
        "merged_data": merged_data[:15],  # Cap to avoid token overflow
        "sources": sources,
        "conflicts": conflicts,
        "total_items": len(merged_data)
    }


def format_fused_for_llm(fused: dict) -> str:
    """Format fused results into a clean string for the LLM."""
    lines = ["=== FUSED DATA FROM ALL TOOLS ==="]
    lines.append(f"Sources used: {', '.join(fused['sources'])}")
    lines.append(f"Total data items: {fused['total_items']}")

    if fused["conflicts"]:
        lines.append(f"⚠ Conflicts detected: {fused['conflicts']}")

    lines.append("")
    for i, item in enumerate(fused["merged_data"], 1):
        source = item.pop("_source", "unknown")
        tool = item.pop("tool", "unknown")
        
        # Build a clean readable string
        parts = []
        if "text" in item: parts.append(item.pop("text"))
        if "title" in item: parts.append(f"Title: {item.pop('title')}")
        
        # Add remaining fields
        for k, v in item.items():
            if k != "url": parts.append(f"{k}: {v}")
            
        content = " | ".join(parts)
        url_part = f" (URL: {item.get('url')})" if "url" in item else ""
        lines.append(f"[{i}] SOURCE: {source} | CONTENT: {content}{url_part}")

    return "\n".join(lines)
