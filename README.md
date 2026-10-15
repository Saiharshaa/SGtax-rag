# BC3415 Tax RAG

Cited answers to Singapore corporate income tax questions, retrieved from the
Income Tax Act 1947 and IRAS e-Tax guides. Built for tax associates at SME-focused
accounting firms. NTU BC3415 *AI in Accounting & Finance* group project.

The core claim, measured and not just asserted: **structure-aware chunking +
hybrid retrieval beats naive fixed-size chunking on legal text.**

**Status:** ingestion, data quality report, retrieval and cited answer generation are done
(Phases 0-3). The evaluation (Phase 4) has its BM25 results in [`results/metrics.md`](results/metrics.md);
the dense rows follow once the Gemini index is built. The app is next. See [`docs/PLAN.md`](docs/PLAN.md).

## Setup

```bash
uv venv --python 3.11 .venv          # or: python3.11 -m venv .venv
.venv\Scripts\activate               # macOS/Linux: source .venv/bin/activate
uv pip install -r requirements-dev.txt
cp .env.example .env                 # add GROQ_API_KEY and GEMINI_API_KEY
pytest
```

## Build and query the index

```bash
python scripts/build_chunks.py       # PDFs in data/raw/ -> chunks in data/processed/
python scripts/build_index.py        # BM25 + Gemini dense index in index/ (~45 min on the free tier; resumable)
python scripts/search.py "Can a company deduct expenses incurred before it started business?"
python scripts/ask.py "Can a company deduct expenses incurred before it started business?"
```

Without `GEMINI_API_KEY`, use `build_index.py --bm25-only` and `search.py --config structured_bm25_boost`.

## Evaluate

```bash
python scripts/evaluate.py                # retrieval metrics -> results/metrics.md, results/comparison.png
python scripts/evaluate.py --answers 10   # + generated answers -> results/answers.md
```

Configs whose dense index isn't complete are listed as pending. Query embeddings are cached in
`index/query_embeddings.json`, so reruns don't use up the Gemini quota.

## Source documents

The Income Tax Act 1947 (2020 Revised Edition, from Singapore Statutes Online) and five IRAS
e-Tax guides on corporate income tax. The PDFs are not in git; download them into `data/raw/`
using the links and checksums in [`data/raw/SOURCES.md`](data/raw/SOURCES.md). The app itself
never scrapes or downloads anything.

## Layout

```
rag/          library code: parsers, chunk schema, reference detector, retrieval, generation
tests/        pytest; tests/fixtures/sample_act.txt is a synthetic Act (not real law)
eval/         questions.jsonl: questions with gold sections/paragraphs (scripts/evaluate.py scores them)
data/raw/     source PDFs        data/processed/  parsed chunks (JSONL)
index/        persisted BM25 + Chroma index, shipped to Render
results/      metrics.md, comparison.png, answers.md, data_quality.md
docs/PLAN.md  phase plan, design decisions, open questions
```
