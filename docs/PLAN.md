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
| 1 | Ingestion: Act + guide parsers on the real PDFs, structured chunks, naive baseline chunks (~500 tokens, 50 overlap) | **done**: `python scripts/build_chunks.py` (3,577 structured, 1,017 naive) |
| 1b | `results/data_quality.md` + chunk-length histogram (see below) | **done**: `python scripts/data_quality.py` |
| 2 | Retrieval: BM25 + Chroma dense, RRF merge, exact-section boost, optional one-hop expansion, `baseline`/`improved` flag | **done**: `python scripts/build_index.py` (~45 min on the Gemini free tier, resumable), `python scripts/search.py "..."` |
| 3 | Generation: Groq (Gemini fallback), answer only from retrieved chunks, cite `[ITA 1947, s X(Y)]`, refuse when context is insufficient | **done**: `python scripts/ask.py "..."` |
| 4 | Evaluation: `eval/questions.jsonl` (25-30, DRAFT until reviewed), Recall@5, MRR, citation correctness on 10; `results/metrics.md` + `comparison.png` | **done** except the naive dense baseline (index still building): `python scripts/evaluate.py --answers 10`; questions await review |
| 5 | Streamlit app, `render.yaml`, README with mermaid diagram + design decisions, memory check under 512 MB | **done**: live on Render; `streamlit run app.py` peaks at ~200 MB. Demo video: `python scripts/record_demo.py` |

Each phase ends with a summary and a stop for review.

### Phase 1b: data quality report (`results/data_quality.md`)

- Document versions and dates; whether each guide pre-dates or post-dates the Act edition used
- Parse coverage: sections expected vs parsed, empty or truncated chunks, chunk length distribution (+ histogram PNG)
- Cross-reference integrity: share of cited sections that resolve to a parsed chunk; list of unresolved ones
- Known gaps: repealed/amended provisions, content outside the corpus, OCR/formatting errors

Short and factual; it feeds a slide directly.

### Phase 2: retrieval (`rag/retrieve.py`)

`Retriever.search(query, config, k)` runs BM25 and/or dense search over one corpus (50 candidates
each), merges them with reciprocal rank fusion (k = 60), adds the section boost, and returns the
top k with each hit's BM25 and dense rank so results can be explained.

| Config | Corpus | BM25 | Dense | Section boost | Expansion | Role |
|---|---|---|---|---|---|---|
| `naive_dense` = `baseline` | naive | | ✓ | | | the approach the project argues against |
| `structured_dense` | structured | | ✓ | | | ablation: chunking alone |
| `structured_hybrid` | structured | ✓ | ✓ | | | ablation: + BM25 |
| `structured_hybrid_boost` | structured | ✓ | ✓ | ✓ | | ablation: + section boost |
| `improved` | structured | ✓ | ✓ | ✓ | ✓ | what the app uses |
| `naive_bm25`, `structured_bm25`, `structured_bm25_boost` | | ✓ | | | | extra rows; also work without an API key |

- **Section boost.** For each section named in the question ("s 14R(2)", "section 37B"), the two
  best-ranked chunks the retrievers found get a bonus worth one extra first-place vote in the fusion
  (1/61), narrowed to the subsection when it is a chunk of its own. A number means the current section
  with that number; a pre-2020 number counts only when no current section has it ("14U" → s 14R), because
  71 of the 98 former numbers are also current numbers. Sections of other Acts are ignored.
- **Boost, version 1 → 2.** The first version gave the bonus to *every* chunk of a named section, including
  chunks no retriever found, plus half the bonus to the section a former number became. The Phase 4
  evaluation showed this flooding the top 5: "section 14Q" (renovation, before 2020) filled it with today's
  s 14Q, which is a different provision, and recall on the two former-number questions fell from 0.75 to
  0.25. Version 2 only re-ranks retrieved chunks, caps the bonus at two per section, and lets current
  numbering win. It was designed after seeing those two questions, so treat its numbers as tuned on them.
- **One-hop expansion.** For the top hits, the first chunk of each Act section they cite (max 3) is returned
  separately as extra context for generation. It never changes the ranking, so Recall@5/MRR are unaffected.
