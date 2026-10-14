# BC3415 Tax RAG

Cited answers to Singapore corporate income tax questions, retrieved from the
Income Tax Act 1947 and IRAS e-Tax guides. Built for tax associates at SME-focused
accounting firms. NTU BC3415 *AI in Accounting & Finance* group project.

The core claim, measured and not just asserted: **structure-aware chunking +
hybrid retrieval beats naive fixed-size chunking on legal text.**

**Status:** Phase 0 (plan + scaffold). See [`docs/PLAN.md`](docs/PLAN.md).

## Setup

```bash
uv venv --python 3.11 .venv          # or: python3.11 -m venv .venv
.venv\Scripts\activate               # macOS/Linux: source .venv/bin/activate
uv pip install -r requirements-dev.txt
cp .env.example .env                 # add GROQ_API_KEY and GEMINI_API_KEY
pytest
```

## Source documents

Put the PDFs in `data/raw/` (we don't scrape or download anything):

- `ITA_1947.pdf`: Income Tax Act 1947, current revised edition from Singapore Statutes Online
- `etax_*.pdf`: 3 to 5 IRAS e-Tax guides on corporate income tax

## Layout

```
rag/          library code: parsers, chunk schema, reference detector, retrieval, generation
tests/        pytest; tests/fixtures/sample_act.txt is a synthetic Act (not real law)
eval/         questions.jsonl + evaluation script
data/raw/     source PDFs        data/processed/  parsed chunks (JSONL)
index/        persisted BM25 + Chroma index, shipped to Render
results/      metrics.md, comparison.png, data_quality.md
docs/PLAN.md  phase plan, design decisions, open questions
```
