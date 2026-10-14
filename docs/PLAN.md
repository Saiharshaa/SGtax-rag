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
| 1 | Ingestion: Act + guide parsers on the real PDFs, structured chunks, naive baseline chunks (~500 tokens, 50 overlap) | ready: sources in `data/raw/`, structure verified below |
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

## Document structure (verified 2026-10-14)

Sources, editions and checksums: [`data/raw/SOURCES.md`](../data/raw/SOURCES.md).

**Act** (`ITA_1947.pdf`, 1,323 pages, 2020 Revised Edition, version in force from 11/9/2026):

- Pages 1-16: arrangement of sections (TOC). Body starts on page 17; schedules run from page
  1225 to the end (12 schedules, First to Twelfth).
- 28 `PART n` lines in the body (Arabic numerals), each followed by an upper-case title line.
  No Divisions.
- Section heading on its own line, in **bold**, directly above `10.—(1) Income tax is ...`
  (or `9. All returns ...` when there are no subsections). This matches the assumptions the
  Phase 0 parser and fixture were built on, **except** that ~127 headings wrap onto two lines
  (s 14R: "Deduction for expenses incurred before first dollar of income / from trade,
  business, profession or vocation"). The Phase 0 parser only takes the last line, so Phase 1
  must collect headings by their bold font flag rather than by line position.
- 98 renumbered sections end with their pre-2020 number as a marker line (`[14T`). That
  gives an old → new map, so a question using an old number can still be resolved.
- Amendment notes `[Act 33 of 2022 wef 26/04/2024]` in a smaller font (9 pt vs 13 pt body).
- Running header `2020 Ed.  Income Tax Act 1947  <page>` and footer
  `Informal Consolidation – version in force from 11/9/2026` on every page: strip both.
- The key sections for the example questions are numbered under the 2020 Revised Edition:
  group relief is **s 37B** ("Group relief for Singapore companies"), renovation/refurbishment
  is **s 14N**. Older material online uses pre-2020 numbers (s 37C, s 14Q, s 14U).

**e-Tax guides** (5 PDFs, 13-52 pages each, all current editions published 30 Jan 2026):

- Numbered headings (`1  Aim`, `3  Glossary`) and paragraphs `2.1 ...` at the start of a line
  (24-57 numbered paragraphs per guide).
- Running header is the guide title; footer is the page number; footnotes sit at the page
  bottom ("3 Please refer to IRAS e-Tax Guide on ...").
- They cite Act sections inline with 2020 Revised Edition numbers ("section 37D of the Income
  Tax Act (“ITA”)", "Section 14R", "section 14N"). Citations sometimes wrap across lines
  ("section\n 37(3)(b)"); `rag/refs.py` already allows that.

Two parsers (`rag/parse_act.py`, `rag/parse_guide.py`) feed one chunk schema. Act sections cited
inside guide paragraphs are recorded as that chunk's `cross_refs`.

### Extraction findings (seed for Phase 1b)

- **Extractor choice:** pypdf runs words together ("Regulationsmadeforthepurposeofsubsection(3)").
  PyMuPDF `get_text(sort=True)` and poppler `pdftotext` keep the spacing. We use PyMuPDF: it's
  pip-installable (poppler isn't) and exposes bold flags for headings.
- **Non-breaking hyphens:** the Act uses U+2011 1,368 times ("pre‑commencement", "carry‑back"),
  so a plain search for "pre-commencement" misses them. Normalise U+2011 → `-` before anything else.
- **Odd glyphs:** `ð Þ × þ` appear ~24 times each in the Act: formulas set in symbol fonts that
  extract as Latin-1 letters. They're unreadable in chunks; list the affected sections in 1b.
- **Template residue:** the date-of-commencement guide's title page carries a leftover header
  from another guide ("Income Tax Treatment of REIT ETFs"); the pre-commencement guide's title
  page has overlapping, garbled text. Title pages are excluded from chunks.
- **Version gap:** the Act PDF is consolidated to 11 Sep 2026 and all five guides are dated
  30 Jan 2026, so the guides pre-date the Act version by ~7 months. Any 2026 amendments
  after January may not be reflected in the guides.
- **Legacy numbering:** 1 pre-2020 section number found across the guides (renovation guide).

## Data and copyright

The IRAS guides state that no part may be reproduced or "stored in a retrieval system of any
nature" without IRAS's written permission, which is exactly what a RAG index does. This is a
university project relying on educational fair use, but to limit exposure:

- The source PDFs are not committed to git (`.gitignore`); `data/raw/SOURCES.md` lists where to
  fetch them, with checksums.
- The deployed app shows short retrieved excerpts with citations, not whole documents.
- To decide before Phase 5: whether the Render app should be password-protected rather than public.

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
- Source PDFs stay out of git (IRAS copyright notice); `data/raw/SOURCES.md` + SHA-256 keep teammates on identical files.
- PyMuPDF (`sort=True`) for extraction; pypdf loses word spacing on these PDFs.

## Rubric mapping

| Criterion | Evidence |
|---|---|
| a. Coding practice | small single-purpose functions in `rag/`, pytest suite in `tests/` |
| b. Problem analysis + solution | this plan, baseline vs improved ablation in `results/metrics.md` |
| c. Data quality | `results/data_quality.md` (Phase 1b) |
| Cloud system with AI model + API | Streamlit on Render, Groq/Gemini APIs |

## Checks on the real PDFs

- [x] Text extraction quality: PyMuPDF `sort=True`; header/footer patterns identified
- [x] Part numbering is `PART 3` (Arabic); no Divisions
- [x] Section line format `10.—(1)` with a bold heading line above it
- [x] Table of contents present (pages 1-16); schedules at pages 1225-1323
- [x] Amendment note format `[Act 33 of 2022 wef 26/04/2024]`
- [x] Guide numbering, footnotes, headers; publication dates (all 30 Jan 2026)
- [x] No scanned pages: every page has a text layer, so no OCR needed
- [ ] Phase 1: whether any schedule has its own `PART` lines (the parser would misread them; stop at the first schedule instead)
- [ ] Phase 1: repealed-section format in the body
- [ ] Phase 1: split the Interpretation section (s 2) per defined term for one-hop definition expansion
- [ ] Phase 1: multi-line bold headings (~127); add a two-line-heading case to the fixture and tests
- [ ] Phase 1: strip `[14T`-style old-number markers from chunk text; keep them as metadata (old → new map)