- **Dense index.** Gemini `gemini-embedding-001` at 768 dimensions, `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`
  task types, backoff on 429/5xx. Each vector is stored with a hash of its text, so a build interrupted by
  the free-tier quota resumes where it stopped. The collection records the embedder, and querying with
  another one raises.
- **Free-tier quota.** The free tier allows 100 embedding requests a minute, counts every text in a batch
  as one, and counts rejected requests too. Quick retries therefore kept the window full and the build
  livelocked. Requests now go in batches of 50, paced client-side to 100 texts a minute, and a 429 waits for
  its "retry in N s" hint or a full minute: ~45 min for both corpora. `gemini-embedding-2` was tried and
  rejected: it merges a batch of texts into one vector.
- **Measured** (3,577 chunks, offline hash embedder standing in for Gemini): BM25 builds in under 1 s,
  Chroma holds 14.5 MB on disk, a warm hybrid query takes ~20 ms, and the process peaks at 167 MB RSS.
  onnxruntime (installed with chromadb) is never imported because embeddings are passed in explicitly.
- **Bug found by the dense build.** Chroma rejected duplicate chunk ids: cross-references wrapped onto a
  line start ("... under subsections (1),\n(1AA) and (2C).") were parsed as new subsections. A line now
  opens a subsection only if its text starts like a sentence and the label is new. This removed 90
  fragment chunks (3,667 → 3,577) and 65 duplicate ids; `results/data_quality.md` is regenerated.

### Phase 3: generation (`rag/generate.py`, `rag/llm.py`)

`answer(question, retriever, models)` retrieves with the `improved` config (top 5 + up to 3 cross-referenced
sections), asks the model, and checks the citations.

- **Models.** Groq `openai/gpt-oss-120b` (temperature 0, reasoning effort medium; 1-3 s per answer), with
  Gemini `gemini-3.8-flash` as the fallback when Groq fails after its own retries. `gemini-2.5-flash` is
  closed to new API keys. Override with `GROQ_MODEL` / `GEMINI_CHAT_MODEL`.
- **Citations by number.** Sources are numbered `[1]`..`[n]` in the prompt and the model cites numbers; the
  code rewrites them as `[ITA 1947, s 14R(2)]` / `[e-Tax Guide: ..., para 5.1]`. Every citation in an answer
  is therefore well-formed and points at a chunk the model was shown. Adjacent marks merge into one
  citation, OpenAI-style `【1†L3】` marks are understood, and numbers outside the list are dropped and
  reported (`Answer.invalid_citations`, for Phase 4's citation-correctness check).
- **Refusal.** The model is told to reply with one fixed sentence when the sources don't answer. An answer
  with no valid citation is also turned into that refusal (the raw output is kept in `Answer.raw`): an
  uncited tax answer is worse than none. Nothing retrieved means no model call.
- **Spot checks** (structured BM25 + boost, before the dense index existed): the pre-commencement question
  is answered from s 14R(1)-(2), s 14X(3) and the guide's paras 2.1 and 4.2; the R&R cap question gives
  $300,000 per three-year period from paras 5.1-5.5; "What is the current GST rate?" is refused.
- **Context by tokens, not chunk count** (changed in Phase 4). Answers get 2,500 tokens of retrieved
  chunks, the size of five naive chunks, plus up to three cross-referenced sections. With top 5, the
  structured config gave the model ~400 tokens and refused 4 of 10 answerable questions.

### Phase 4: evaluation (`rag/evaluate.py`, `scripts/evaluate.py`)

Results with the structured Gemini index (the naive one is still being built, so `naive_dense`, the
planned baseline, is pending; naive BM25 stands in). Full tables: [`results/metrics.md`](../results/metrics.md);
answers: [`results/answers.md`](../results/answers.md).

| Config | Recall@5 | MRR@10 | Recall @ 2,500 tokens |
|---|---|---|---|
| naive BM25 | 0.44 | 0.46 | 0.44 |
| structured BM25 | 0.42 | 0.43 | 0.59 |
| structured dense (Gemini) | 0.63 | **0.81** | 0.80 |
| structured hybrid + boost | 0.59 | 0.63 | 0.78 |
| **structured routed = `improved`** | **0.71** | 0.80 | **0.81** |

| Answers (10 answerable + 3 out of scope) | naive BM25 | `improved` |
|---|---|---|
| Answerable questions answered | 8 / 10 | **10 / 10** |
| Citation precision | 0.42 | 0.44 |
| Out-of-scope questions refused | 3 / 3 | 3 / 3 |

- **Structure wins at equal context.** Given the same 2,500 tokens, structure-aware chunks find 81% of gold
  units (`improved`) against 44% for naive BM25. Top-5 alone hides this: five naive chunks hold six times
  the text.
- **Hybrid was not better than dense, so the app routes.** Merging BM25 into the dense ranking (RRF) lowered
  MRR from 0.81 to 0.64: on plain-language questions BM25's ranking pulls good dense results down (Recall@5
  0.57 hybrid vs 0.66 dense), while on questions that name a section it helps (0.67-0.75 vs 0.50-0.56).
  `improved` therefore uses dense search, and adds BM25 and the section boost only when the question names
  a section: Recall@5 0.71, the best row. The routing rule was chosen after seeing these results on the same
  25 questions, so treat 0.71 as tuned on them.
