"""
tests/test_Apex.py

Unit tests for Apex's core components.
Run with: pytest tests/ -v

Why tests matter:
- Proves to Forze you write production-quality code, not just demos
- Catches bugs before they reach the vector store or Claude
- Documents expected behaviour — tests are specs
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.chunker import chunk_text, clean_text, Chunk


# ─────────────────────────────────────────────
# Chunker tests
# ─────────────────────────────────────────────

class TestCleanText:
    def test_strips_html_tags(self):
        result = clean_text("<p>Hello <b>world</b></p>")
        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_collapses_excess_newlines(self):
        result = clean_text("line1\n\n\n\n\nline2")
        assert "\n\n\n" not in result

    def test_collapses_repeated_dashes(self):
        result = clean_text("title\n--------\ncontent")
        assert "--------" not in result

    def test_strips_leading_trailing_whitespace(self):
        result = clean_text("   hello   ")
        assert result == "hello"

    def test_empty_string(self):
        result = clean_text("")
        assert result == ""


class TestChunkText:
    SAMPLE = """
    The hydrogen fuel cell stack converts hydrogen and oxygen into electricity.
    The only byproduct is water. This makes it a zero-emission power source.
    The stack operates at roughly 80 degrees Celsius and requires thermal management.
    The BMS monitors every cell in the battery pack for voltage and temperature.
    The embedded software team writes firmware in C using FreeRTOS on STM32 microcontrollers.
    CAN bus connects all electronic control units in the vehicle at 500 kbit per second.
    """ * 5  # repeat to force multiple chunks

    def _make_chunks(self, text=None, chunk_size=50):
        return chunk_text(
            text=text or self.SAMPLE,
            source_type="markdown",
            source_name="test.md",
            source_url="https://example.com/test.md",
            chunk_size=chunk_size,
            chunk_overlap=10,
        )

    def test_returns_list_of_chunks(self):
        chunks = self._make_chunks()
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_all_chunks_are_chunk_objects(self):
        chunks = self._make_chunks()
        for c in chunks:
            assert isinstance(c, Chunk)

    def test_chunk_has_required_fields(self):
        chunks = self._make_chunks()
        c = chunks[0]
        assert c.text
        assert c.source_type == "markdown"
        assert c.source_name == "test.md"
        assert c.source_url == "https://example.com/test.md"
        assert c.chunk_index == 0
        assert c.total_chunks == len(chunks)

    def test_chunk_indices_are_sequential(self):
        chunks = self._make_chunks()
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_total_chunks_consistent(self):
        chunks = self._make_chunks()
        total = len(chunks)
        for c in chunks:
            assert c.total_chunks == total

    def test_empty_text_returns_empty_list(self):
        chunks = chunk_text(
            text="",
            source_type="markdown",
            source_name="empty.md",
            source_url="https://example.com",
        )
        assert chunks == []

    def test_whitespace_only_returns_empty_list(self):
        chunks = chunk_text(
            text="   \n\n\t  ",
            source_type="markdown",
            source_name="empty.md",
            source_url="https://example.com",
        )
        assert chunks == []

    def test_short_text_is_single_chunk(self):
        short = "This is a very short document."
        chunks = chunk_text(
            text=short,
            source_type="markdown",
            source_name="short.md",
            source_url="https://example.com",
        )
        assert len(chunks) == 1
        assert "short document" in chunks[0].text

    def test_no_empty_chunk_texts(self):
        chunks = self._make_chunks()
        for c in chunks:
            assert c.text.strip() != ""

    def test_chunk_metadata_to_dict(self):
        chunks = self._make_chunks()
        meta = chunks[0].to_metadata()
        assert isinstance(meta, dict)
        assert meta["source_type"] == "markdown"
        assert meta["source_name"] == "test.md"
        assert "chunk_index" in meta
        assert "total_chunks" in meta

    def test_metadata_has_no_nested_dicts(self):
        """ChromaDB requires flat metadata — no nested objects."""
        chunks = self._make_chunks()
        meta = chunks[0].to_metadata()
        for v in meta.values():
            assert not isinstance(v, dict), f"Nested dict found in metadata: {v}"
            assert not isinstance(v, list), f"List found in metadata: {v}"

    def test_author_and_date_passed_through(self):
        chunks = chunk_text(
            text="Some content about the car.",
            source_type="markdown",
            source_name="test.md",
            source_url="https://example.com",
            author="Faliha Awan",
            date="2025-01-15",
        )
        assert chunks[0].author == "Faliha Awan"
        assert chunks[0].date == "2025-01-15"
        assert chunks[0].to_metadata()["author"] == "Faliha Awan"


# ─────────────────────────────────────────────
# Markdown connector tests
# ─────────────────────────────────────────────

class TestMarkdownConnector:
    def test_ingest_real_sample_doc(self, tmp_path):
        """Test against an actual markdown file."""
        from ingestion.markdown_connector import ingest_markdown_file

        doc = tmp_path / "test_doc.md"
        doc.write_text("""---
