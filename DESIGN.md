# Design Document — Multi-Tournament Sports Analysis Agent

## 1. Problem Statement

### Background

Many real sports questions cannot be answered from a single data source. Consider a question like:

> *"Who are the top 3 six-hitters in PSL history, and what do match reports say about their playing style?"*

Answering this correctly requires:
1. Pulling **precise statistics** (six counts, rankings) from a structured PSL database.
2. Retrieving **narrative context** (playing style, match highlights) from unstructured match report documents.
3. **Combining both** into one coherent, accurate answer.

A single RAG pipeline cannot do this well on its own. It either retrieves text documents and misses the exact numbers, or queries a database and misses the contextual explanation. The agent needs to look at the question, decide what *kind* of source will best answer it, retrieve from that source, and then decide whether it needs to look somewhere else before composing the final answer.

This problem is further complicated by:

- **Heterogeneous data formats** — sports data exists as SQLite tables (PSL records), large CSV files (IPL ball-by-ball, FIFA player attributes), unstructured text documents (match reports, player profiles), and live web content (latest news).
- **Ambiguous or vague queries** — users may ask "stats" or "Who is Kohli?" without specifying which tournament or stat type, requiring the agent to infer intent.
- **Data gaps and boundaries** — some player data simply does not exist in local sources (e.g., Test cricket stats for retired players), requiring honest acknowledgement rather than hallucination.
- **Safety and scope** — the agent must refuse non-sports questions, future predictions, and unethical requests without crashing or fabricating responses.

### Goal

The objective of this project is to build a **Multi-Tournament Sports Analysis Agent** that:

- Accepts any sports-related question in plain English — no SQL, no code, no schema knowledge required from the user.
- Dynamically selects and chains the right data sources: structured DB (SQL), structured CSV (Pandas), unstructured documents (FAISS vector search), or live web (Tavily API).
- Executes queries, cross-verifies results across sources, and synthesizes a coherent, data-grounded final answer.
- Gracefully refuses questions that are out of scope (non-sports topics, future predictions, unethical requests).
- Provides full traceability — every answer includes the steps, tools, and data used to produce it.

The system covers three major sports tournaments: **IPL** (Indian Premier League), **PSL** (Pakistan Super League), and **FIFA** (international football), with live web search for real-time news and events.

---

## 2. Data Sources

The agent has access to four distinct types of data sources:

### 2.1 Structured Data — IPL (CSV / Pandas)

| Property | Details |
|---|---|
| File | `data/structure_data/IPL.csv` |
| Size | ~110 MB (ball-by-ball data) |
| Format | CSV (Pandas) |
| Key Columns | `batter`, `bowler`, `runs_batter`, `runs_total`, `balls_faced`, `match_id`, `wicket_kind` |
| Use Cases | Top run scorers, wicket takers, aggregated career stats per player |

### 2.2 Structured Data — PSL (SQLite Database)

| Property | Details |
|---|---|
| File | `data/sports_data.db` |
| Format | SQLite |
| Tables | `psl_most_runs_by_a_player`, `psl_most_wickets_in_psl`, `psl_highest_individual_score`, `psl_most_sixes_in_psl_history`, `psl_lowest_totals`, `psl_best_bowling_figures_in_an_innings_in_psl`, `psl_result_summary_of_teams` |
| Use Cases | Historical records, rankings, team results |

### 2.3 Structured Data — FIFA (CSV / Pandas)

| Property | Details |
|---|---|
| File | `data/structure_data/player_stats.csv` |
| Size | ~904 KB |
| Format | CSV (Pandas) |
| Key Columns | `player`, `country`, `club`, `age`, `ball_control`, `dribbling`, `marking`, `slide_tackle`, `reactions`, `att_position`, `vision`, `composure`, `acceleration`, `sprint_speed` |
| Use Cases | Player attribute comparisons, top-rated players per skill |

### 2.4 Unstructured Data — Sports Documents (Vector Store / FAISS)

| Property | Details |
|---|---|
| Directory | `data/unstructured/` |
| Index | `faiss.index` + `meta.pkl` |
| Embedding Model | `SentenceTransformer("all-MiniLM-L6-v2")` |
| Documents | Babar Azam PSL 2024 highlights, FIFA 2022 World Cup Final match report, IPL 2024 season review, Lionel Messi 2024-25 season stats, Virat Kohli IPL 2024 performance |
| Use Cases | Biographical info, match narratives, player playing style descriptions |

### 2.5 Live Web — Tavily Search API

| Property | Details |
|---|---|
| API | Tavily Search (`search_depth="basic"`, `max_results=5`) |
| Use Cases | Latest news, real-time data not present in local sources, cross-verification of records |
| Fallback | Used when `query_data` or `search_docs` returns no results or suspicious data |

