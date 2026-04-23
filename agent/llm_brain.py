import os
import json
from pydantic import BaseModel
from typing import Literal, Optional, List
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# -------- LLM --------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

# -------- MODELS --------
class ToolCall(BaseModel):
    name: Literal["search_docs", "query_data", "web_search"]
    input: str
    query_type: Optional[str] = None
    csv_name: Optional[str] = None

class PlannerDecision(BaseModel):
    thought: str
    action: Literal["chat", "tool_use"]
    tools: List[ToolCall] = []

class EvaluationResult(BaseModel):
    sufficient: bool
    feedback: str
    correction: Optional[str] = None
    output: str = ""

# -------- LOAD REGISTRY --------
def load_tool_registry():
    with open("data/tool_registry.json") as f:
        return json.dumps(json.load(f), indent=2)

def load_schema_registry():
    with open("data/schema_registry.json") as f:
        return json.load(f)

def load_compact_schema():
    """Compact schema with table/column names only — no sample data."""
    schema = load_schema_registry()
    lines = []

    for dataset_name, dataset_info in schema.items():
        dtype = dataset_info.get("type", "unknown")

        if dtype == "pandas":
            path = dataset_info.get("path", "")
            csv_name = path.split("Proadapt-Project/data/")[-1] if "Proadapt-Project" in path else path
            cols = list(dataset_info.get("columns", {}).keys())
            cols = [c for c in cols if c != "Unnamed: 0"]
            lines.append(f"📊 {dataset_name.upper()} (type=pandas, csv_name=\"{csv_name}\"):")
            lines.append(f"   Columns: {', '.join(cols[:25])}")
            lines.append("")

        elif "tables" in dataset_info:
            tables = dataset_info.get("tables", {})
            lines.append(f"📊 {dataset_name.upper()} (type=sql):")
            for table_name, table_info in tables.items():
                cols = list(table_info.get("columns", {}).keys())
                lines.append(f"   Table: {table_name}")
                lines.append(f"   Columns: {', '.join(cols)}")
            lines.append("")

    return "\n".join(lines)

def _get_psl_table_names():
    try:
        schema = load_schema_registry()
        psl = schema.get("psl_db", {}).get("tables", {})
        return ", ".join(psl.keys())
    except Exception:
        return "psl_most_runs_by_a_player, psl_highest_individual_score"

# ────────────────────────────────────────────────────────────
# PLANNER PROMPT
# ────────────────────────────────────────────────────────────

PLANNER_PROMPT = """
    You are a reasoning-based Sports Analytics Planner.
Your job is to create a step-by-step plan to answer the user's question.
For each step, you will select the appropriate tool and provide a clear "intent" for that tool.
AVAILABLE DATASETS (High Level):
1. IPL (Structured): Player stats, ball-by-ball, match results. (Pandas: "IPL.csv")
2. PSL (Structured): Highest scores, most runs, wickets, team results. (SQL: "psl_db")
3. FIFA (Structured): Player attributes, skills, club info. (Pandas: "player_stats.csv")
4. Sports Docs (Unstructured): Biographical info, descriptions, context.
5. Web (Live/Latest): Latest news, missing data from local sources.
---
TOOLS PURPOSE:
- query_data:
  Use for structured stats (runs, wickets, scores, rankings).
  You must provide:
  1. "input": A natural language "intent" (e.g., "Find most runs in PSL history").
  2. "query_type": "sql" or "pandas".
  3. "csv_name": Use "IPL.csv" or "player_stats.csv" if query_type is pandas.
- search_docs:
  Use for descriptions, explanations, player info, or "Who is X?" questions.
  "input": The search query.
- web_search:
  Use for live info or when other tools fail.
  "input": The search query.
---
IMPORTANT RULES:
- You are a PLANNER. Break down complex questions.
- If a question is about a person ("Who is Kohli?"), ALWAYS start with search_docs or web_search to identify them first.
- If the tool result is "No results", pivot to a different tool (e.g., from DB to Web).
- DO NOT generate code. The tools generate their own code internally.

FEW-SHOT EXAMPLES:
Q: Who is Virat?
{
  "thought": "I need to find biographical info and then check for stats.",
  "action": "tool_use",
  "tools": [
    {"name": "search_docs", "input": "Biographical information about Virat Kohli"},
    {"name": "query_data", "input": "Find career IPL stats for Virat Kohli", "query_type": "pandas", "csv_name": "IPL.csv"}
  ]
}
Q: Compare PSL vs IPL top scorers
{
  "thought": "I need to get the top run scorers from both PSL (SQL) and IPL (Pandas).",
  "action": "tool_use",
  "tools": [
    {"name": "query_data", "input": "Find the player with the most runs in PSL history", "query_type": "sql"},
    {"name": "query_data", "input": "Find the player with the most runs in IPL history", "query_type": "pandas", "csv_name": "IPL.csv"}
  ]
}

---

OUTPUT FORMAT (JSON ONLY):

{
  "thought": "...reasoning...",
  "action": "tool_use",
  "tools": [
    {"name": "search_docs", "input": "..."},
    {"name": "query_data", "input": "...", "query_type": "...", "csv_name": "..."}
  ]
}
"""