author: Test Author
date: 2025-01-01
---

# Test Document

This is a test document about hydrogen fuel cells and CAN bus systems.
The embedded software team writes firmware for the STM32 microcontroller.
FreeRTOS provides real-time scheduling for safety-critical tasks.
""")
        chunks = ingest_markdown_file(str(doc))
        assert len(chunks) >= 1
        assert chunks[0].source_name == "test_doc.md"
        assert chunks[0].author == "Test Author"
        assert chunks[0].date == "2025-01-01"
        assert "hydrogen" in chunks[0].text.lower() or "FreeRTOS" in chunks[0].text

    def test_ingest_folder(self, tmp_path):
        from ingestion.markdown_connector import ingest_markdown_folder

        (tmp_path / "doc1.md").write_text("# Doc 1\nContent about fuel cells.")
        (tmp_path / "doc2.md").write_text("# Doc 2\nContent about CAN bus.")
        (tmp_path / "notes.txt").write_text("Some plain text notes.")

        chunks = ingest_markdown_folder(str(tmp_path))
        source_names = [c.source_name for c in chunks]
        assert "doc1.md" in source_names
        assert "doc2.md" in source_names

    def test_nonexistent_file_raises(self):
        from ingestion.markdown_connector import ingest_markdown_file
        with pytest.raises(FileNotFoundError):
            ingest_markdown_file("/nonexistent/path/file.md")


# ─────────────────────────────────────────────
# Gap tracker tests
# ─────────────────────────────────────────────

class TestGapTracker:
    def test_log_and_retrieve_gap(self, tmp_path):
        """Gaps logged should appear in get_gaps()."""
        import importlib
        import retrieval.gap_tracker as gt

        # Use a temp DB for this test
        original = gt.GAPS_DB_PATH if hasattr(gt, 'GAPS_DB_PATH') else None
        test_db = str(tmp_path / "test_gaps.db")

        # Monkey-patch the path
        import retrieval.gap_tracker as gap_mod
        gap_mod.GAPS_DB_PATH = test_db
        gap_mod.init_db()

        gap_mod.log_gap("How do I deploy to production?", "No deployment docs found")
        gaps = gap_mod.get_gaps(resolved=False)

        assert len(gaps) >= 1
        questions = [g["question"] for g in gaps]
        assert "How do I deploy to production?" in questions

    def test_resolve_gap(self, tmp_path):
        import retrieval.gap_tracker as gap_mod
        test_db = str(tmp_path / "test_gaps2.db")
        gap_mod.GAPS_DB_PATH = test_db
        gap_mod.init_db()

        gap_mod.log_gap("Unresolved question?")
        gaps = gap_mod.get_gaps(resolved=False)
        gap_id = gaps[0]["id"]

        gap_mod.resolve_gap(gap_id)
        open_gaps = gap_mod.get_gaps(resolved=False)
        resolved_gaps = gap_mod.get_gaps(resolved=True)

        open_ids = [g["id"] for g in open_gaps]
        resolved_ids = [g["id"] for g in resolved_gaps]

        assert gap_id not in open_ids
        assert gap_id in resolved_ids

    def test_gap_count(self, tmp_path):
        import retrieval.gap_tracker as gap_mod
        test_db = str(tmp_path / "test_gaps3.db")
        gap_mod.GAPS_DB_PATH = test_db
        gap_mod.init_db()

        gap_mod.log_gap("Question 1?")
        gap_mod.log_gap("Question 2?")
        gap_mod.log_gap("Question 3?")

        assert gap_mod.gap_count() == 3
