---
title: Web Research Agent
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🔍 Agentic Web Research Assistant

> A stateful AI agent that searches the web in real time, summarises results with citations, and remembers your full conversation across the session — built with LangGraph and Chainlit.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-green?style=flat-square)
![Chainlit](https://img.shields.io/badge/Chainlit-1.3-orange?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## ✨ Features

- **Agentic routing** — decides at runtime whether to search the web or answer from conversation memory
- **Real-time web search** — powered by Tavily, fetches and summarises top 5 sources with citations
- **Persistent memory** — SQLite-backed checkpointing keeps full conversation history across sessions
- **Live agent thinking** — Chainlit Steps show each graph node as it runs (Routing → Searching → Summarising → Responding)
- **Token streaming** — responses stream character by character like ChatGPT
- **Chat starters** — suggested prompts on the welcome screen
- **Full observability** — every LLM call and tool use traced in LangSmith
- **One-command Docker deploy** — single container, hot-reload in development

---

## 🏗️ Architecture

```
User
 │
 ▼
Chainlit UI  (WebSocket, port 8000)
 │
 ▼
LangGraph Agent
 │
 ├── Router Node        decides: search web OR answer from memory
 │        │
 │   [needs search]
 │        ├── Search Node       calls Tavily API → top 5 results
 │        └── Summarise Node    condenses results + adds source URLs
 │
 └── Respond Node       generates final answer → streams to UI
          │
          ▼
   AsyncSqliteSaver     persists state per thread_id
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent | LangGraph 0.2 | Stateful graph with conditional routing and cycles |
| UI | Chainlit 1.3 | WebSocket chat UI with Steps and streaming |
| Search | Tavily API | Real-time web search with source URLs |
| Memory | AsyncSqliteSaver + aiosqlite | Async cross-session conversation persistence |
| LLM | GPT-4o-mini (OpenAI) | Routing, summarisation, response generation |
| Tracing | LangSmith | Full agent observability and trace debugging |
| Deploy | Docker Compose | Single-container, volume-mounted hot reload |

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- API keys for [OpenAI](https://platform.openai.com), [Tavily](https://tavily.com) (free tier), and [LangSmith](https://smith.langchain.com) (free tier)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/web-research-agent.git
cd web-research-agent
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```ini
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=web-research-agent
MODEL_NAME=gpt-4o-mini
SQLITE_DB_PATH=/tmp/data/checkpoints.db
```

### 3. Run

```bash
docker compose up --build
```

Open **http://localhost:8000** — you're live.

---

## 📁 Project Structure

```
web-research-agent/
│
├── backend/
│   └── app/
│       ├── agent/
│       │   ├── state.py       # ResearchState TypedDict
│       │   ├── tools.py       # Tavily search tool
│       │   ├── nodes.py       # Router, Search, Summarise, Respond nodes
│       │   └── graph.py       # StateGraph assembly + AsyncSqliteSaver
│       ├── api/
│       │   └── routes.py      # FastAPI endpoints (optional REST layer)
│       └── core/
│           └── config.py      # Pydantic settings
│
├── frontend/
│   ├── app.py                 # Chainlit app — lifecycle hooks + streaming
│   ├── chainlit.md            # Welcome screen content
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/                      # SQLite DB (Docker volume — gitignored)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔄 Agent Graph — Node by Node

### Router Node
Looks at the user's message and conversation history. Asks the LLM one question: *"Does this need a web search or can it be answered from memory?"* Returns `needs_search: bool`.

### Search Node
Calls Tavily with the user's query. Returns top 5 results with `url`, `title`, and `content` for each.

### Summarise Node
Condenses the 5 raw search results into a clean answer with source URLs as footnotes. Only runs if Router decided to search.

### Respond Node
Generates the final answer. If a summary exists — uses it directly. If answering from memory — calls the LLM with full conversation history.

### Conditional Edge
```
Router → [needs_search=True]  → Search → Summarise → Respond → END
Router → [needs_search=False] ──────────────────────→ Respond → END
```

---

## 💻 Development Workflow

Hot reload is enabled — no rebuild needed for code changes:

```bash
# Start with hot reload
docker compose up

# Edit any .py file → Chainlit reloads automatically (1-2 seconds)

# Only rebuild when you change requirements.txt
docker compose up --build
```

To run **without Docker** (local dev):

```bash
cd frontend
pip install -r requirements.txt
export $(cat ../.env | xargs)
chainlit run app.py --reload
```

---

## 🔭 Observability — LangSmith

Every run is traced automatically when `LANGCHAIN_TRACING_V2=true` is set.

Open [smith.langchain.com](https://smith.langchain.com) → select the `web-research-agent` project to see:

- Full trace of every node execution
- Token usage per LLM call
- Tool inputs and outputs (Tavily queries + results)
- Latency breakdown per node
- Conversation thread history

---

## 🔑 Key Implementation Decisions

**Why Chainlit over Streamlit?**
Chainlit is WebSocket-based and async-first — it natively supports `astream_events()` for real-time LangGraph streaming. Streamlit re-renders the whole page on every interaction and has no equivalent to Chainlit's Steps (collapsible agent thinking panels).

**Why AsyncSqliteSaver over SqliteSaver?**
`astream_events()` runs on an async event loop. The sync `SqliteSaver` blocks the loop on every checkpoint read/write. `AsyncSqliteSaver` with `aiosqlite` keeps the loop unblocked so streaming stays smooth.

**Why `astream_events()` over `cl.LangchainCallbackHandler`?**
The callback handler doesn't stream cleanly with LangGraph's multi-node graphs — it only streams if `force_stream_final_answer=True` and adds latency. `astream_events()` gives per-node event control and reliable token streaming.

**Why a single Docker container?**
Chainlit hosts the agent directly — no separate FastAPI server needed for the UI layer. The `backend/` folder is mounted as a volume and imported as a Python package, keeping the agent code cleanly separated without requiring a second running service.

---

## 🗺️ Roadmap / Stretch Goals

- [ ] Add a **Query Rewriter Node** — rewrites vague queries before searching
- [ ] Add a **Fact-Check Node** — cross-references claims across 2+ sources
- [ ] Add **citation formatting** — inline `[1]` footnotes with source links
- [ ] Add **long-term memory** — store past sessions in ChromaDB for cross-session recall
- [ ] Deploy to **Railway** (backend) + **Hugging Face Spaces** (frontend)
- [ ] Add **LangSmith evaluation dataset** — automated groundedness scoring on every run

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built as Project 1 of a 6-project Agentic AI learning plan using the [CampusX LangGraph playlist](https://www.youtube.com/playlist?list=PLKnIA16_RmvYsvB8qkUQuJmJNuiCUJFPL).

**Stack:** [LangGraph](https://github.com/langchain-ai/langgraph) · [Chainlit](https://github.com/Chainlit/chainlit) · [Tavily](https://tavily.com) · [LangSmith](https://smith.langchain.com)
