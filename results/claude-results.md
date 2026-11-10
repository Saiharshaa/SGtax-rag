# Claude Opus 5.5 as the answer model, against the IRAS Bot, and on a public tax benchmark

Three questions, tested on 7 November 2026 from [Legal_RAG_Exp](https://github.com/Khawpuneiei/Legal_RAG_Exp) on this repo's
corpus, chunks, Gemini index, prompt and citation checker:

1. How good is this pipeline with a frontier answer model, Claude Opus 5.5, in place of the local qwen stand-ins of
   [`experiments.md`](experiments.md)?
2. How does it compare with IRAS's own chatbot?
3. How does Claude do on a public tax benchmark with a published leaderboard?

**The app is unchanged.** It still answers with gpt-oss-120b on Groq, which has still not been tested. Claude was plugged
in through the `ChatModel` protocol in [`rag/llm.py`](../rag/llm.py) (`complete(system, user)`), so `rag.generate`
ran as it is. The adapter is Legal_RAG_Exp's `src/llm/claude.py`.

Full write-up, code and per-question grades:
[`docs/taxrag-claude-results.md`](https://github.com/Khawpuneiei/Legal_RAG_Exp/blob/main/docs/taxrag-claude-results.md)
([Khawpuneiei/Legal_RAG_Exp#3](https://github.com/Khawpuneiei/Legal_RAG_Exp/pull/3)).

## Setup

- **Pipeline:** `improved` on the Gemini index (2,500 tokens of hits plus up to 3 sections they cite), your system
  prompt, numbered sources, citation rewriting, and your rule that an answer citing no source becomes a refusal. This
  is B0 in [`experiments.md`](experiments.md).
- **Model:** Claude Opus 5.5 (`claude-opus-5-5`) through the Anthropic API, effort `medium`, up to 16,000 output
  tokens. The app's cap is 2,000; no reply in the pipeline used more than 1,489. With no retrieval, 4 of the 79 replies
  went past 2,000 tokens (largest 2,177), which the app's cap would cut.
- **Questions:** the same held-out test split as [`experiments.md`](experiments.md).
  - 79 answerable questions with gold sections and paragraphs (59 in plain language, 16 citing a section, 4 citing a
    former section number), plus 20 the corpus can't answer.
  - They were written from this corpus and audited by LLM agents, not by tax professionals or users.
- **Judging:**
  - Each question's answers from every system were graded blind (correct, partial or incorrect against the gold
    sections) by two LLM judges reading them in opposite orders, with a third on each disagreement.
  - 243 distinct answers; the first two judges agreed on 95% (κ 0.91).
  - "Correct (all)" counts partial as half and an unanswered question as 0.
  - The judges are Claude agents, and no person checked the grades.

## This pipeline with Claude: 79 answerable test questions

| System | Answered | Correct / partial / incorrect | Correct (all) | Fully correct |
|---|---|---|---|---|
| **Claude Opus 5.5 in this pipeline** | 78 | 71 / 6 / 1 | **0.937** | 0.899 |
| qwen3:8b in this pipeline (the earlier stand-in) | 71 | 47 / 19 / 5 | 0.715 | 0.595 |
| Claude Opus 5.5 with no retrieval | 79 | 33 / 27 / 19 | 0.589 | 0.418 |

Paired over the 79 questions (95% bootstrap CI, Wilcoxon p):
- Claude in this pipeline − qwen3:8b in this pipeline: **+0.222 [+0.139, +0.304]**, p < 0.001, 31 questions better,
  3 worse.
- Claude in this pipeline − Claude with no retrieval: **+0.348 [+0.247, +0.456]**, p < 0.001; wrong answers 1 against
  19.
  - "No retrieval" means the question alone with a short system prompt, without your refusal rule: what a general
    assistant knows by itself.
- qwen3:8b in this pipeline − Claude with no retrieval: +0.127 [+0.006, +0.253], p = 0.08.

Notes:
- **Out of scope:** Claude declined all 20 questions the corpus can't answer; qwen3:8b declined 17.
- **Unanswered:** most of qwen3:8b's 8 unanswered questions were replies cut off at the 2,000-token cap, thinking
  included. Claude declined 1 (h021, below).
- **Your 28 questions:** 25 of 25 answered and 3 of 3 out-of-scope declined. These answers were not judged.
- **By type:** 0.949 on plain-language questions, 0.938 on those citing a section, and 0.750 on the 4 citing a former
  section number.
- **Citations:**
  - Claude cites more of the gold sections and paragraphs: 0.878 against 0.776 (gold cited, all).
  - Its citation precision is lower: 0.472 against 0.569, because it cites more of the sources it is given.
  - The sources held 92% of the gold units, so retrieval now sets most of the remaining ceiling.
- **The one wrong answer (h021) is a retrieval miss.**
  - The question applies s 37B(17), which works through s 37A(4).
  - `improved` returned s 37B(17) but not s 37A(4), and Claude, told to answer only from the sources, said it could not
    compute the figure.
- **Judging rounds:** qwen3:8b scored 0.747 on the same answers in [`experiments.md`](experiments.md) and 0.715 here.
  The two judging rounds differ by about 0.03.

**Deep Tax Search** (`improved_astar`, the app toggle) was also run with Claude and judged blind against `improved` in a
separate pool of the same design (155 distinct answers, 97% agreement):
- It scored 0.949 against 0.943, +0.006 [−0.019, +0.038]: no measurable difference. (The same `improved` answers score
  0.943 in this pool and 0.937 in the main one.)
- It turned one refusal into a right answer and one partial answer into a wrong one.
- It did not fix h021: its context also lacks s 37A(4).

## Against the IRAS Bot: 25 sampled questions

The IRAS Bot ("Chat with IRAS" on iras.gov.sg, on GovTech's VICA platform) was the one free, public, no-login Singapore
tax chatbot found.
- It was asked a seeded sample of 25 of the 79 answerable questions (19 plain-language, 5 citing a section, 1 citing a
  former number), each once and as written, in a fresh conversation, on 7 November 2026.
- Its "please rephrase" fallback counts as no answer.
- Its replies are not published, because the IRAS website's terms bar republishing its content.

| System | Answered (of 25) | Correct / partial / incorrect | Correct (all) | On its own answered questions |
|---|---|---|---|---|
| **Claude Opus 5.5 in this pipeline** | 25 | 22 / 2 / 1 | **0.920** | 0.920 |
| qwen3:8b in this pipeline | 23 | 14 / 7 / 2 | 0.700 | 0.761 |
| Claude Opus 5.5 with no retrieval | 25 | 11 / 9 / 5 | 0.620 | 0.620 |
| IRAS Bot | 15 | 12 / 2 / 1 | 0.520 | 0.867 |

- **Claude in this pipeline − IRAS Bot: +0.400 [+0.180, +0.620]**, p = 0.005, 13 questions better, 2 worse.
- **The gap is coverage.**
  - On the 15 questions it answered, the IRAS Bot scores 0.867 and Claude in this pipeline 0.900.
  - On the other 10 it asked for a single short message of at most 15 words.
  - All 25 are scenario questions for tax associates, 23 to 58 words each, far over that guidance. It answered long
    questions as well as short ones, so length alone does not explain which got the fallback.
- **The result held up on a stricter re-grade.**
  - Two fresh judges re-graded the sample, told to recompute every figure and not to assume any answer is right.
  - They changed 8 of the 100 grades, all downgrades, 6 of them for Claude with no retrieval.
  - Claude in this pipeline − IRAS Bot was +0.380 [+0.140, +0.600].
- **chat.gov.sg is left out.** The whole-of-government assistant was also asked these questions and its answers were
  judged in the same pool, but its terms of use forbid benchmarking the service, so its results are not reported. The
  linked write-up says how that happened.

## Claude alone on TaxCalcBench (US federal returns)

There is no public Singapore tax benchmark with answers. [TaxCalcBench](https://github.com/column-tax/tax-calc-bench)
(Column Tax, MIT licence) has open data, an objective score and a published leaderboard. It gives the model a
taxpayer's data and asks for a completed Form 1040. This tests Claude alone, with no retrieval and no Singapore corpus.
- **Run:** its TY 2024 set (51 returns) had no Claude Opus 5.5 row, so it was run with the benchmark's own prompt, data
  and evaluator.
- **Fully correct returns:** 64.71% at the benchmark's default effort, and 66.67% one level up.
  - The best published TY24 row is 62.75% (GPT-5.4 Pro and GPT-5.4).
  - That lies inside each run's 95% interval (51% to 76% at the default).
  - At the same level, the best published run is 58.82% (GPT-5.4 Pro); GPT-5.4 scores 56.86% and Claude Opus 4.6
    52.94%.
- **Not like for like:**
  - The TY24 board stops at models of early 2026.
  - Its answer keys have been public since July 2025, so a newer model may have seen them.
  - On Column Tax's own TY25 board, Claude Opus 5.5 gets 42% without web search, tied second.

## Cost

- $4.65 at list prices for 127 answers through this pipeline (the 99 test questions and your 28): $0.037 an answer,
  8 s median.
- Deep Tax Search $4.63 more; TaxCalcBench $5.41 and $7.17; the whole round $24.34.

## What this means for the app

- **With a strong answer model, this pipeline is right on almost all of these questions, and retrieval sets most of
  what is left.** The one wrong answer is a missed cross-reference, and the contexts held 92% of the gold units.
- **Retrieval probably matters more than the model.** On these questions, removing retrieval (with your prompt and
  refusal rule) cost Claude more than swapping in qwen3:8b: +0.127 [+0.006, +0.253], but Wilcoxon p = 0.08, and only one
  model swap was tried.
- **Not tested: gpt-oss-120b.** How the app's own model compares is still open. The next useful check, given a Groq
  key, is the same 79 questions through the app's model.
- **Using Claude in the app** would need four things, none of which this PR adds:
  - a `ChatModel` for it in `rag/llm.py`;
  - that model added to `default_models()`;
  - the `anthropic` package in `requirements.txt`;
  - an `ANTHROPIC_API_KEY`.

## Caveats

- **The judges are LLMs, and Claude models.** Two of the four reported systems are Claude (chat.gov.sg's answers were
  also in the pool), and the questions were also written by LLM agents.
  - The judging is blind and anchored on the gold sections, but an answer's style can give its system away.
  - The stricter re-grade suggests the first judges were generous to Claude with no retrieval.
  - No person or non-Claude judge has checked the grades.
- **This pipeline has a home advantage.** The questions were written from the e-Tax Guides and the Act in this corpus,
  and the judges see the gold units in the form this pipeline cites them. The IRAS Bot retrieves from iras.gov.sg pages
  that may not hold the same paragraphs.
- **The IRAS Bot was asked questions it is not designed for.** A short FAQ-style set would measure it differently. Each
  question was asked once with no rephrasing, and the bot may change.
- **25 questions** for the bot comparison means wide intervals, though the gap excludes 0 on both gradings.