---

## 3. Functional Requirements — Tools

The agent exposes four functional capabilities (tools), each with a distinct purpose and interface.

### 3.1 `query_data` — Smart Query Tool ⭐

This is the most sophisticated tool in the system. Unlike a traditional query tool that expects pre-written SQL or Pandas code, `query_data` accepts a **natural language intent** and internally uses an LLM to translate that intent into executable code — then executes it and returns structured results.

**Why it is special (Smart Tool):**

1. **Intent → Code Translation**: The Planner never writes SQL or Pandas. It provides a human-readable description like *"Find the player with the most runs in PSL history"*. The Smart Tool's internal LLM reads the full schema registry and generates the correct SQL or Pandas code.
2. **Self-Correction**: If the generated code fails (e.g., wrong column name), the tool automatically retries with the error message included as context, allowing the LLM to correct the code without human intervention.
3. **Schema Awareness**: The tool loads `data/schema_registry.json` at runtime, giving the code-generator full visibility into all tables and columns for all datasets.
4. **Dual Backend**: The same tool handles both SQL (SQLite) and Pandas (CSV) via the `query_type` parameter.

**Interface:**

```
query_data(
  query_type: "sql" | "pandas",
  intent:     "natural language description of what to retrieve",
  csv_name:   "IPL.csv" | "player_stats.csv"  (required for pandas)
)
```

**Internal Flow:**

```
Intent (NL) → LLM Code Generator → SQL or Pandas Code
                                          ↓
                              Execute against DB / CSV
                                          ↓
                           Error? → Retry with error feedback
                                          ↓
                              Return structured result dict
```

**Output Format:**
```json
{
  "source": "SQLite DB | IPL.csv | player_stats.csv",
  "columns": ["Player", "Runs"],
  "rows": [["Babar Azam", 3792]],
  "row_count": 1,
  "query_used": "SELECT ..."
}
```

---

### 3.2 `search_docs` — Vector Document Search Tool

Searches an indexed FAISS vector store built from curated sports documents (match reports, player profiles, season reviews).

**How it works:**
1. Takes a natural language query string.
2. Encodes it using `SentenceTransformer("all-MiniLM-L6-v2")`.
3. Performs cosine similarity search over the FAISS index.
4. Returns the top-k most relevant text chunks with source filenames.

**Best used for:** narrative content, biographical information, playing styles, match summaries.

**Output Format:**
```json
{
  "query": "Babar Azam PSL 2024 performance",
  "results": [{"text": "...", "source": "babar_azam_psl_2024...txt"}]
}
```

---

### 3.3 `web_search` — Live Web Search Tool

Calls the **Tavily Search API** for real-time information not available in local data sources.

**How it works:**
1. Accepts a search query string.
2. Sends a `basic` depth search to Tavily (fast, low-cost).
3. Returns top 5 results with title, snippet/content, URL, and published date.

**Best used for:** latest news, event results, data not covered by local databases.

**Output Format:**
```json
{
  "query": "Babar Azam current form 2025",
  "results": [{"title": "...", "snippet": "...", "url": "..."}]
}
```

---

### 3.4 `chat` — Direct Response (No Tool)

Used when the Planner determines that **no tool should be invoked** — e.g., for out-of-scope questions (non-sports), future predictions, or unsafe requests. The Synthesizer generates a polite, contextual refusal directly.

---

## 4. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                  (main.py — CLI Input Loop)                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │  User Question (natural language)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT LOOP  (agent_loop.py)                  │
│                                                                 │
│   ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐    |
│   │   PLANNER   │───▶│  TOOL EXECUTOR   │───▶│  EVALUATOR |    │
│   │ (llm_brain) │    │  (agent_loop)    │    │ (llm_brain) │    │
│   └─────────────┘    └──────────────────┘    └──────┬──────┘    │
│         ▲                    │                       │          │
│         │                    ▼                       │          │
│   Context Manager     ┌──────────────┐        Sufficient?       │
│   (context.py)        │ RESULT FUSER │         │       │        │
│                       │  (fusion.py) │         ▼       ▼        │
│                       └──────┬───────┘      YES      NO         |
│                              │               │        │         │
│                       SYNTHESIZER            │     Update       │
│                       (llm_brain)            │     Context      │
│                              │               │     Retry        │
│                              ▼               │                  │
└──────────────────────────────┼───────────────┼──────────────────┘
                               │               │
                               └───────────────┘
                                       │
                               FINAL ANSWER
                              (with trace log)
