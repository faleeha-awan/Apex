"""
retrieval/query_engine.py

The brain of PitWall. Given a user question:
1. Search the vector store for relevant chunks
2. Format them as context
3. Send to Claude with the answer prompt
4. Parse the response — detect knowledge gaps
5. Log gaps to SQLite
6. Return a structured result

This is the file you'll iterate on the most — the prompt and
retrieval strategy determine answer quality more than anything else.
"""
import anthropic
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.vector_store import VectorStore
from retrieval.prompts import ANSWER_PROMPT, GAP_DETECTION_SIGNAL
from retrieval.gap_tracker import init_db, log_gap
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TOP_K_CHUNKS, CONFIDENCE_THRESHOLD, CHROMA_DB_PATH


# Initialise the gaps DB on import
init_db()


def _format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context block for Claude.
    Each chunk is labelled with its source so Claude can cite it.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_name", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("text", "").strip()
        parts.append(f"[Excerpt {i} from {source} (relevance: {score:.2f})]\n{text}")
    return "\n\n---\n\n".join(parts)


def query(
    question: str,
    top_k: int = TOP_K_CHUNKS,
    stream: bool = False,
) -> dict:
    """
    Answer a question using retrieved documents + Claude.

    Returns:
        {
            "answer": str,           # Claude's answer
            "sources": list[dict],   # chunks used
            "is_gap": bool,          # True if docs didn't cover the question
            "gap_description": str,  # what's missing (if is_gap)
            "top_score": float,      # relevance of best retrieved chunk
        }
    """
    # 1. Retrieve relevant chunks
    store = VectorStore(db_path=CHROMA_DB_PATH)
    chunks = store.search(question, top_k=top_k)

    top_score = chunks[0]["score"] if chunks else 0.0

    # 2. If nothing relevant retrieved, flag as gap immediately
    if not chunks or top_score < CONFIDENCE_THRESHOLD:
        description = f"No relevant documentation found for: {question}"
        log_gap(question, description)
        return {
            "answer": "I couldn't find relevant information in the team's documentation to answer this question.",
            "sources": [],
            "is_gap": True,
            "gap_description": description,
            "top_score": top_score,
        }

    # 3. Format context and build prompt
    context = _format_context(chunks)
    prompt = ANSWER_PROMPT.format(context=context, question=question)

    # 4. Call Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if stream:
        # Streaming version — returns a generator, caller handles output
        return _stream_query(client, prompt, question, chunks, top_score)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text.strip()

    # 5. Detect knowledge gaps
    is_gap = GAP_DETECTION_SIGNAL in answer
    gap_description = ""

    if is_gap:
        # Extract the gap description after the signal
        gap_description = answer.split(GAP_DETECTION_SIGNAL, 1)[1].strip()
        log_gap(question, gap_description)
        # Clean the answer to show the gap message only
        answer = f"The documentation doesn't fully cover this. Missing: {gap_description}"

    # 6. Return structured result
    return {
        "answer": answer,
        "sources": chunks,
        "is_gap": is_gap,
        "gap_description": gap_description,
        "top_score": top_score,
    }


def _stream_query(client, prompt, question, chunks, top_score):
    """
    Generator that yields answer text token by token.
    Used by the FastAPI streaming endpoint.
    """
    full_answer = []

    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full_answer.append(text)
            yield text

    # After streaming, check for gap
    answer = "".join(full_answer)
    if GAP_DETECTION_SIGNAL in answer:
        gap_desc = answer.split(GAP_DETECTION_SIGNAL, 1)[1].strip()
        log_gap(question, gap_desc)


if __name__ == "__main__":
    # Quick test — run from project root with:
    # PYTHONPATH=. python retrieval/query_engine.py
    test_questions = [
        "What CAN message ID does the fuel cell use to report its status?",
        "How do I get access to the workshop?",
        "What happened with the coolant failure at Zandvoort?",
        "What is the supplier for the buffer battery cells?",
        "How do you deploy the car to production?",  # should be a knowledge gap
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        result = query(q)
        print(f"A: {result['answer'][:200]}...")
        print(f"   Sources: {[s['source_name'] for s in result['sources'][:2]]}")
        print(f"   Gap: {result['is_gap']} | Top score: {result['top_score']:.3f}")
