"""
api/main.py

FastAPI backend for Apex.

Endpoints:
  POST /query          — ask a question, get an answer + sources
  GET  /sources        — list all ingested documents
  GET  /gaps           — list unanswered questions (admin)
  POST /gaps/{id}/resolve — mark a gap as resolved
  POST /ingest         — trigger re-ingestion (admin)
  GET  /health         — sanity check
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from retrieval.query_engine import query
from retrieval.gap_tracker import get_gaps, resolve_gap, gap_count, init_db
from ingestion.vector_store import VectorStore
from config import ANTHROPIC_API_KEY, CHROMA_DB_PATH

app = FastAPI(
    title="Apex API",
    description="AI knowledge assistant for motorsport engineering teams",
    version="1.0.0",
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

init_db()


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 8


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    is_gap: bool
    gap_description: str
    top_score: float


@app.get("/health")
def health():
    store = VectorStore(db_path=CHROMA_DB_PATH)
    return {
        "status": "ok",
        "chunks_in_store": store.count(),
        "open_gaps": gap_count(),
        "api_key_set": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "placeholder_key"),
    }


@app.post("/query", response_model=QueryResponse)
def ask_question(req: QueryRequest):
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "placeholder_key":
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Add your key to the .env file.",
        )
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = query(question=req.question.strip(), top_k=req.top_k)
    return QueryResponse(**result)


@app.get("/sources")
def list_sources():
    store = VectorStore(db_path=CHROMA_DB_PATH)
    return {
        "sources": store.list_sources(),
        "total_chunks": store.count(),
    }


@app.get("/gaps")
def list_gaps(resolved: bool = False):
    return {
        "gaps": get_gaps(resolved=resolved),
        "total_open": gap_count(),
    }


@app.post("/gaps/{gap_id}/resolve")
def mark_gap_resolved(gap_id: int):
    resolve_gap(gap_id)
    return {"status": "resolved", "gap_id": gap_id}


@app.post("/ingest")
def trigger_ingest(source: str = "markdown", clear: bool = False):
    """Trigger re-ingestion. source = markdown | pdf | github | all"""
    from ingestion.ingest_pipeline import run_ingestion
    counts = run_ingestion(source=source, clear=clear)
    return {"status": "complete", "counts": counts}


# Serve frontend
@app.get("/")
def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Apex API is running. Frontend not found — check frontend/ folder."}


@app.get("/admin")
def serve_admin():
    admin_path = os.path.join(FRONTEND_DIR, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    raise HTTPException(status_code=404, detail="Admin page not found")


# Mount static assets (CSS, JS)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