```

```
                        TOOLS LAYER
    ┌──────────────┬────────────────┬───────────────┐
    │  query_data  │  search_docs   │   web_search  │
    │  (Smart Tool)│  (FAISS/SBERT) │  (Tavily API) │
    └──────┬───────┴────────┬───────┴───────┬───────┘
           │                │               │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌────▼──────┐
    │ SQLite DB   │  │ FAISS Index │  │Tavily API │
    │ IPL CSV     │  │ (docs/)     │  │(live web) │
    │ FIFA CSV    │  └─────────────┘  └───────────┘
    └─────────────┘
```

---

## 5. System Flow Diagram

```
User sends a question
        │
        ▼
  ┌─────────────────────────────────────────────────┐
  │  PLANNER (LLM)                                  │
  │  Reads: question + previous context             │
  │  Decides: action = "chat" or "tool_use"         │
  │  Outputs: list of tool calls with intents       │
  └─────────────────┬───────────────────────────────┘
                    │
          ┌─────────┴──────────┐
          │                    │
   action = "chat"    action = "tool_use"
          │                    │
   Synthesizer          ┌──────▼───────────────────────────┐
   (direct answer)      │  For each tool call in parallel: │
          │             │  1. Check for duplicate → skip   │
          │             │  2. Execute tool                 │
          │             │  3. Append result to trace       |
          │             └──────────────┬───────────────────┘
          │                            │
          │                   ┌────────▼────────┐
          │                   │  RESULT FUSION  │
          │                   │  DB > Docs > Web│
          │                   └────────┬────────┘
          │                            │
          │                   ┌────────▼────────┐
          │                   │  SYNTHESIZER    │
          │                   │  (LLM Analyst)  │
          │                   └────────┬────────┘
          │                            │
          │                   ┌────────▼────────┐
          │                   │   EVALUATOR     │
          │                   │  sufficient?    │
          │                   └──────┬──────┬───┘
          │                         │      │
          │                       YES      NO
          │                         │      │
          │                         │   Update feedback
          │                         │   Re-plan (next step)
          │                         │   Max 8 steps total
          ▼                         ▼
       RETURN                   RETURN
      ANSWER                   ANSWER
```

---

## 6. Tech Stack

| Component | Technology | Version / Notes |
|---|---|---|
| **Language** | Python | 3.11+ |
| **LLM Provider** | Groq API | `llama-3.1-8b-instant`, temperature=0.3 |
| **LLM Framework** | LangChain | `langchain-core`, `langchain-groq` |
| **Embedding Model** | SentenceTransformers | `all-MiniLM-L6-v2` (384-dim) |
| **Vector Store** | FAISS | `faiss-cpu`, persisted as `faiss.index` + `meta.pkl` |
| **Structured DB** | SQLite | `sports_data.db` (PSL tables) |
| **CSV Processing** | Pandas | IPL.csv (110 MB), player_stats.csv |
| **Web Search** | Tavily API | `tavily-python`, basic depth, 5 results |
| **Data Validation** | Pydantic | `BaseModel` for PlannerDecision, ToolCall, EvaluationResult |
| **Environment** | python-dotenv | `.env` for API keys |
| **Package Manager** | uv / pip | `pyproject.toml` |
| **Schema Registry** | JSON | `data/schema_registry.json`, `data/tool_registry.json` |

---

## 7. Component Design Details

### 7.1 Planner (llm_brain.py — `plan_action`)

The Planner is an LLM-driven reasoning engine with a structured prompt that enforces:

- **Scope rules**: Only sports-related questions are handled. Non-sports → `action: "chat"`.
- **No prediction rule**: Future events are declined.
- **Multi-tool parallelism**: The Planner can emit multiple tool calls per step (e.g., SQL + web simultaneously).
- **Mandatory cross-verification**: Record claims (highest, most, best) must use both `query_data` AND `web_search`.
- **Intent-only output**: The Planner never writes SQL or Pandas code — only natural language intents.

**Output schema (Pydantic):**
```python
class PlannerDecision:
    thought: str          # Reasoning trace
    action: "chat" | "tool_use"
    tools: List[ToolCall] # Tool calls with intent, query_type, csv_name
```

### 7.2 Synthesizer (llm_brain.py — `synthesize_answer`)

A Sports Analyst persona that reads fused evidence and produces a coherent answer. Prioritizes DATABASE results over web. Refuses non-sports questions. Outputs answers tagged with sources.

### 7.3 Evaluator (llm_brain.py — `evaluate_answer`)

Checks if the synthesized answer accurately reflects the evidence (tool outputs). Uses rules to:
- Accept minor formatting differences (commas, asterisks in scores).
- Require multi-source evidence for record claims.
- Prevent infinite loops by marking answers as `sufficient` when improvement is marginal.

**Output schema:**
```python
class EvaluationResult:
    sufficient: bool      # True = accept answer, False = retry
    feedback: str         # Why it passed/failed
    correction: str       # Guidance for next planning step
    output: str           # The refined final answer
