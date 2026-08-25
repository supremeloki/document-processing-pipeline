# doc-pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Document ingestion for RAG: extract text from txt/md/json, strip markdown and HTML noise, normalize whitespace, chunk with overlap, enrich metadata — the clean path from raw files to indexed chunks.

## 🚀 Overview

Raw documents are noisy: markdown syntax, HTML tags, triple-spaced paragraphs. `doc-pipeline` cleans them into model-ready text, splits into overlapping word-window chunks (so context survives chunk boundaries), attaches metadata via pluggable enrichers, and processes whole directories in one call. Formats are explicit — unsupported suffixes raise instead of silently producing garbage.

## ✨ Features

- **Extraction:** `.txt` / `.md` / `.json` (flattened to readable text); unknown formats rejected
- **Markdown stripping:** headers, bold/italic markers, links (label kept), images, footnotes
- **Optional HTML removal** for mixed-format sources
- **Whitespace normalization:** collapsed runs, capped blank lines
- **Overlap chunking:** `split_chunks(text, max_words=150, overlap=20)` with boundary-word continuity
- **Metadata enrichers:** plug callables that append computed fields
- **Directory batch mode:** suffix-filtered processing + aggregate `PipelineStats`
- **Zero dependencies**

## 🚧 Structure

```
document-processing-pipeline/
├── src/doc_pipeline/
│   ├── __init__.py
│   └── core.py
├── tests/
│   └── test_core.py
├── README.md
└── pyproject.toml
```

## 📦 Installation

```bash
git clone https://github.com/supremeloki/document-processing-pipeline.git
cd document-processing-pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 📋 Requirements

- Python 3.11+
- No runtime dependencies

## 🏃 Quick Start

```python
from pathlib import Path
from doc_pipeline import DocumentPipeline

pipeline = DocumentPipeline(chunk_size=150, chunk_overlap=20)
document = pipeline.process_file(Path("docs/handbook.md"), doc_id="handbook")

print(document.chunk_count, document.token_count)
print(document.metadata)

batch = pipeline.process_directory(Path("docs"))
print(DocumentPipeline.summarize(batch))
```

## 🔧 Error Handling

```text
DocPipelineError
├── SourceMissingError       # file doesn't exist
├── UnsupportedFormatError   # .bin/.exe/etc rejected by suffix
└── invalid overlap config   # overlap >= max_words raises
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📝 Code Quality

- Full type hints (`X | None` style), frozen documents/stats
- Zero comments — names carry the meaning
- Overlap continuity asserted: tail of chunk N equals head of chunk N+1

## 📄 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**Kooroush Masoumi** - [kooroushmasoumi@gmail.com](mailto:kooroushmasoumi@gmail.com)

---

⭐ Star this repo if you find it useful!
