"""
ingestion/ingest_pipeline.py

The entry point for all ingestion. Run this to load documents into PitWall.

Usage:
    python -m ingestion.ingest_pipeline                    # ingest everything
    python -m ingestion.ingest_pipeline --source markdown  # only local docs
    python -m ingestion.ingest_pipeline --source github    # only GitHub
    python -m ingestion.ingest_pipeline --source pdf       # only PDFs

After running, your vector store is populated and the API can answer queries.
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.chunker import Chunk
from ingestion.vector_store import VectorStore
from ingestion.markdown_connector import ingest_markdown_folder
from ingestion.pdf_connector import ingest_pdf_folder
from ingestion.github_connector import ingest_github_repos
from config import CHROMA_DB_PATH

SAMPLE_DOCS_PATH = "./docs/sample_docs"
PDFS_PATH = "./docs/pdfs"


def run_ingestion(source: str = "all", clear: bool = False) -> dict:
    """
    Run the full ingestion pipeline.

    Args:
        source: "all" | "markdown" | "github" | "pdf"
        clear: if True, wipe the vector store before ingesting

    Returns:
        dict with counts per source
    """
    print("\n=== PitWall Ingestion Pipeline ===\n")

    store = VectorStore(db_path=CHROMA_DB_PATH)

    if clear:
        print("Clearing existing data...")
        # Recreate the collection by deleting and re-creating
        store.client.delete_collection("pitwall_docs")
        from chromadb.utils import embedding_functions
        from config import EMBED_MODEL
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        store.collection = store.client.get_or_create_collection(
            name="pitwall_docs",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        print("Done.\n")

    counts = {}
    all_chunks: list[Chunk] = []

    # --- Markdown / local docs ---
    if source in ("all", "markdown"):
        print("[1/3] Ingesting local markdown docs...")
        if os.path.exists(SAMPLE_DOCS_PATH):
            chunks = ingest_markdown_folder(SAMPLE_DOCS_PATH)
            all_chunks.extend(chunks)
            counts["markdown"] = len(chunks)
        else:
            print(f"  Skipping — folder not found: {SAMPLE_DOCS_PATH}")
            counts["markdown"] = 0

    # --- PDFs ---
    if source in ("all", "pdf"):
        print("\n[2/3] Ingesting PDFs...")
        if os.path.exists(PDFS_PATH) and any(
            f.endswith(".pdf") for f in os.listdir(PDFS_PATH)
        ):
            chunks = ingest_pdf_folder(PDFS_PATH)
            all_chunks.extend(chunks)
            counts["pdf"] = len(chunks)
        else:
            print(f"  Skipping — no PDFs found in {PDFS_PATH}")
            counts["pdf"] = 0

    # --- GitHub ---
    if source in ("all", "github"):
        print("\n[3/3] Ingesting GitHub repos...")
        try:
            chunks = ingest_github_repos()
            all_chunks.extend(chunks)
            counts["github"] = len(chunks)
        except Exception as e:
            print(f"  GitHub ingestion failed: {e}")
            counts["github"] = 0

    # --- Store everything ---
    if all_chunks:
        print(f"\nStoring {len(all_chunks)} chunks in vector store...")
        added = store.add_chunks(all_chunks)
        print(f"Done. Vector store now has {store.count()} total chunks.")
    else:
        print("\nNo chunks to store.")

    counts["total"] = len(all_chunks)
    counts["store_total"] = store.count()

    print("\n=== Ingestion complete ===")
    print(f"  Markdown chunks : {counts.get('markdown', 0)}")
    print(f"  PDF chunks      : {counts.get('pdf', 0)}")
    print(f"  GitHub chunks   : {counts.get('github', 0)}")
    print(f"  Total in store  : {counts.get('store_total', 0)}")

    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PitWall ingestion pipeline")
    parser.add_argument(
        "--source",
        choices=["all", "markdown", "github", "pdf"],
        default="all",
        help="Which source to ingest (default: all)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear vector store before ingesting",
    )
    args = parser.parse_args()
    run_ingestion(source=args.source, clear=args.clear)
