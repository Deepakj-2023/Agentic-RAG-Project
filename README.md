# 🏏 Multi-Tournament Sports Analysis Agent

> An **Agentic RAG system** built from scratch — no LangGraph, no AutoGen, no pre-built agent framework. A custom agent that thinks step-by-step, selects tools dynamically, retrieves from multiple heterogeneous sources, self-evaluates its own answers, and corrects itself before responding.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Core-1C3C3C?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-llama--3.1--8b-F55036?style=for-the-badge)
![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-00ADD8?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-PSL_Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Tavily](https://img.shields.io/badge/Tavily-Live_Web_Search-4A90E2?style=for-the-badge)

---

## 📌 What is Agentic RAG?

Standard RAG (Retrieval-Augmented Generation) retrieves once from a single source, then generates. It cannot decide *which* source to use, cannot cross-verify, and cannot recover from errors.

**Agentic RAG** wraps retrieval inside an autonomous agent loop:

```
Standard RAG:   Question → Retrieve → Generate → Answer

Agentic RAG:    Question
                    ↓
                PLANNER decides: which tool? which source?
                    ↓
                Tool executes (SQL / CSV / Docs / Web)
                    ↓
                EVALUATOR checks: is the answer grounded in evidence?
                    ↓ NO → re-plan
                    ↓ YES
                SYNTHESIZER produces final answer
                    ↓
                Answer + full trace
```

The agent can run **up to 8 reasoning steps**, use **multiple tools in parallel**, **self-correct failed queries**, and **refuse out-of-scope questions** — all without any human intervention.

---

## 🚩 The Problem

Many real sports questions cannot be answered from a single data source. Consider:

> *"Who are the top 3 six-hitters in PSL history, and what do match reports say about their playing style?"*

This requires:
1. **Exact statistics** → structured PSL database (SQL)
2. **Narrative context** → unstructured match report documents (FAISS vector search)
3. **Fused answer** combining both into one coherent response

A single RAG pipeline cannot do this — it either retrieves numbers and misses the story, or retrieves the story and misses the numbers. An agent must decide what to use, retrieve from each, and combine.

**Additional challenges:**
- Data lives in heterogeneous formats: SQLite, large CSVs (~110 MB), `.txt` documents, and the live web
- Some queries are vague ("stats"), out-of-domain ("NBA runs"), or unsafe ("hack a website") — each needs a different response strategy
- Structured data schemas are complex and error-prone — the agent must self-correct failed queries

---

## 🗂️ Data Sources

| Source | Format | Coverage |
|--------|--------|----------|
| `data/sports_data.db` | SQLite | PSL records: runs, wickets, sixes, scores, team wins |
| `data/structure_data/IPL.csv` | CSV (~110 MB) | Ball-by-ball IPL data across all seasons |
| `data/structure_data/player_stats.csv` | CSV (~900 KB) | FIFA player attributes (dribbling, speed, composure…) |
| `data/unstructured/*.txt` | Plain text (FAISS indexed) | Match reports, player profiles, season reviews |
| Tavily Search API | Live web | Latest news, real-time data, cross-verification |
| `data/knowledge_graph.json` | JSON | Precomputed facts for fast lookup (IPL champions, PSL records) |

**Unstructured documents indexed:**
- Babar Azam PSL 2024 highlights
- FIFA 2022 World Cup Final match report (Wikipedia)
- IPL 2024 season review
- Lionel Messi 2024–25 season stats
- Virat Kohli IPL 2024 performance analysis

---

## 🏗️ System Architecture

```
╔═══════════════════════════════════════════════════════════════════════╗
║                        USER INTERFACE                                 ║
║               main.py — Interactive CLI Question Loop                 ║
║         Input: natural language question  |  Output: answer + trace   ║
╚═══════════════════════════════════════════╦═══════════════════════════╝
                                            ║  User Question
                                            ▼
╔═══════════════════════════════════════════════════════════════════════╗
║                    AGENT LOOP  (agent/agent_loop.py)                  ║
║                       MAX_STEPS = 8 per question                      ║
║                                                                       ║
║  ┌─────────────────┐                              ┌────────────────┐  ║
║  │    PLANNER      │ ◀─── Context (last 6 steps)  │   EVALUATOR    │  ║
║  │  llm_brain.py   │                              │  llm_brain.py  │  ║
║  │                 │  Decides:                    │                │  ║
║  │ • Sports only?  │  action = "chat"             │ Checks answer  │  ║
║  │ • Future event? │     OR                       │ vs evidence    │  ║
║  │ • Which tools?  │  action = "tool_use"         │                │  ║
║  │ • NL intents    │  + list of tool calls        │ sufficient?    │  ║
║  └────────┬────────┘                              └───────┬────────┘  ║
║           │                                               │           ║
║           ▼                                       YES ◀──┤           ║
║  ┌─────────────────┐                               │      │ NO        ║
║  │  TOOL EXECUTOR  │                               │      │           ║
║  │  (agent_loop)   │ ── runs tools in parallel     │   feedback +     ║
║  │                 │ ── duplicate check → skip     │   re-plan        ║
║  │  query_data     │ ── appends to trace           │   (next step)    ║
║  │  search_docs    │                               │                  ║
║  │  web_search     │                               │                  ║
║  └────────┬────────┘                               │                  ║
║           │                                        │                  ║
║           ▼                                        │                  ║
║  ┌─────────────────┐   ┌─────────────────┐         │                  ║
║  │  RESULT FUSER   │──▶│   SYNTHESIZER   │─────────┘                  ║
║  │  fusion.py      │   │  llm_brain.py   │                            ║
║  │                 │   │                 │                            ║
║  │ Priority order: │   │ Sports Analyst  │                            ║
║  │ DB > Docs > Web │   │ persona. Quotes │                            ║
║  │ Deduplicates    │   │ exact numbers.  │                            ║
║  │ Max 20 items    │   │ Prefers DB data │                            ║
║  └─────────────────┘   └─────────────────┘                            ║
╚═══════════════════════════════════════════════════════════════════════╝
                                            │
                                     FINAL ANSWER
                               answer + trace + steps_used
```

---

## 🔧 Tools & How They Work

### ⭐ `query_data` — Smart Query Tool  (`tools/query_tool.py`)

The most powerful component. The Planner **never writes SQL or Pandas code** — it only provides a natural language intent. The Smart Tool translates that intent to executable code internally.

```
Intent: "Find the player with the most sixes in PSL history"
   │
   ▼
LLM reads data/schema_registry.json (all table/column names)
   │
   ▼
Generates: SELECT "Player","6s" FROM psl_most_sixes_in_psl_history ORDER BY "6s" DESC LIMIT 1
   │
   ▼
Executes against SQLite or Pandas (based on query_type)
   │
   ├── Success → return structured result dict
   │
   └── Error (wrong column, type mismatch, etc.)
         │
         ▼
      LLM re-generates code with error context included
         │
         ▼
      Retry (up to 2 attempts) → return result or error
```

**Backends supported:**

| `query_type` | Target | When to use |
|---|---|---|
| `"sql"` | `data/sports_data.db` (SQLite) | PSL records (runs, wickets, sixes, scores, team wins) |
| `"pandas"` | `IPL.csv` or `player_stats.csv` | IPL ball-by-ball data, FIFA player attributes |

---

### 🔍 `search_docs` — FAISS Vector Document Search  (`tools/search_doc_tool.py`)

Semantic search over curated sports documents using:
- **Embedding model:** `SentenceTransformer("all-MiniLM-L6-v2")` (384-dim)
- **Index:** FAISS `IndexFlatL2` (persisted as `faiss.index` + `meta.pkl`)
- **Singleton pattern:** loaded once at startup via `utils/vector_store.py`

Returns top-3 matching text chunks with source filename.  
Best for: narrative content, match summaries, playing style descriptions, biographical info.

---

### 🌐 `web_search` — Live Tavily Search  (`tools/web_search_tool.py`)

Calls **Tavily Search API** (`search_depth="basic"`, `max_results=5`).  
Returns: title, snippet, URL, published date per result.  
Used for: latest news, data not in local sources, mandatory cross-verification of records.

---

### 💬 `chat` — Direct Refusal (No Tool)

Used when the Planner's scope rules trigger: non-sports questions, future predictions, or unethical requests. The Synthesizer generates a polite, contextual refusal — no tools invoked.

---

## 🔄 Step-by-Step Execution Flow

```
User Question
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ PLANNER (LLM)                                                │
│   Reads: question + last 6 steps of context                  │
│   Rules enforced:                                            │
│     • Non-sports → action: "chat" (refuse)                   │
│     • Future event → action: "chat" (refuse)                 │
│     • Records ("highest", "most") → MUST use DB + web_search │
│     • Complex compare → split into sub-intents per league    │
│   Outputs: action + list of tool calls (name + NL intent)    │
└────────────────────┬─────────────────────────────────────────┘
                     │
           ┌─────────┴─────────┐
    action="chat"       action="tool_use"
           │                   │
    Synthesizer       For each tool call:
    (direct answer)     • Duplicate? → swap to web_search
           │            • Execute tool
           │            • Append {step, tool, input, output} to trace
           │            • Update Context (last 6 steps kept)
           │                   │
           │          ┌────────▼──────────────┐
           │          │  RESULT FUSION        │
           │          │  (fusion.py)          │
           │          │  DB rows → structured │
           │          │  Docs → text chunks   │
           │          │  Web → snippets       │
           │          │  Priority: DB > Docs  │
           │          │  > Web, max 20 items  │
           │          └────────┬──────────────┘
           │                   │
           │          ┌────────▼──────────────┐
           │          │  SYNTHESIZER (LLM)    │
           │          │  Sports Analyst role  │
           │          │  Quotes exact numbers │
           │          │  Prefers DB over web  │
           │          └────────┬──────────────┘
           │                   │
           │          ┌────────▼──────────────┐
           │          │  EVALUATOR (LLM)      │
           │          │  Is answer grounded   │
           │          │  in evidence?         │
           │          └──────┬──────┬─────────┘
           │               YES     NO
           │                │       │
           │                │   same feedback?
           │                │     │       │
           │                │    YES      NO → re-plan
           │                │     │             (next step)
           │                │   [STOP]
           │                │   (no improvement)
           └────────────────┘
                    │
             FINAL ANSWER
          (answer + trace log)
```

---

## 💡 Example Runs

### Single-Tool
```
User: Who scored the most runs in IPL history?

→ Step 1: query_data (pandas, IPL.csv)
          Intent: "Find the player with the most runs in IPL history"
          Generated: df.groupby('batter')['runs_total'].sum()
                       .sort_values(ascending=False).head(1)
          Result: V Kohli → 9242 runs

ANSWER: V Kohli is the top run scorer in IPL history with 9,242 runs.
TRACE:  1 step used
```

### Multi-Tool (Parallel)
```
User: Tell me about the 2022 FIFA World Cup final and Lionel Messi's FIFA game stats.

→ Step 1a: web_search
           Intent: "2022 FIFA World Cup final"
           Result: Argentina defeated France 4-2 on penalties (3-3 AET)

→ Step 1b: query_data (pandas, player_stats.csv)
           Intent: "Find Lionel Messi's FIFA player attributes"
           Result: Ball Control 93, Dribbling 95, Composure 96, Vision 94...

→ FUSION: DB result (high reliability) + Web result (medium)
→ EVALUATOR: sufficient = True

ANSWER: Argentina won the 2022 World Cup. Messi stats: Dribbling 95, Composure 96, Vision 94...
TRACE:  1 step, 2 tools in parallel
```

### Scope Refusal
```
User: Can you help me write Python code to hack a website?

→ PLANNER: action = "chat" (unethical + non-sports)

ANSWER: I cannot provide assistance with hacking a website.
        Is there anything else I can help you with?
TRACE:  1 step, 0 tools
```

### Self-Correction
```
User: Which PSL team won the most matches?

→ Step 1: query_data (sql)
          Generated: SELECT Team, Won FROM psl_result_summary
          ERROR: no such column: Team

→ Step 2: query_data (sql) [retry with error context]
          Generated: SELECT "Team", "Won" FROM psl_result_summary_of_teams
          Result: Islamabad United — 61 wins

ANSWER: Islamabad United won the most PSL matches with 61 victories.
TRACE:  2 steps, self-corrected SQL on retry
```

---

## 📂 Complete Project Structure

```
Proadapt-Project/
│
├── agent/                          # Core agent components
│   ├── agent_loop.py               # Main loop: MAX_STEPS=8, tool dispatch, trace
│   ├── context.py                  # Per-run session state (last 6 steps, UUID keyed)
│   ├── fusion.py                   # Multi-source result merger (DB > Docs > Web)
│   └── llm_brain.py                # Planner · Synthesizer · Evaluator prompts + LLM calls
│
├── tools/                          # Tool implementations
│   ├── query_tool.py               # ⭐ Smart Query Tool (NL intent → SQL/Pandas + self-correct)
│   ├── search_doc_tool.py          # FAISS semantic document search
│   └── web_search_tool.py          # Tavily API live web search
│
├── utils/                          # Shared utilities
│   ├── vector_store.py             # VectorStore singleton (SentenceTransformer + FAISS)
│   ├── knowledge_graph.py          # Precomputed facts builder + fast lookup
│   ├── db_utils.py                 # SQLite connection helpers
│   └── config.py                   # Configuration constants
│
├── data/                           # All data assets
│   ├── sports_data.db              # SQLite: PSL tables (batting, bowling, scores, teams)
│   ├── schema_registry.json        # Full table/column metadata (used by Smart Tool LLM)
│   ├── tool_registry.json          # Tool definitions and descriptions
│   ├── knowledge_graph.json        # Precomputed facts (IPL champions, PSL records, FIFA)
│   ├── structure_data/
│   │   ├── IPL.csv                 # Ball-by-ball IPL data (~110 MB)
│   │   └── player_stats.csv        # FIFA player attributes (~900 KB)
│   └── unstructured/               # Scraped documents (FAISS indexed)
│       ├── babar_azam_psl_2024_records_...txt
│       ├── fifa_world_cup_2022_full_final_...txt
│       ├── ipl_2024_season_review_...txt
│       ├── lionel_messi_2024-2025_season_...txt
│       └── virat_kohli_ipl_2024_performance_...txt
│
├── scripts/                        # Data setup scripts
│   ├── setup_data.py               # Loads CSVs into SQLite, builds schema registry
│   └── collect_real_docs.py        # Scrapes and indexes documents into FAISS
│
├── faiss.index                     # Persisted FAISS vector index (root level)
├── meta.pkl                        # FAISS document metadata (texts + sources)
│
├── main.py                         # CLI entry point: interactive question loop
├── evaluation_runner.py            # 22-question automated evaluation suite (4 categories)
├── output_document.json            # All Q&A pairs captured with full tool traces
├── test_smart_query.py             # Unit test for Smart Query Tool
├── testi.py                        # Quick integration test
├── DESIGN.md                       # Full system design document
├── EVALUATION.md                   # Evaluation report (all 22 questions)
├── pyproject.toml                  # Project dependencies
└── README.md                       # This file
```

---

## 🚀 Setup & Run

### 1️⃣ Install Dependencies

```bash
pip install langchain-groq langchain-core tavily-python pandas \
            sentence-transformers faiss-cpu python-dotenv pydantic
```

Or with `uv`:
```bash
uv sync
```

### 2️⃣ Configure Environment

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3️⃣ (First time) Set up data

```bash
python scripts/setup_data.py         # Load CSVs into SQLite, build schema registry
python scripts/collect_real_docs.py  # Scrape and index documents into FAISS
```

### 4️⃣ Run Interactive Agent

```bash
python main.py
```

```
============================================================
Welcome to the Multi-Tournament Sports Analysis Agent!
Type 'exit' or 'quit' to stop.
============================================================

User Question: Who hit the most sixes in PSL history?
```

### 5️⃣ Run Evaluation Suite

```bash
# All 22 questions (takes ~10-15 min due to Groq rate limits)
python evaluation_runner.py

# Specific questions by ID
python evaluation_runner.py S1 S2 M1 R1 E3
```

---

## 📊 Evaluation Results

The agent was tested on **22 questions** across 4 categories:

| Category | # Questions | Description |
|----------|-------------|-------------|
| 🟢 Single-Tool (S1–S7) | 7 | One SQL or Pandas query + optional web verification |
| 🔵 Multi-Tool (M1–M7) | 7 | Parallel tool execution across multiple source types |
| 🔴 Refusal (R1–R4) | 4 | Non-sports, future predictions, unethical requests |
| 🟡 Edge-Case (E1–E4) | 4 | Ambiguous input, missing data, wrong-domain sport, future dates |

**Key outcomes:**
- ✅ 100% correct refusal rate on all 4 out-of-scope questions
- ✅ Self-correction recovered SQL column errors (e.g., M5: 3 retry attempts succeeded)
- ✅ Parallel tool execution worked correctly for all multi-tool questions
- ✅ Data gaps (Tendulkar Test stats, Mbappe web timeout) acknowledged transparently
- ✅ Ambiguous query ("stats") handled gracefully without crash or hallucination

> Full results: [`EVALUATION.md`](EVALUATION.md) · Full design: [`DESIGN.md`](DESIGN.md) · Raw traces: [`output_document.json`](output_document.json)

---

## 🧰 Tech Stack

| Component | Technology | Role |
|-----------|------------|------|
| Language | Python 3.11+ | — |
| LLM | Groq (`llama-3.1-8b-instant`, temp=0.3) | Planner, Synthesizer, Evaluator, Code Generator |
| LLM Framework | LangChain Core (`langchain-groq`) | Message formatting, LLM invocation |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) | Document encoding for FAISS search |
| Vector Store | FAISS (`faiss-cpu`, IndexFlatL2) | Semantic search over match reports |
| Structured DB | SQLite | PSL historical records |
| CSV Processing | Pandas | IPL ball-by-ball, FIFA attributes |
| Web Search | Tavily Python Client | Real-time news and live data |
| Data Validation | Pydantic v2 | Typed models for Planner/Evaluator outputs |
| Environment | python-dotenv | API key management |
| Package Manager | uv / pip | `pyproject.toml` based |

---

## 🎬 Video Demo

▶️ [Watch the project demo on Google Drive](https://drive.google.com/file/d/1A0_JfOCwWcfzzEg-rbai0xlbVcgdcLIs/view?usp=drive_link)