- **Citations a reader can check.** Structure-aware answers cite `[ITA 1947, s 37D(6)]` or `[e-Tax Guide:
  Carry-back Relief System, para 9.1]`; naive chunks carry no section or paragraph, so naive answers cite
  only the document and sometimes add paragraph numbers of their own (`[9.1][9.3]`).
- **Citation precision is about even (0.44 vs 0.42).** `improved` cites more sources per answer, including
  ones next to the gold paragraphs, which this automatic measure counts as misses.
- **A known failure: q01** (two Singapore companies 80% owned by a Hong Kong parent). Dense retrieval misses
  GR para 6.3, which disregards shareholdings held by foreign companies, and the model wrongly concludes the
  80% holding qualifies. BM25 found para 6.3 in the earlier run. Worth a look before the presentation.
- **Refusals.** All configs refuse all three out-of-scope questions. With BM25, the refusals on answerable
  questions (q02, q08) were retrieval misses; `improved` answers both.
- **Caveats.** 25 answerable questions, 5 of them naming sections: differences of a few points are within
  noise. The questions are DRAFT until reviewed, and both the boost's version 2 and the routing rule were
  chosen after seeing results on them. Citation precision is automatic; whether each answer is right is for
  manual review in `results/answers.md`.
- **Questions to review** (DRAFT notes from drafting):
  - q09: DC:2.2 and DC:4.3 contain the same list word for word; both are gold, so Recall@5 needs both.
  - q12: gold is `DC:6`, because the date-of-commencement guide's annex of industry examples is parsed
    into paragraph 6 ("Updates and amendments"). That is a parser gap: the guide parser doesn't detect
    this annex. Relabel q12 if it is fixed.
  - q19, q21: `RR:12` is the renovation guide's whole FAQ annex (6 chunks), so a hit on any of them counts.
  - q25: the Act and the guide frame the default differently. Under s 14N(3A) the one-year write-off is the
    default for YA 2021, 2022 and 2024 onwards unless the taxpayer elects three years; the guide (para 4.2)
    presents one year as the election. Both say the choice is irrevocable.
  - q05: PC:2.2 and DC:3.4 also state the 12-month look-back but aren't gold, so retrieving them instead of
    s 14R or PC:4.2 counts as a miss.
- **Pending:** `naive_dense` (the planned baseline) and answers from `baseline`, once the naive Gemini index
  is built (`python scripts/build_index.py --corpus naive`; requests are now capped by size, which the
  naive chunks needed). Then rerun `python scripts/evaluate.py --answers 10`.

### Phase 5: app and deploy (`app.py`, `render.yaml`)

- **App.** A chat-style Streamlit page with three example questions. Each answer shows the model, the time
  and the retrieval used, and an expander with the cited sources as 600-character excerpts. A toggle
  shows the naive-chunk answer in a second tab, so the project's claim can be seen in a demo. Dollar
  amounts are escaped, because Streamlit reads `$...$` as LaTeX.
