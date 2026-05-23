"""
ingestion/pdf_connector.py

Extracts text from PDFs using PyMuPDF (fitz).
Works on scanned PDFs too (though quality depends on the scan).

PyMuPDF is fast, handles multi-column layouts better than pdfminer,
and doesn't require poppler to be installed separately.
"""
from pathlib import Path
import fitz  # PyMuPDF
from ingestion.chunker import chunk_text, Chunk


def ingest_pdf(
    filepath: str,
    source_url: str = "",
    author: str = "",
    date: str = "",
) -> list[Chunk]:
    """
    Extract text from a PDF and return chunks.

    Args:
        filepath: path to the PDF
        source_url: URL to link back to (e.g. DOE paper URL)
        author: override author (if not detectable from PDF metadata)
        date: override date
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {filepath}")

    doc = fitz.open(str(path))

    # Try to get author/date from PDF metadata
    meta = doc.metadata or {}
    if not author:
        author = meta.get("author", "")
    if not date:
        date = meta.get("creationDate", "")[:10]  # YYYYMMDD → YYYY-MM-DD ish

    # Extract text page by page
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # plain text extraction
        if text.strip():
            pages_text.append(text)

    doc.close()

    full_text = "\n\n".join(pages_text)
    if not full_text.strip():
        print(f"  [pdf] WARNING: no text extracted from {path.name} (scanned?)")
        return []

    return chunk_text(
        text=full_text,
        source_type="pdf",
        source_name=path.name,
        source_url=source_url or f"file://{path.resolve()}",
        author=author,
        date=date,
    )


def ingest_pdf_folder(folder_path: str) -> list[Chunk]:
    """Ingest all PDFs in a folder."""
    folder = Path(folder_path)
    all_chunks = []
    files_processed = 0

    for filepath in sorted(folder.glob("**/*.pdf")):
        try:
            chunks = ingest_pdf(str(filepath))
            all_chunks.extend(chunks)
            files_processed += 1
            print(f"  [pdf] {filepath.name} → {len(chunks)} chunks")
        except Exception as e:
            print(f"  [pdf] SKIP {filepath.name}: {e}")

    print(f"  [pdf] total: {files_processed} files, {len(all_chunks)} chunks")
    return all_chunks