# ────────────────────────────────────────
# SYNTHESIZER PROMPT
# ────────────────────────────────────────

SYNTHESIZER_PROMPT = """
You are a Sports Analyst. Answer using ONLY the provided data. Quote exact numbers. Prefer DATABASE over web results. If no relevant data, say so.

Format:
--- Analyst Insight ---
[Answer with exact data]
Sources: [sources used]
"""

# ────────────────────────────────────────
# EVALUATOR PROMPT
# ────────────────────────────────────────

EVALUATOR_PROMPT = """
You are an evaluator checking if an answer is correct based on evidence.

Rules:
1. The "RAW TOOL OUTPUTS" are the ground truth. Accept variations like "145" vs "145*" if they refer to the same value.
2. "Sufficient" = The answer is grounded in tool evidence. If the tool result confirms the answer (e.g. Jason Roy 145), mark as sufficient.
3. "Correction" = Only suggest a correction if the data is actually missing or clearly wrong. 
4. DO NOT loop infinitely if the answer is already correct. If the answer is correct but the "source" name is slightly different, mark as sufficient.
5. If the agent finds the answer via web_search because query_data failed, that is ACCEPTABLE.

JSON Schema:
{
  "sufficient": true/false,
  "feedback": "Why it is sufficient or not",
  "correction": "Fix suggestion (if any)",
  "output": "Final answer"
}
"""

# ────────────────────────────────────────
# FUNCTIONS
# ────────────────────────────────────────

def plan_action(question: str, context: str) -> PlannerDecision:
    prompt = PLANNER_PROMPT

    context_trimmed = context[:1200] if len(context) > 1200 else context

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Question: {question}\n\nPrevious Steps:\n{context_trimmed}")
    ]

    response = llm.invoke(messages)
    content = _extract_json(response.content)

    try:
        decision = PlannerDecision(**json.loads(content))
        if decision.action not in ["chat", "tool_use"]:
            decision.action = "chat"
        return decision
    except Exception as e:
        print("Planner ERROR:", e)
        print("Raw output:", response.content[:300])
        return PlannerDecision(thought="Fallback to chat", action="chat", tools=[])


def synthesize_answer(question: str, data: str) -> str:
    data_trimmed = data[:2500] if len(data) > 2500 else data
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"Question: {question}\n\nEvidence Data:\n{data_trimmed}")
    ]
    return llm.invoke(messages).content.strip()


def evaluate_answer(question: str, answer: str, data: str) -> EvaluationResult:
    data_trimmed = data[:1500] if len(data) > 1500 else data
    messages = [
        SystemMessage(content=EVALUATOR_PROMPT),
        HumanMessage(content=f"Question: {question}\n\nAnswer:\n{answer}\n\nEvidence:\n{data_trimmed}")
    ]

    response = llm.invoke(messages)
    raw = response.content
    content = _extract_json(raw)

    try:
        return EvaluationResult(**json.loads(content))
    except Exception as e:
        print(f"[EVAL PARSE WARN] {e}")
        raw_lower = raw.lower()
        if '"sufficient": true' in raw_lower or '"sufficient":true' in raw_lower:
            return EvaluationResult(sufficient=True, feedback="Parsed from raw", correction=None, output=answer)
        return EvaluationResult(sufficient=False, feedback="Evaluation parsing failed", correction=None, output=answer)


def _extract_json(text: str) -> str:
    # Remove markdown code blocks if present
    text = text.replace("```json", "").replace("```", "").strip()
    
    # Simple Python to JSON conversion for common mishaps
    text = text.replace("None", "null").replace("True", "true").replace("False", "false")
    
    # Find the outermost curly braces
    start = text.find("{")
    end = text.rfind("}")
    
    if start == -1 or end == -1:
        return text
        
    return text[start:end+1]