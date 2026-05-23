"""
ingestion/markdown_connector.py

Ingests local .md and .txt files.
This is the connector you'll use for your sample docs folder.
"""
import os
from pathlib import Path
from ingestion.chunker import chunk_text, Chunk


def ingest_markdown_file(
    filepath: str,
    base_url: str = "https://github.com/yourusername/pitwall/blob/main/",
) -> list[Chunk]:
    """
    Read a markdown/text file, chunk it, return Chunk objects.

    Args:
        filepath: path to the .md or .txt file
        base_url: prefix for constructing a source_url link
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    text = path.read_text(encoding="utf-8", errors="ignore")
    source_name = path.name
    source_url = base_url + path.name

    # Try to extract author/date from frontmatter (--- key: value ---)
    author, date = _parse_frontmatter(text)

    return chunk_text(
        text=text,
        source_type="markdown",
        source_name=source_name,
        source_url=source_url,
        author=author,
        date=date,
    )


def ingest_markdown_folder(
    folder_path: str,
    base_url: str = "https://github.com/yourusername/pitwall/blob/main/docs/",
) -> list[Chunk]:
    """
    Ingest all .md and .txt files in a folder.
    Returns all chunks from all files combined.
    """
    folder = Path(folder_path)
    all_chunks = []
    files_processed = 0

    for filepath in sorted(folder.glob("**/*.md")) + sorted(folder.glob("**/*.txt")):
        try:
            chunks = ingest_markdown_file(str(filepath), base_url)
            all_chunks.extend(chunks)
            files_processed += 1
            print(f"  [markdown] {filepath.name} → {len(chunks)} chunks")
        except Exception as e:
            print(f"  [markdown] SKIP {filepath.name}: {e}")

    print(f"  [markdown] total: {files_processed} files, {len(all_chunks)} chunks")
    return all_chunks


def _parse_frontmatter(text: str) -> tuple[str, str]:
    """
    Extract author and date from YAML frontmatter if present.
    Frontmatter looks like:
    ---
    author: Faliha Awan
    date: 2025-01-15
    ---
    """
    author = ""
    date = ""
    if not text.startswith("---"):
        return author, date

    end = text.find("---", 3)
    if end == -1:
        return author, date

    frontmatter = text[3:end]
    for line in frontmatter.splitlines():
        if line.startswith("author:"):
            author = line.split(":", 1)[1].strip()
        elif line.startswith("date:"):
            date = line.split(":", 1)[1].strip()

    return author, date
