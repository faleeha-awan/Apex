"""
ingestion/vector_store.py

Wraps ChromaDB. Handles:
- Creating / loading the persistent collection
- Adding chunks (with deduplication by source)
- Searching by semantic similarity
- Deleting all chunks from a source (for re-ingestion)

ChromaDB uses sentence-transformers under the hood for embedding —
all-MiniLM-L6-v2 runs locally, no API key needed, ~80MB download on first run.
"""
import hashlib
import math
import re
from collections import Counter
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions
from ingestion.chunker import Chunk
from config import CHROMA_DB_PATH, TOP_K_CHUNKS


COLLECTION_NAME = "pitwall_docs"
EMBED_DIM = 384  # match typical sentence-transformer dim



def _make_chunk_id(chunk: Chunk) -> str:
    key = f"{chunk.source_name}::{chunk.chunk_index}::{chunk.text[:100]}"
    return hashlib.md5(key.encode()).hexdigest()


class VectorStore:
    def __init__(self, db_path: str = CHROMA_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk]) -> int:
        """
        Add chunks to the vector store.
        Skips chunks that already exist (same ID).
        Returns number of chunks actually added.
        """
        if not chunks:
            return 0

        ids = [_make_chunk_id(c) for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [c.to_metadata() for c in chunks]

        # ChromaDB upserts — won't duplicate if ID already exists
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = TOP_K_CHUNKS,
        source_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic search. Returns top_k most relevant chunks.

        Each result dict has:
          - text: the chunk text
          - score: cosine similarity (0-1, higher = more relevant)
          - metadata: source info
        """
        where = {"source_type": source_type} if source_type else None

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks_out = []
        if not results["documents"] or not results["documents"][0]:
            return chunks_out

        for text, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB returns cosine *distance* (0=identical, 2=opposite)
            # Convert to similarity score 0-1
            score = 1 - (distance / 2)
            chunks_out.append({
                "text": text,
                "score": round(score, 4),
                "source_name": metadata.get("source_name", ""),
                "source_url": metadata.get("source_url", ""),
                "source_type": metadata.get("source_type", ""),
                "author": metadata.get("author", ""),
                "date": metadata.get("date", ""),
            })

        # Sort by score descending
        chunks_out.sort(key=lambda x: x["score"], reverse=True)
        return chunks_out

    def delete_source(self, source_name: str) -> int:
        """
        Remove all chunks from a specific source.
        Useful when re-ingesting an updated file.
        """
        results = self.collection.get(
            where={"source_name": source_name},
            include=[],
        )
        ids = results.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self.collection.count()

    def list_sources(self) -> list[dict]:
        """Return a deduplicated list of all ingested sources."""
        results = self.collection.get(include=["metadatas"])
        seen = {}
        for meta in results.get("metadatas", []):
            name = meta.get("source_name", "")
            if name not in seen:
                seen[name] = {
                    "source_name": name,
                    "source_type": meta.get("source_type", ""),
                    "source_url": meta.get("source_url", ""),
                    "author": meta.get("author", ""),
                    "date": meta.get("date", ""),
                }
        return list(seen.values())