```

### 7.4 Result Fusion (fusion.py)

Merges all tool outputs into a priority-ordered evidence block:
1. **Structured DB data** (highest reliability)
2. **Document search results** (medium reliability)
3. **Web search results** (lower reliability, most recent)

Deduplicates results and formats them for the Synthesizer LLM.

### 7.5 Context Manager (context.py)

Maintains a per-run state dictionary. Every tool call result is appended. The context string is passed to the Planner each iteration (trimmed to 1,200 chars to avoid token limits), enabling genuine multi-step reasoning.

---

## 8. Evaluation & Expected Outcomes

### 8.1 Test Categories and Expected Behaviors

| Category | Count | Expected Behavior |
|---|---|---|
| **Single-Tool** | 7 | Correct data retrieval from a single SQL or Pandas source with optional web verification |
| **Multi-Tool** | 7 | Parallel tool invocation, result fusion, and coherent comparative answers |
| **Refusal** | 4 | 100% refusal rate for non-sports, unethical, and future-prediction queries |
| **Edge-Case** | 4 | Graceful handling of ambiguity, missing data, wrong-domain sports, and future dates |

### 8.2 Key Design Goals vs. Outcomes

| Design Goal | Mechanism | Outcome |
|---|---|---|
| No SQL/code from user | Smart Tool (LLM → code) | ✅ User provides only natural language |
| No hallucination | Evaluator + cross-verification rule | ✅ Data-grounded answers; refusals when uncertain |
| Multi-source verification | Planner rule: records must use `query_data` + `web_search` | ✅ Applied for S1–S7, M1–M7 |
| Graceful error recovery | Smart Tool self-correction (2 retries) | ✅ SQL column errors recovered in M5 |
| Scope enforcement | Planner `SCOPE RULE` + `REFUSAL` instructions | ✅ 100% refusal on R1–R4, E1 |
| Traceability | Full trace log per response | ✅ Every answer includes step-by-step tool trace |
| Max steps guard | `MAX_STEPS = 8` in agent_loop | ✅ Agent never runs indefinitely |

### 8.3 Observed Limitations

- **IPL historical players** (e.g., Sachin Tendulkar) who retired before the data collection period appear as "not found" in IPL.csv.
- **Test cricket data** is not included in any local database — acknowledged transparently when queried.
- **Web search connectivity** can fail intermittently (connection timeouts), reducing cross-verification reliability in those runs.
- **PSL schema naming** caused SQL generation errors when column names contained special characters (`"6s"`, `"Match Date"`), mitigated by the Smart Tool's self-correction and explicit schema rules.
- **Ambiguous queries** (e.g., "stats") are handled but produce generic responses; clarification prompting would improve user experience.

---

## 9. Project Structure

```
Proadapt-Project/
│
├── agent/
│   ├── agent_loop.py        # Core execution engine (MAX_STEPS=8, tool dispatch)
│   ├── context.py           # Per-run state management
│   ├── fusion.py            # Multi-source result merging (DB > Docs > Web)
│   └── llm_brain.py         # Planner, Synthesizer, Evaluator LLM prompts & functions
│
├── tools/
│   ├── query_tool.py        # Smart Query Tool (NL intent → SQL/Pandas → result)
│   ├── search_doc_tool.py   # FAISS vector search over unstructured docs
│   └── web_search_tool.py   # Tavily API web search
│
├── data/
│   ├── sports_data.db            # SQLite: PSL tables
│   ├── schema_registry.json      # All table/column metadata for Smart Tool
│   ├── tool_registry.json        # Tool definitions
│   ├── knowledge_graph.json      # Entity relationships
│   ├── structure_data/
│   │   ├── IPL.csv               # Ball-by-ball IPL data (~110 MB)
│   │   └── player_stats.csv      # FIFA player attributes (~900 KB)
│   └── unstructured/
│       ├── babar_azam_psl_2024_records_...txt
│       ├── fifa_world_cup_2022_full_final_...txt
│       ├── ipl_2024_season_review_...txt
│       ├── lionel_messi_2024-2025_season_...txt
│       └── virat_kohli_ipl_2024_performance_...txt
│
├── utils/
│   └── vector_store.py      # FAISS index loading + SentenceTransformer embedding
│
├── main.py                  # CLI entry point (interactive Q&A loop)
├── evaluation_runner.py     # 22-question automated evaluation suite
├── output_document.json     # Captured Q&A pairs with full traces
├── faiss.index              # Persisted FAISS vector index
├── meta.pkl                 # FAISS document metadata
├── DESIGN.md                # This document
├── EVALUATION.md            # Evaluation report
└── README.md                # Setup and overview
```

---

*Document prepared for the Multi-Tournament Sports Analysis Agent — Proadapt Project.*
