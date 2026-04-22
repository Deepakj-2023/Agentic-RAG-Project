# llm_brain.py : LLM interaction and decision parsing

import os
import json
import re
from pydantic import BaseModel
from typing import Literal, Optional, List, Dict
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from utils.db_utils import get_dynamic_schema

load_dotenv()

# Initialize ChatGroq
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.4
)

# --- Role 1: Planner (Decision Maker) ---
class ToolCall(BaseModel):
    name: Literal["search_docs", "query_data", "web_search"]
    input: str
    query_type: Optional[str] = None
    csv_name: Optional[str] = None

class PlannerDecision(BaseModel):
    action: Literal["chat", "tool_use"]
    reason: str
    tools: List[ToolCall] = []

# --- Role 2: Synthesizer (Answer Generator) ---
# (Produces natural text, no Pydantic needed)

# --- Role 3: Evaluator (Feedback Loop) ---
class EvaluationResult(BaseModel):
    sufficient: bool
    feedback: str = "No feedback provided."
    correction: Optional[str] = None
    next_action: Literal["web_search", "query_data", "search_docs", "none"] = "none"


PLANNER_PROMPT = """You are a Strategic Planner for a Sports Analysis Agent.
Your job is to analyze the user question and decide which tools (if any) are needed to find the answer.

=== TOOLS AVAILABLE ===
1. query_data: Best for structured, historical data from local CSV/SQL databases (IPL/PSL statistics, match winners, player stats).
2. search_docs: Best for semi-structured articles and in-depth reports stored in the local vector store.
3. web_search: Best for broad knowledge, real-time updates, and any information not present in local repositories.

=== DYNAMIC SCHEMA ===
{dynamic_schema}

=== RULES ===
- SELECT the best tool(s) based on where the required data is most likely to reside.
- You can use 'multi_tool' to fetch and compare data from multiple sources (e.g., comparing local historical stats with latest web news).
- Treat all tools as equal capabilities; choose based on the specific question and missing context from previous steps.
- If the first tool result is shallow, use a DIFFERENT tool to cross-verify or go deeper.

=== EXAMPLES ===
Q: "Who won IPL 2023?"
A: {
  "action": "tool_use",
  "reason": "I need to check the local database for the 2023 winner.",
  "tools": [{"name": "query_data", "input": "SELECT winner FROM ipl_matches WHERE season='2023' AND date=(SELECT MAX(date) FROM ipl_matches WHERE season='2023')", "query_type": "sql"}]
}

Q: "Top PSL player and FIFA 2018 winner"
A: {
  "action": "tool_use",
  "reason": "This is a multi-part question requiring database and web search.",
  "tools": [
    {"name": "query_data", "input": "SELECT Player, Runs FROM psl_batting ORDER BY Runs DESC LIMIT 1", "query_type": "sql"},
    {"name": "web_search", "input": "who won FIFA World Cup 2018"}
  ]
}

=== OUTPUT FORMAT ===
You MUST return ONLY a JSON object. No preamble, no explanation.
{
  "action": "tool_use",
  "reason": "...",
  "tools": [
    {"name": "query_data", "input": "...", "query_type": "sql", "csv_name": "match_stats"}
  ]
}
"""

SYNTHESIZER_PROMPT = """You are a sophisticated Sports AI Analyst. 
Your goal is to provide a comprehensive, natural, and insightful response.

=== MANDATORY RULES ===
1. USE THE PROVIDED DATA: You have detailed snippets and stats in the 'COLLECTED DATA' section. USE THEM.
2. DO NOT HALUCINATE: If the data says a player won an award, state it. If the data is missing, admit it.
3. BE SPECIFIC: Use names, scores, runs, and dates. Avoid "he had a good season". Say "he scored 741 runs and won the Orange Cap".
4. ANALYST INSIGHT: Always include a section '--- Analyst Insight ---' with a high-level conclusion.
5. NO GENERIC ADVICE: Do NOT tell the user to "check cricinfo" or "visit websites". YOU ARE THE ANALYST.
"""

EVALUATOR_PROMPT = """You are a Critical Quality Evaluator for an Agentic RAG system.
Your job is to scrutinize the current answer and decide if it's truly enough or if the agent needs to dig deeper.

=== EVALUATION CRITERIA (OBSESSED WITH EVIDENCE) ===
1. SPECIFICITY: Does the answer contain actual numbers, dates, and names? Generic phrases like "good form" or "key player" are NOT enough.
2. DEPTH: Did the tools provide enough detail, or was the result too shallow?
3. COMPLETENESS: Does it answer ALL parts of the user's question? 
4. NO GIVING UP: If the answer says "information not available" or "I don't know" for any part of the question, but there are UNUSED tools with likely capabilities, then sufficient MUST be FALSE.

=== OUTPUT FORMAT ===
You MUST return ONLY a JSON object with ALL these fields:
{{
  "sufficient": true | false,
  "feedback": "Critique focusing on missing metrics or shallow reasoning.",
  "correction": "Specific instruction for the Planner to fix the gaps.",
  "next_action": "web_search" | "query_data" | "search_docs" | "none"
}}
"""




def plan_action(question: str, context: str) -> PlannerDecision:
    """PLANNER ROLE: Decide which tools to use."""
    schema = get_dynamic_schema()
    prompt = PLANNER_PROMPT.replace("{dynamic_schema}", schema)
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Question: {question}\nHistory:\n{context}")
    ]
    response = llm.invoke(messages)
    content = _extract_json(response.content)
    try:
        return PlannerDecision(**json.loads(content))
    except Exception as e:
        # Fallback to chat if JSON fails
        print(f"[DEBUG] JSON Parse Error: {e}")
        print(f"[DEBUG] Raw Content: {response.content}")
        return PlannerDecision(action="chat", reason="JSON Parse Error", tools=[])

def synthesize_answer(question: str, data: str) -> str:
    """SYNTHESIZER ROLE: Generate final natural answer."""
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"Question: {question}\nData:\n{data}")
    ]
    return llm.invoke(messages).content.strip()

def evaluate_answer(question: str, answer: str, data: str) -> EvaluationResult:
    """EVALUATOR ROLE: Check if answer is sufficient."""
    messages = [
        SystemMessage(content=EVALUATOR_PROMPT),
        HumanMessage(content=f"Question: {question}\nAnswer: {answer}\nAvailable Data: {data}")
    ]
    response = llm.invoke(messages)
    content = _extract_json(response.content)
    try:
        return EvaluationResult(**json.loads(content))
    except:
        return EvaluationResult(sufficient=True, next_action="none")

def _extract_json(text: str) -> str:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text