- **Degrades instead of failing.** `answer_best_available()` uses `improved` and falls back to the same
  pipeline on BM25 (`improved_bm25`) when dense search can't run: index incomplete, embedding quota used
  up, or Gemini down. The caption says which retrieval answered.
- **Access.** `APP_PASSWORD` turns on a sign-in form (constant-time comparison); without it the app is open,
  which is how it runs locally.
- **Memory.** Signing in, answering an example, then a comparison question peaks at 194 MB in-process
  (Windows, BM25 retrieval; `streamlit.testing` AppTest with the real index and Groq). Render's limit is
  512 MB; Chroma and the Streamlit server add some on top.
- **Deploy.** `render.yaml` is a Blueprint for a free Python 3.11.16 web service: `pip install -r
  requirements.txt`, then `streamlit run app.py` on `$PORT`, with a health check on `/_stcore/health`.
  The three secrets are set in the dashboard (`sync: false`).
- **Speed.** One answer takes 2-4 s. With the comparison on, the second model call often waits for Groq's
  free-tier tokens-per-minute limit: 30-40 s in testing.

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
- The deployed app shows short retrieved excerpts (600 characters) with citations, not whole documents.
- Decided in Phase 5: the app is password-protected (`APP_PASSWORD`), and the index the app needs, which
  contains the documents' text, is committed to the private repo so Render can serve it. Building it at
  deploy time would need the PDFs, which stay out of git.

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
  structured + hybrid + section boost. BM25-only rows (naive, structured, structured + boost) are
  added: they need no API key, and they separate chunking from retrieval method too.
- **Equal context**: top-5 is not a fair comparison on its own. A naive chunk is 500 tokens and a
  structured one ~80 (median), so five naive chunks give the model six times the text. Each row also
  reports **Recall @ 2,500 tokens**: chunks taken in rank order until they fill the space of five naive
  chunks.
- **Question set** (`eval/questions.jsonl`, 28, DRAFT): 20 plain-language questions across the five guide
  topics, 3 that name a section with 2020 numbering, 2 that use a pre-2020 number, and 3 the corpus can't
  answer (GST rate, buyer's stamp duty, property tax rate), which test refusal. Drafted from the documents
  with an evidence quote per question; `tests/test_questions.py` checks that every gold label exists and
  every quote appears in a gold chunk.

## Design decisions so far

- Two parsers, one schema: Act and guides are structured differently, but retrieval and the UI shouldn't care.
- Empty strings rather than `None` in chunk fields: ChromaDB metadata rejects `None`.
- Gemini embeddings via API for both indexing and queries: a local model would need torch at query time, which Render's 512 MB can't hold.
- `requirements.txt` holds runtime deps only (what Render installs); PDF parsing, charts and tests go in `requirements-dev.txt`.
- The Act parser assumes section numbers only increase, and treats a second "section 1" as the end of the table of contents.
- Schedules are skipped for now; they'll be added if the eval questions need them.
- Source PDFs stay out of git (IRAS copyright notice); `data/raw/SOURCES.md` + SHA-256 keep teammates on identical files.
- PyMuPDF (`sort=True`) for extraction; pypdf loses word spacing on these PDFs.
- BM25 is hand-rolled (~60 lines, Snowball stemming, JSON on disk) rather than `rank_bm25`: no numpy at query time, and every scoring step is visible for the report.
- Fusion by rank (RRF), not score: BM25 scores and cosine similarities are on different scales.
- Built indexes stay out of git for now: `index/<corpus>/chunks.jsonl` holds the IRAS text. How they reach Render (commit to the private repo, or a build step) is decided in Phase 5.

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
- [x] Parsing stops at the first schedule, so Part lines inside schedules can't confuse it
- [x] Repealed sections (`5. [Repealed by ...]`) and deleted subsections (`[Deleted by Act ...]`) are skipped
- [x] s 2(1) is split one chunk per defined term (`defined_term` field)
- [x] Multi-line bold headings joined at extraction (tested)
- [x] `[14T`-style old-number markers kept as `former_section` metadata, not chunk text
- [x] Cross-references wrapped onto a line start ("(1AA) and (2C).") don't open subsections; chunk ids are unique (tested)
