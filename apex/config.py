"""
config.py — single source of truth for all settings.
Every other module imports from here, never from os.environ directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Storage paths
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
GAPS_DB_PATH = os.getenv("GAPS_DB_PATH", "./data/gaps.db")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))

# Retrieval
TOP_K_CHUNKS = int(os.getenv("TOP_K_CHUNKS", "8"))

# Embedding model (Claude doesn't have embeddings yet, we use a local approach)
# We'll use chromadb's built-in sentence-transformers embedding for free,
# and Claude only for the answer synthesis step.
EMBED_MODEL = "all-MiniLM-L6-v2"

# Claude model for synthesis
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Confidence threshold — below this, answer is flagged as a knowledge gap
CONFIDENCE_THRESHOLD = 0.4

def validate():
    """Call this on startup to catch missing keys early."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key.\n"
            "Get one at: https://console.anthropic.com"
        )

if __name__ == "__main__":
    validate()
    print("Config OK")
    print(f"  CHROMA_DB_PATH : {CHROMA_DB_PATH}")
    print(f"  GAPS_DB_PATH   : {GAPS_DB_PATH}")
    print(f"  CHUNK_SIZE     : {CHUNK_SIZE}")
    print(f"  TOP_K_CHUNKS   : {TOP_K_CHUNKS}")
