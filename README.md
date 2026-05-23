# Apex ⚡

**AI-powered knowledge assistant for student motorsport engineering teams.**

Apex solves a real problem every student engineering team faces: critical knowledge walking out the door when members graduate. Design decisions, supplier contacts, testing failures, embedded architecture — all of it scattered across Drive folders, Slack threads, and people's heads.

Apex ingests a team's documentation from multiple sources, makes it instantly queryable via natural language, and automatically surfaces knowledge gaps — questions the documentation can't answer, waiting to be written.

---

## Demo

> **"What caused the coolant failure at Zandvoort?"**

> Based on the lessons learned documentation, the Zandvoort coolant failure was caused by tap water being used to refill the coolant circuit instead of de-ionised water during a maintenance session. Tap water contains ions that raised conductivity to 18 µS/cm — well above the 5 µS/cm spec — which can short internal fuel cell membranes. [lessons_learned_2024.md]

> **"How do I get workshop access as a new member?"**

> Your student card is activated for 24/7 workshop access within three working days of joining. Until then, always arrive with an existing member. The workshop is in the Faculty of Mechanical Engineering, building 34, ground floor, room 0.34. [onboarding_guide.md]

---

## What it does

- **Multi-source ingestion** — pulls from local markdown files, PDFs, GitHub repositories, and Google Drive
- **Semantic search** — finds relevant documentation by meaning, not just keywords
- **Source attribution** — every answer cites exactly which documents were used, with links
- **Knowledge gap tracking** — when Claude can't answer from the docs, the question is logged in an admin panel as a gap waiting to be filled
- **Human-in-the-loop** — AI retrieves and synthesises, humans verify sources before acting

---

## Architecture

```
Documents (Drive, GitHub, PDFs, Markdown)
        ↓
  Connectors (per source)
        ↓
   Chunker (512-token chunks, 64-token overlap)
        ↓
  Embedder (all-MiniLM-L6-v2, local)
        ↓
  ChromaDB (persistent vector store)
        ↓
  Query Engine (semantic search → Claude synthesis)
        ↓
  FastAPI (REST API + WebSocket)
        ↓
  Frontend (chat UI + admin panel)
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude (Anthropic) via API |
| Embeddings | sentence-transformers / all-MiniLM-L6-v2 |
| Vector store | ChromaDB (persistent, local) |
| Backend | FastAPI + uvicorn |
| Frontend | Vanilla JS, no framework |
| Gap tracking | SQLite |
| Data sources | GitHub API, Google Drive API, PyMuPDF |

---

## Project structure

```
Apex/
├── config.py                    # all settings, loaded from .env
├── ingestion/
│   ├── chunker.py               # splits text into overlapping token chunks
│   ├── vector_store.py          # ChromaDB wrapper (add, search, list, delete)
│   ├── markdown_connector.py    # local .md and .txt files
│   ├── pdf_connector.py         # PDF extraction via PyMuPDF
│   ├── github_connector.py      # GitHub repo READMEs and docs
│   ├── gdrive_connector.py      # Google Drive docs and files
│   └── ingest_pipeline.py       # orchestrates all connectors
├── retrieval/
│   ├── prompts.py               # Claude prompt templates
│   ├── gap_tracker.py           # SQLite gap logging and resolution
│   └── query_engine.py          # retrieval + Claude synthesis
├── api/
│   └── main.py                  # FastAPI routes
├── frontend/
│   ├── index.html               # chat interface
│   └── admin.html               # knowledge gap admin panel
├── docs/
│   └── sample_docs/             # sample motorsport team documentation
└── tests/
    └── test_Apex.py          # unit tests (pytest)
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/Apex
cd Apex
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install sentence-transformers
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env` and add:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
GITHUB_TOKEN=ghp_your_token_here       # optional, for GitHub connector
```

Get an Anthropic key at [console.anthropic.com](https://console.anthropic.com).

### 3. Ingest documents

```bash
# Local markdown docs (included as sample)
python -m ingestion.ingest_pipeline --source markdown

# GitHub repos (needs GITHUB_TOKEN)
python -m ingestion.ingest_pipeline --source github

# PDFs — drop files into docs/pdfs/ first
python -m ingestion.ingest_pipeline --source pdf

# Google Drive (see Google Drive setup below)
python -m ingestion.ingest_pipeline --source gdrive --folder-id YOUR_FOLDER_ID

# Everything at once
python -m ingestion.ingest_pipeline --source all
```

### 4. Run

```bash
uvicorn api.main:app --reload --port 8000
```

Open `http://localhost:8000` for the chat interface.
Open `http://localhost:8000/admin` for the knowledge gap admin panel.

---

## Google Drive setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Google Drive API**
3. Credentials → Create → OAuth 2.0 Client ID → Desktop App
4. Download the JSON → save as `credentials.json` in project root
5. First run opens a browser for consent — after that it's automatic

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
python -m ingestion.ingest_pipeline --source gdrive --folder-id YOUR_FOLDER_ID
```

The folder ID is the last part of the Drive folder URL.

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

Tests cover the chunker, markdown connector, and gap tracker with 15+ assertions.

---

## Knowledge gap tracking

Every question Apex can't answer from the documentation is logged automatically. Visit `/admin` to see open gaps — these become a backlog of documentation that needs to be written.

This turns Apex from a passive search tool into an active signal for where team knowledge is missing.

---

## Extending Apex

Adding a new data source takes one file. Create `ingestion/confluence_connector.py`, implement `ingest_confluence_space(space_key) -> list[Chunk]`, and add it to `ingest_pipeline.py`. The chunker, vector store, and query engine need zero changes.

Planned connectors: Confluence, Slack (message history), Notion.
