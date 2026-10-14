# Plan

## Problem

Tax associates and accountants at SME-focused accounting firms answer corporate income tax
questions by manually searching the Income Tax Act 1947 (ITA) and IRAS e-Tax guides. This
tool answers in seconds, cites the exact section or guide paragraph for every claim, and
says so when the sources don't cover the question.

The core claim, which the evaluation must prove or disprove: **structure-aware chunking +
hybrid retrieval beats naive fixed-size chunking on legal text.**

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Plan, repo layout, chunk schema, parser interfaces, section-reference detector, synthetic Act parser + tests | **done** |
| 1 | Ingestion: Act + guide parsers on the real PDFs, structured chunks, naive baseline chunks (~500 tokens, 50 overlap) | blocked: PDFs not in `data/raw/` yet |
| 1b | `results/data_quality.md` + chunk-length histogram (see below) | after 1 |
| 2 | Retrieval: BM25 + Chroma dense, RRF merge, exact-section boost, optional one-hop expansion, `baseline`/`improved` flag | |
| 3 | Generation: Groq (Gemini fallback), answer only from retrieved chunks, cite `[ITA 1947, s X(Y)]`, refuse when context is insufficient | |
| 4 | Evaluation: `eval/questions.jsonl` (25-30, DRAFT until reviewed), Recall@5, MRR, citation correctness on 10; `results/metrics.md` + `comparison.png` | |
| 5 | Streamlit app, `render.yaml`, README with mermaid diagram + design decisions, memory check under 512 MB | |

Each phase ends with a summary and a stop for review.

### Phase 1b: data quality report (`results/data_quality.md`)

- Document versions and dates; whether each guide pre-dates or post-dates the Act edition used
- Parse coverage: sections expected vs parsed, empty or truncated chunks, chunk length distribution (+ histogram PNG)
- Cross-reference integrity: share of cited sections that resolve to a parsed chunk; list of unresolved ones
- Known gaps: repealed/amended provisions, content outside the corpus, OCR/formatting errors

Short and factual; it feeds a slide directly.

## Document structure

**Assumed until the PDFs land; to be verified before Phase 1.**

- **Act** (Singapore Statutes Online revised edition): table of contents, then Parts → sections →
  subsections `(1)` → paragraphs `(a)` → sub-paragraphs `(i)`. Section numbers carry letter
  suffixes (`14Q`), paragraph letters can run past `(z)` (`(za)`), definitions sit in the
  Interpretation section, amendment notes appear as `[Act 5 of 2019 wef ...]`, and schedules
  follow the sections.
- **e-Tax guides**: numbered headings and paragraphs (`2`, `2.1`, `2.1.1`), worked examples,
  annexes; they cite Act sections inline ("section 14(1) of the ITA").

Two parsers (`rag/parse_act.py`, `rag/parse_guide.py`) feed one chunk schema. Act sections cited
inside guide paragraphs are recorded as that chunk's `cross_refs`.

## Chunk schema

Defined in [`rag/schema.py`](../rag/schema.py). Examples:

| field | Act chunk | guide chunk | naive chunk |
|---|---|---|---|
| `chunk_id` | `ITA:s14Q(2)#1` | `etax_group_relief:p5.2#1` | `naive:ITA_1947.pdf#0042` |
| `doc_type` | `act` | `guide` | `naive` |
| `path` | `Income Tax Act 1947 > Part 6 > s 14Q > (2)` | `<guide title> > 5 Conditions > 5.2` | empty |
| `section` / `subsection` / `para` | `14Q` / `2` / empty | empty / empty / `5.2` | empty |
| `cite` | `ITA 1947, s 14Q(2)` | `<guide title>, para 5.2` | empty |
| `cross_refs` | sections cited in the text | Act sections cited in the paragraph | empty |
| `char_start` / `char_end` | span in extracted text | span in extracted text | span in extracted text |

The path and heading are prepended to the text before indexing (`Chunk.embed_text()`).

## Evaluation design

- **Gold labels** are Act section numbers, plus guide paragraph IDs where a guide is the real
  answer. Questions are drafted from the documents in the style of the examples ("Can a company
  deduct expenses it incurred before it started its business?") and stay DRAFT until reviewed.
- **Scoring naive chunks**: they have no section labels, so a naive chunk counts as a hit for a
  gold section when its character span overlaps that section's span. Both chunkers run over the
  same extracted text, so this is fair.
- **Ablation**: the core claim changes chunking and retrieval at once. To show which one helps,
  the results table has four rows: naive + dense, structured + dense, structured + hybrid,
  structured + hybrid + section boost.

## Design decisions so far

- Two parsers, one schema: Act and guides are structured differently, but retrieval and the UI shouldn't care.
- Empty strings rather than `None` in chunk fields: ChromaDB metadata rejects `None`.
- Gemini embeddings via API for both indexing and queries: a local model would need torch at query time, which Render's 512 MB can't hold.
- `requirements.txt` holds runtime deps only (what Render installs); PDF parsing, charts and tests go in `requirements-dev.txt`.
- The Act parser assumes section numbers only increase, and treats a second "section 1" as the end of the table of contents.
- Schedules are skipped for now; they'll be added if the eval questions need them.
- Source PDFs are committed to this private repo so every teammate builds the same index.

## Rubric mapping

| Criterion | Evidence |
|---|---|
| a. Coding practice | small single-purpose functions in `rag/`, pytest suite in `tests/` |
| b. Problem analysis + solution | this plan, baseline vs improved ablation in `results/metrics.md` |
| c. Data quality | `results/data_quality.md` (Phase 1b) |
| Cloud system with AI model + API | Streamlit on Render, Groq/Gemini APIs |

## To verify when the PDFs land (before Phase 1)

- [ ] Text extraction quality: pypdf vs PyMuPDF; running headers, footers, page numbers
- [ ] Part numbering (`PART 3` vs `PART III`); whether Divisions exist
- [ ] Section line format (`10.—(1)`) and heading placement above the number
- [ ] Table of contents present; whether any schedule contains its own `PART` headings (the parser would misread them)
- [ ] Format of amendment notes and repealed sections
- [ ] Definitions: split the Interpretation section per defined term so definitions can be pulled in by one-hop expansion
- [ ] Guide numbering, examples, annexes, footnotes; publication date of each guide
- [ ] Any scanned pages that would need OCR
