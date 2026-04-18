# llm_brain.py : LLM interaction and decision parsing

import os
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.messages import SystemMessage, HumanMessage

load_dotenv()

#  Initialize ChatGroq
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

#  Structured Output Model
class Decision(BaseModel):
    action: Literal["search_docs", "query_data", "web_search", "final"]
    input: str


SYSTEM_PROMPT = """
You are an intelligent agent.

You have 3 tools:
- search_docs → for document explanations
- query_data → for structured data
- web_search → for current information

Responsibilities:
1. Decide which tool to use
2. Decide if result is enough or not to answer the User Question :{input}

Rules:
- NEVER guess
- Use tools when needed
- If enough → return final
- If not → call another tool
- If impossible → say "I cannot answer"

Return STRICT JSON:
{
  "action": "...",
  "input": "..."
}
"""


def call_llm(question: str, context: str) -> Decision:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Question: {question}\nContext: {context}")
    ]

    response = llm.invoke(messages)

    content = response.content

    try:
        return Decision.model_validate_json(content)
    except Exception:
        return Decision(action="final", input="I cannot parse response")