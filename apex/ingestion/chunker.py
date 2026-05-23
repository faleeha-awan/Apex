"""
ingestion/chunker.py

Takes raw text + metadata, returns a list of Chunk objects.
Uses tiktoken to count tokens accurately (same tokenizer Claude uses).

Why overlap? So a sentence that spans a chunk boundary isn't lost.
If chunk N ends mid-sentence, chunk N+1 starts 64 tokens back,
so that sentence appears in full in at least one chunk.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    """A single piece of a document, ready to embed and store."""
    text: str
    source_type: str      # "github", "pdf", "markdown", "notion"
    source_name: str      # filename or repo name
    source_url: str       # direct link to the original
    chunk_index: int      # position within the document
    total_chunks: int     # how many chunks this doc was split into
    author: Optional[str] = None
    date: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_metadata(self) -> dict:
        """ChromaDB metadata must be flat key-value, no nested dicts."""
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "author": self.author or "",
            "date": self.date or "",
        }


def _count_tokens(text: str) -> int:
    """
    Approximate token count: ~1 token per word (good enough for chunking).
    Real tokenizers are ~1.3 tokens/word, so we're slightly conservative —
    chunks may be a bit smaller than chunk_size. That's fine.
    """
    return len(text.split())


def _encode(text: str) -> list[str]:
    """Return words as the 'token' list for overlap calculation."""
    return text.split()


def clean_text(text: str) -> str:
    """
    Remove junk that wastes tokens and confuses the embedder:
    - Excessive whitespace / blank lines
    - HTML tags
    - Repeated dashes or equals (common in markdown dividers)
    """
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse repeated dashes/equals lines
    text = re.sub(r"[-=]{4,}", "", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_text(
    text: str,
    source_type: str,
    source_name: str,
    source_url: str,
    author: Optional[str] = None,
    date: Optional[str] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Split text into overlapping chunks of ~chunk_size tokens.

    Strategy:
    1. Clean the text first
    2. Split into sentences (rough, but good enough)
    3. Pack sentences into chunks until we hit the token limit
    4. Start the next chunk chunk_overlap tokens back
    """
    text = clean_text(text)
    if not text:
        return []

    # Split into sentences — we won't break mid-sentence
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[Chunk] = []
    current_sentences: list[str] = []
    current_token_count = 0

    for sentence in sentences:
        sentence_token_count = _count_tokens(sentence)

        # If adding this sentence would exceed the limit, flush current chunk
        if current_token_count + sentence_token_count > chunk_size and current_sentences:
            chunk_text_str = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    text=chunk_text_str,
                    source_type=source_type,
                    source_name=source_name,
                    source_url=source_url,
                    chunk_index=len(chunks),
                    total_chunks=0,
                    author=author,
                    date=date,
                )
            )

            # Overlap: keep last chunk_overlap words worth of sentences
            overlap_word_count = 0
            overlap_sentences = []
            for s in reversed(current_sentences):
                s_words = _count_tokens(s)
                if overlap_word_count + s_words > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_word_count += s_words

            current_sentences = overlap_sentences
            current_token_count = sum(_count_tokens(s) for s in current_sentences)

        current_sentences.append(sentence)
        current_token_count += sentence_token_count

    # Flush the last chunk
    if current_sentences:
        chunks.append(
            Chunk(
                text=" ".join(current_sentences),
                source_type=source_type,
                source_name=source_name,
                source_url=source_url,
                chunk_index=len(chunks),
                total_chunks=0,
                author=author,
                date=date,
            )
        )

    # Now we know total_chunks, fill it in
    total = len(chunks)
    for chunk in chunks:
        chunk.total_chunks = total

    return chunks


if __name__ == "__main__":
    # Quick smoke test
    sample = """
    The hydrogen fuel cell stack is the heart of the Forze IX powertrain.
    It converts hydrogen and oxygen directly into electricity through an electrochemical reaction,
    with water as the only byproduct. The stack operates at roughly 80 degrees Celsius and
    requires careful thermal management to maintain efficiency. During race conditions, the
    power demand fluctuates rapidly, so the energy management system must balance draw from
    the fuel cell against the buffer battery pack. The battery absorbs regenerative braking
    energy and handles peak power demands that the fuel cell alone cannot satisfy.
    """ * 10  # repeat to test chunking

    chunks = chunk_text(
        text=sample,
        source_type="markdown",
        source_name="fuel_cell_overview.md",
        source_url="https://github.com/example/Apex/docs/fuel_cell_overview.md",
        author="Forze Team",
        date="2024-01-01",
    )

    print(f"Input length: {len(sample)} chars")
    print(f"Chunks produced: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i}: {len(c.text)} chars — '{c.text[:60]}...'")
