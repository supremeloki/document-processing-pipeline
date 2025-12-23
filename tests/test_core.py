import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from doc_pipeline import (
    Cleaner,
    DocumentPipeline,
    SourceMissingError,
    UnsupportedFormatError,
    extract_text,
    split_chunks,
)


def test_extract_plain_text(tmp_path):
    doc = tmp_path / "note.txt"
    doc.write_text("plain content", encoding="utf-8")
    assert extract_text(doc) == "plain content"


def test_extract_json_flattens(tmp_path):
    doc = tmp_path / "data.json"
    doc.write_text('{"title": "Report", "tags": ["a", "b"]}', encoding="utf-8")
    text = extract_text(doc)
    assert "Report" in text
    assert "a" in text and "b" in text


def test_missing_source_raises(tmp_path):
    with pytest.raises(SourceMissingError):
        extract_text(tmp_path / "ghost.txt")


def test_unsupported_format_rejected(tmp_path):
    binary = tmp_path / "model.bin"
    binary.write_bytes(b"\x00\x01")
    with pytest.raises(UnsupportedFormatError):
        extract_text(binary)


def test_markdown_stripped():
    cleaner = Cleaner(remove_markdown=True)
    raw = "# Header\n\nSome **bold** [link](http://x) text\n\n![img](pic.png)"
    clean = cleaner(raw)
    assert "#" not in clean
    assert "**" not in clean
    assert "[link]" not in clean
    assert "Header" in clean


def test_html_tags_removed_when_enabled():
    cleaner = Cleaner(remove_html=True, remove_markdown=False)
    cleaned = cleaner("<p>hello <b>world</b></p>")
    assert "<" not in cleaned
    assert "hello" in cleaned and "world" in cleaned


def test_whitespace_normalized():
    cleaner = Cleaner(remove_markdown=False)
    result = cleaner("too   many\tspaces\n\n\n\nhere")
    assert "too many spaces" in result
    assert "\n\n\n" not in result


def test_chunking_with_overlap():
    words = [f"w{i}" for i in range(100)]
    chunks = split_chunks(" ".join(words), max_words=30, overlap=5)
    assert len(chunks) >= 3
    first_tail = chunks[0].split()[-5:]
    second_head = chunks[1].split()[:5]
    assert first_tail == second_head


def test_invalid_overlap_rejected():
    with pytest.raises(Exception):
        split_chunks("text", max_words=10, overlap=10)


def test_full_pipeline_process_text():
    pipeline = DocumentPipeline(chunk_size=20, chunk_overlap=3)
    document = pipeline.process_text(
        "Sample document text. " * 5, doc_id="sample"
    )
    assert document.chunk_count >= 1
    assert document.token_count == 15
    assert document.metadata["source"] == "<memory>"


def test_enrichers_add_metadata():
    def add_checksum(meta):
        return {"checksum": len(str(meta))}
    pipeline = DocumentPipeline(enrichers=[add_checksum])
    document = pipeline.process_text("content", doc_id="e")
    assert "checksum" in document.metadata

