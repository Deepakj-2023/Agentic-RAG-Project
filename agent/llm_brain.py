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
    temperature=0.2
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
    output: str

# -------- LOAD REGISTRY --------
def load_tool_registry():
    with open("data/tool_registry.json") as f:
        return json.dumps(json.load(f), indent=2)

def load_schema_registry():
    with open("data/schema_registry.json") as f:
        return json.dumps(json.load(f), indent=2)

# -------- PROMPTS --------

PLANNER_PROMPT = """
You are a STRICT planning agent.

You MUST return JSON only.

VALID actions:
- "chat"
- "tool_use"

NEVER output anything else like "wait", "thinking", etc.

Rules:
- Greeting/simple question → action = "chat"
- Data question → action = "tool_use"
- If tool_use → MUST provide at least one tool
- Do NOT hallucinate tools
- Do NOT repeat same query

Tools:
{tool_registry}

Schemas:
{schema_registry}

OUTPUT FORMAT:
{
  "thought": "...",
  "action": "chat" OR "tool_use",
  "tools": []
}
"""

SYNTHESIZER_PROMPT = """
You are a Sports AI Analyst.

Rules:
- Use ONLY given data
- If data is irrelevant → say "No relevant data found"
- DO NOT hallucinate
- Be precise

Format:
--- Analyst Insight ---
"""

EVALUATOR_PROMPT = """
You are a STRICT evaluator.

Mark sufficient = TRUE ONLY IF:
- Answer directly matches question
- Data is relevant
- No hallucination

If wrong or irrelevant → sufficient = FALSE

OUTPUT JSON:
{
  "sufficient": true or false,
  "feedback": "...",
  "correction": "...",
  "output": "..."
}
"""

# -------- FUNCTIONS --------

def plan_action(question: str, context: str) -> PlannerDecision:
    prompt = PLANNER_PROMPT.format(
        tool_registry=load_tool_registry(),
        schema_registry=load_schema_registry()
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Question: {question}\nContext:\n{context[-1500:]}")
    ]

    response = llm.invoke(messages)
    content = _extract_json(response.content)

    try:
        decision = PlannerDecision(**json.loads(content))

        # 🔥 SAFETY FIX
        if decision.action not in ["chat", "tool_use"]:
            decision.action = "chat"

        return decision

    except Exception as e:
        print("Planner ERROR:", e)

        # ✅ SAFE FALLBACK
        return PlannerDecision(
            thought="Fallback to chat",
            action="chat",
            tools=[]
        )


def synthesize_answer(question: str, data: str) -> str:
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"Question: {question}\nData:\n{data[:2000]}")
    ]
    return llm.invoke(messages).content.strip()


def evaluate_answer(question: str, answer: str, data: str) -> EvaluationResult:
    messages = [
        SystemMessage(content=EVALUATOR_PROMPT),
        HumanMessage(content=f"Q: {question}\nAnswer: {answer}\nData: {data[:2000]}")
    ]

    response = llm.invoke(messages)
    content = _extract_json(response.content)

    try:
        return EvaluationResult(**json.loads(content))
    except Exception:
        return EvaluationResult(
            sufficient=False,
            feedback="Evaluation parsing failed",
            correction=None,
            output=answer
        )


def _extract_json(text: str) -> str:
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    return text[start:end+1] if start != -1 and end != -1 else text