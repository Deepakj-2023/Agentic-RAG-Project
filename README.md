# Agentic RAG System (Custom AI Agent with Tool Use)

## Overview

This project implements an **Agentic Retrieval-Augmented Generation (RAG) system** built from scratch, without relying on prebuilt agent frameworks.

The goal is to simulate how an intelligent AI agent works internally — making decisions step by step, choosing tools, gathering information, and producing a final answer.

The system is designed to:

- Understand user queries
- Decide the next best action
- Use tools dynamically
- Retrieve data from multiple sources
- Combine results into a final response with traceability

## Problem Statement

The objective is to build an AI agent that can:

- **Retrieve information from multiple data sources:**
  - Unstructured documents
  - Structured databases
  - Web sources
- **Perform multi-step reasoning**
- **Dynamically select and use tools**
- **Generate answers with proper traceability**
- **Avoid hallucination and return safe fallback responses when unsure**

## System Architecture

### Agent Workflow

```
User Query
   ↓
LLM (Decision Maker)
   ↓
Agent Loop
   ↓
Tool Selection
   ↓
Tool Execution
   ↓
Context Update
   ↓
Repeat (Max 8 Steps)
   ↓
Final Answer
```

### Core Components

#### LLM Brain (Decision Maker)

Responsible for deciding what the agent should do next.

It outputs structured actions such as:
- `query_data`
- `search_docs`
- `web_search`
- `final`

#### Agent Loop

This is the core execution engine.

- Runs iteratively
- Executes actions returned by the LLM
- Updates context after every step
- Stops when:
  - Final answer is generated
  - Maximum steps are reached

#### Tools Layer

Handles interaction with external data sources.

| Tool Name | Description |
|-----------|-------------|
| `query_data` | Fetches data from structured sources (DB/CSV) |
| `search_docs` | Retrieves information from documents |
| `web_search` | Fetches external data from web APIs |
| `final` | Produces the final answer |

#### Context Manager

Maintains state across iterations:

- Stores intermediate results
- Tracks previous steps
- Enables multi-step reasoning

## Tools Implemented

### query_data

- Works with structured data (SQLite / CSV)
- Built using Dependency Inversion Principle (DIP)
- Supports multiple data sources via abstraction layer

### search_docs

- Retrieves data from unstructured documents
- Currently a placeholder
- Can be extended using vector databases like FAISS

### web_search

- Fetches real-time information from web APIs
- Currently a placeholder
- Can be integrated with APIs like Tavily

## Project Structure

```
Proadapt-Project/
│
├── agent/
│   ├── agent_loop.py        # Core execution engine
│   ├── action.py            # Tool execution layer
│   ├── context.py           # State management
│   ├── llm_brain.py         # LLM decision logic
│
├── tools/
│   ├── query_tool.py        # Structured data queries
│   ├── search_doc_tool.py   # Document search
│   ├── web_search_tool.py   # Web search
│   ├── data_sources/        # DIP implementation
│   │   ├── base.py
│   │   ├── sqlite_source.py
│   │   ├── csv_source.py
│   │   ├── factory.py
│
├── utils/
│   ├── config.py            # Configuration
│
├── main.py                  # Application entry point
├── pyproject.toml           # Project dependencies
├── README.md                # This file
```

## Example Flow

**Query:**
```
Compare Infosys and TCS margins
```

**Agent Steps:**
1. `query_data` → fetch financial data
2. `search_docs` → retrieve supporting explanations
3. Combine results
4. Generate final answer

## Tech Stack

- **Python** - Core language
- **FastAPI** - Backend (optional)
- **LangChain** - LLM integration
- **Groq API** - LLM inference
- **SQLite / CSV** - Data layer
- **dotenv** - Environment management

## Setup Instructions

### 1. Install Dependencies

```bash
pip install langchain-groq pandas python-dotenv langchain fastapi uvicorn
```

### 2. Configure Environment

Create a `.env` file:

```
TAVILY_API_KEY=your_api_key
GROQ_API_KEY=your_api_key
```

### 3. Run the Application

```bash
uv run main.py
```

Or:

```bash
python main.py
```

## Notes

- The system is intentionally kept modular and simple
- Tools like `search_docs` and `web_search` are designed for easy extension
- The architecture follows clean design principles (especially DIP in data layer)