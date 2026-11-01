# Experiment results: legal-RAG methods, skills and harnesses on this pipeline

These experiments asked whether the methods and research questions of
[Legal_RAG_Exp](https://github.com/Khawpuneiei/Legal_RAG_Exp), a legal-agreement drafting RAG, carry over to this
tax RAG. They ran on this repo's corpus, chunks, prompt, citation checker and token budget at `ac04f49`, between
29 October and 1 November 2026, on one laptop (RTX 4060, 8 GB). This PR adds the two changes that came out of them:
**Deep Tax Search** (`improved_astar`) and the reply **Retry**.

Full write-ups, code and per-question outputs, in Legal_RAG_Exp. Until
[Khawpuneiei/Legal_RAG_Exp#2](https://github.com/Khawpuneiei/Legal_RAG_Exp/pull/2) is merged, they are on its
`taxrag-transfer` branch:
- [`docs/taxrag-results.md`](https://github.com/Khawpuneiei/Legal_RAG_Exp/blob/main/docs/taxrag-results.md): retrieval methods (part 1);
- [`docs/taxrag-rq12-protocol.md`](https://github.com/Khawpuneiei/Legal_RAG_Exp/blob/main/docs/taxrag-rq12-protocol.md): the plan for part 2, written before any answer existed;
- [`docs/taxrag-rq12-results.md`](https://github.com/Khawpuneiei/Legal_RAG_Exp/blob/main/docs/taxrag-rq12-results.md): skills and harnesses (part 2);
- [`docs/experiment1-results.md`](https://github.com/Khawpuneiei/Legal_RAG_Exp/blob/main/docs/experiment1-results.md): the same skill question on legal drafting.

## Setup

- **Questions:** 149 new questions with gold sections and paragraphs.
  - **Test: 79 answerable and 20 the corpus can't answer.** No setting was tuned and no skill text was written on
    them, but they were used in more than one round. `improved_astar` was designed after a review of an earlier
    A\* variant's test results; its own settings were then tuned on dev. The choices under "What this PR takes
    from it" follow the results on test and dev.
  - **Dev: 40 and 10.** They tuned `improved_astar`'s settings. In part 2 the skill and the combination C were
    written or chosen on dev before any test answer was judged.
- **Retrieval:** your Gemini index and `improved` as deployed, unless a row says otherwise. Your published table
  (Recall@5, MRR and Recall@2,500 on the 28 questions in `eval/`) reproduces exactly through your code.
- **Answer models:** without a Groq key, and with only 20 Gemini requests a day, the answers come from local models:
  qwen2.5:7b, and qwen3:8b as a reasoning stand-in for gpt-oss-120b, with your prompt and your 2,000-token cap
  (thinking included).
- **Judging:**
  - Answers were graded blind (correct, partial or incorrect, condition hidden) by two LLM judges, with a third
    on each disagreement.
  - In part 2, each question's answers were shown side by side, and the two judges read them in opposite orders.
  - "Correct (all)" counts partial as half and an unanswered question as 0, over the answerable questions.
  - No person checked the grades.
- **Tests:** paired bootstrap CIs over questions, and Wilcoxon signed-rank p. Part 2's three primary comparisons
  are Holm-adjusted.

## Part 1: retrieval methods from the legal experiment

| Method | Legal agreements | This corpus (79 test questions) | Carries over? |
|---|---|---|---|
| Cross-encoder reranker | nDCG@10 +0.072, significant | No variant beats `improved` on Gemini; on your own first stage −0.089 R@2,500 and −0.129 MRR (significant) | No |
| Contextual chunks | Recall@5 +0.130, significant | +0.032 R@2,500, not significant (local embedder; not run on Gemini, it would re-embed every chunk) | Not shown |
| A\* dependency expansion (`improved_astar`) | Definition coverage +0.64 | Same hits and tokens as `improved`: the hits' own references, definitions and split pieces resolved 0.706 against 0.499 (+0.207, significant); gold sections 0.926 against 0.918 | Yes, for the evidence |
| Abstention gate | Not needed | Not worth it: the model already leaves most out-of-scope questions unanswered (qwen2.5:7b 20 of 20; qwen3:8b 20 of 20 in part 1, 17 of 20 with `improved` in part 2), and the gate also blocks some right answers | Mostly the same |

**Answers:** no retrieval change made answers significantly more or less correct.
- `improved_astar` against `improved`:
  - qwen2.5:7b: −0.006 [−0.076, +0.070];
  - qwen3:8b: +0.025 [−0.038, +0.089] in part 1, +0.019 in part 2.
- The answer model matters more. On the same contexts in part 1, qwen3:8b lifts `improved` from 0.513 to 0.728
  and cuts wrong answers from 25% to 6%.

## Part 2: skills and harnesses (qwen3:8b, judged 1 November 2026)

The legal project's RQ1 (does a `SKILL.md` playbook help?) and RQ2 (does a harness beat a single LLM call?),
asked of this pipeline. 741 distinct answers were judged; the first two judges agreed on 94% of the answers they
both graded (κ 0.88). A fresh blind re-grade of the 240 answers that decide the comparisons agreed on 93% and
changed no conclusion. B0 and B1 were generated and judged again for this part, so their 0.747 and 0.766 are a
second run of part 1's 0.728 and 0.753.

| Condition | What it is | Correct (all) | Answered (of 79) | Answered wrongly | Out-of-scope answered (of 20) | Chat calls per question |
|---|---|---|---|---|---|---|
| B0 | `improved`, the app today | 0.747 | 71 | 5 | 3 | 1.0 |
| B1 | `improved_astar` | 0.766 | 70 | 5 | 1 | 1.0 |
| S2 | focused tax skill, chosen on dev | 0.722 | 75 | 10 | 1 | 2.0 |
| S1 / S3 / S4 | whole skill in the system prompt / in the message / written by the model | 0.709 / 0.652 / 0.677 | 76 / 76 / 71 | 14 / 14 / 7 | 2 / 2 / 0 | 1.0 |
| V | B0 + retry of an unusable reply, at most 2 | **0.785** | 77 | 7 | 3 | 1.1 |
| DTR | Deep Tax Research: 3 planned searches and 2 for gaps, A\* expansion, one answer | 0.722 | 71 | 6 | 1 | 3.0 |
| DTRa+V | the model picks its searches step by step, + retry | 0.823 | 77 | 3 | 0 | 4.4 |
| C | B1 + S2 + V, chosen on dev | 0.772 | 79 | 11 | 2 | 2.1 |

| Primary comparison | Difference [95% CI] | Wilcoxon p | Holm p | Questions better / worse |
|---|---|---|---|---|
| RQ1: S2 − B0 | −0.025 [−0.108, +0.057] | 0.622 | 1.000 | 9 / 14 |
| RQ2, retry: V − B0 | +0.038 [+0.006, +0.082] | 0.125 | 0.375 | 4 / 0 |
| RQ2, research: DTR − B0 | −0.025 [−0.120, +0.070] | 0.630 | 1.000 | 13 / 16 |

- **None of the three is significant after Holm.** The retry's interval excludes 0 only because just 4 questions
  differ. With 4, the exact test cannot go below p = 0.125.
- **The retry never lowered a question's score, but 2 of the refusals it retried became wrong answers.**
  - 3 of its 4 rescues came from a reply that ran out at the 2,000-token cap with no text; the 4th came from a
    reply that cited no source.
  - Replaying the recorded attempts with only empty replies sent back gives 0.778 on test and 0.775 on dev,
    against 0.747 and 0.738. That is why this PR always retries an empty reply.
- **The skill doesn't help here, though it does on legal drafting.**
  - On the legal project the focused skill raised drafting success from 0.067 to 0.219 (qwen2.5:7b, McNemar
    p = 0.004).
  - A likely reason, not tested: there the skill supplies checklists, approved ranges and routing rules, while
    here the answer has to come from the statute.
  - In an exploratory count (not pre-registered, uncorrected), both whole-skill variants answered 14 test
    questions wrongly against B0's 5.
- **Deep Tax Research didn't help:** −0.025 on test and −0.013 on dev, at 3 calls per question. It was removed
  from this PR.
- **DTRa+V scored highest, but treat it as a hypothesis.**
  - It was picked out of 13 conditions after the results were in.
  - Without the retry, the agent scored about the same as B0 (0.753). Against the retry alone, its lead is
    +0.038, not significant.
  - It would need new questions and gpt-oss-120b.

## What this PR takes from it

- **Deep Tax Search** toggle (off by default): `improved_astar`, falling back to `improved_astar_bm25` without
  embeddings.
  - It resolves more of what the hits depend on (0.71 against 0.50), with the same tokens and no extra model
    calls.
  - What it adds brings unresolved references of its own (26.0 left unresolved, against 19.9).
- **Retry** toggle (off by default): up to 2 retries of a reply that hit the cap, cites no source, or cites a
  number that isn't a source.
- **Default:** an empty reply is always sent back, at most twice.
- **Left out:** the reranker, contextual chunks, the abstention gate, the skill and Deep Tax Research.

## Not yet known

None of this ran on the app's own models. The next useful check, given a Groq key: one `improved` pass over the
79 test questions on gpt-oss-120b, counting replies that stop at the 2,000-token cap. That would show how much
the retry matters in the app.
