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


def flatten_json_text(payload: Any, depth: int = 0) -> str:
    if depth > 6:
        return ""
    if isinstance(payload, dict):
        parts = [f"{k}: {flatten_json_text(v, depth + 1)}" for k, v in payload.items()]
        return " ".join(p for p in parts if p)
    if isinstance(payload, list):
        return " ".join(flatten_json_text(item, depth + 1) for item in payload)
    if isinstance(payload, bool):
        return ""
    return str(payload)


def strip_markdown(text: str) -> str:
    without_noise = MARKDOWN_NOISE.sub(" ", text)
    without_headers = re.sub(r"^#{1,6}\s+", "", without_noise, flags=re.MULTILINE)
    without_links = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", without_headers)
    return without_links


def normalize_whitespace(text: str) -> str:
    single_spaced = WHITESPACE_PATTERN.sub(" ", text)
    collapsed_blank = BLANK_LINE_PATTERN.sub("\n\n", single_spaced)
    return collapsed_blank.strip()


def split_chunks(text: str, max_words: int = 150, overlap: int = 20) -> list[str]:
    if overlap >= max_words:
        raise DocPipelineError("overlap must be smaller than max_words")
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    chunks: list[str] = []
    for index in range(0, len(words), step):
        window = words[index:index + max_words]
        if len(window) < overlap and chunks:
            break
        chunks.append(" ".join(window))
    return chunks


class Cleaner:
    def __init__(self, remove_markdown: bool = True,
                 remove_html: bool = False) -> None:
        self._markdown = remove_markdown
        self._html = remove_html

    def __call__(self, text: str) -> str:
        result = text
        if self._html:
            result = HTML_TAG_PATTERN.sub(" ", result)
        if self._markdown:
            result = strip_markdown(result)
        return normalize_whitespace(result)


class DocumentPipeline:
    def __init__(self, cleaner: Cleaner | None = None,
                 chunk_size: int = 150, chunk_overlap: int = 20,
                 enrichers: Sequence[Callable[[dict[str, Any]], dict[str, Any]]] = ()) -> None:
        self._cleaner = cleaner or Cleaner()
        self._chunk_size = chunk_size
        self._overlap = chunk_overlap
        self._enrichers = list(enrichers)

    def process_file(self, path: Path, doc_id: str | None = None) -> ProcessedDocument:
        raw = extract_text(path)
        return self.process_text(raw, doc_id=doc_id or path.stem,
                                 source_name=path.name)

    def process_text(self, text: str, doc_id: str,
                     source_name: str = "<memory>") -> ProcessedDocument:
        cleaned = self._cleaner(text)
        chunks = tuple(split_chunks(cleaned, self._chunk_size, self._overlap))
        metadata: dict[str, Any] = {
            "source": source_name,
            "characters": len(cleaned),
        }
        for enricher in self._enrichers:
            extra = enricher(metadata)
            if isinstance(extra, dict):
                metadata.update(extra)
        return ProcessedDocument(
            doc_id=doc_id,
            source_name=source_name,
            clean_text=cleaned,
            chunks=chunks,
            token_count=len(TOKEN_PATTERN.findall(cleaned)),
            metadata=metadata,
        )

    def process_directory(self, directory: Path,
                          allowed_suffixes: set[str] | None = None) -> list[ProcessedDocument]:
        suffixes = allowed_suffixes or {".txt", ".md"}
        processed: list[ProcessedDocument] = []
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in suffixes:
                processed.append(self.process_file(path))
        return processed

    @staticmethod
    def summarize(documents: Sequence[ProcessedDocument]) -> PipelineStats:
        return PipelineStats(
            documents=len(documents),
            total_chunks=sum(d.chunk_count for d in documents),
            total_tokens=sum(d.token_count for d in documents),
        )
