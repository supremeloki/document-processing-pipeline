from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence


class DocPipelineError(Exception):
    pass


class UnsupportedFormatError(DocPipelineError):
    def __init__(self, suffix: str) -> None:
        super().__init__(f"unsupported document format: {suffix!r}")


class SourceMissingError(DocPipelineError):
    pass


TOKEN_PATTERN: re.Pattern[str] = re.compile(r"\w+", re.UNICODE)
WHITESPACE_PATTERN: re.Pattern[str] = re.compile(r"[ \t]+")
BLANK_LINE_PATTERN: re.Pattern[str] = re.compile(r"\n{3,}")
MARKDOWN_NOISE: re.Pattern[str] = re.compile(
    r"(!\[[^\]]*\]\([^)]*\)|\[\^?\d+\]|`{1,3}[^`]*`|\*\*|\*|__)"
)
HTML_TAG_PATTERN: re.Pattern[str] = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ProcessedDocument:
    doc_id: str
    source_name: str
    clean_text: str
    chunks: tuple[str, ...]
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


@dataclass(frozen=True)
class PipelineStats:
    documents: int
    total_chunks: int
    total_tokens: int


def extract_text(path: Path) -> str:
    if not path.exists():
        raise SourceMissingError(f"document not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json_loads(path.read_text(encoding="utf-8"))
        return flatten_json_text(payload)
    raise UnsupportedFormatError(suffix)


def json_loads(raw: str) -> Any:
    import json

    return json.loads(raw)


