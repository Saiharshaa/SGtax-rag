"""Phase 4: evaluate retrieval configs, and a sample of generated answers, on eval/questions.jsonl.

    python scripts/evaluate.py                    # retrieval -> results/metrics.md, results/comparison.png
    python scripts/evaluate.py --answers 10       # also answer 10 questions (+ the out-of-scope ones) per
                                                  # answer config -> summary in metrics.md, answers.md
    python scripts/evaluate.py --answers 10 --answer-configs structured_bm25_boost naive_bm25

Configs whose dense index is incomplete are reported as pending; rerun once build_index.py finishes.
Query embeddings are cached in index/query_embeddings.json, so reruns don't spend embedding quota.
"""

import argparse
import statistics
import sys
import time
from datetime import date
from pathlib import Path

import matplotlib
from dotenv import load_dotenv

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunk import NAIVE_SIZE  # noqa: E402
from rag.embed import CachedEmbedder, GeminiEmbedder, MissingApiKey, QuotaExhausted  # noqa: E402
from rag.evaluate import (citation_precision, load_questions, load_spans, recall_at_k,  # noqa: E402
                          reciprocal_rank)
from rag.generate import CONTEXT_TOKENS, answer  # noqa: E402
from rag.llm import LLMUnavailable, default_models  # noqa: E402
from rag.retrieve import CONFIGS, IncompleteIndex, Retriever, within_budget  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS, SPANS = ROOT / "eval" / "questions.jsonl", ROOT / "data" / "processed" / "spans.json"
RESULTS, INDEX = ROOT / "results", ROOT / "index"

# Rows of the results table, in ablation order: each adds one thing to the row above it.
ROWS = ["naive_bm25", "naive_dense", "structured_bm25", "structured_bm25_boost", "structured_dense",
        "structured_hybrid", "structured_hybrid_boost"]
K, MRR_DEPTH, FETCH = 5, 10, 40
BUDGET = CONTEXT_TOKENS          # tokens in five naive chunks: the equal-context comparison
QUESTION_TYPES = ["natural", "section_ref", "old_number"]

SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
CORPUS_COLOUR = {"structured": "#2a78d6", "naive": "#eb6834"}   # same as results/chunk_lengths.png


def score_config(retriever: Retriever, config: str, questions: list, spans: dict) -> list[dict]:
    rows = []
    for q in questions:
        ranked = [hit.chunk for hit in retriever.search(q.question, config, FETCH).hits]
        gold = q.gold_units
        rows.append({"id": q.id, "type": q.type, "recall": recall_at_k(ranked, gold, spans, K),
                     "rr": reciprocal_rank(ranked[:MRR_DEPTH], gold, spans),
                     "budget": recall_at_k(within_budget(ranked, BUDGET), gold, spans, k=len(ranked))})
    return rows


def mean(rows: list[dict], key: str) -> float:
    return statistics.fmean(row[key] for row in rows) if rows else float("nan")


def metrics_table(scores: dict[str, list[dict]]) -> list[str]:
    lines = ["| Config | Corpus | Retrieval | Recall@5 | MRR@10 | Recall @ 2,500 tokens |", "|---|---|---|---|---|---|"]
    for config, rows in scores.items():
        cfg = CONFIGS[config]
        method = " + ".join(name for name, on in (("BM25", cfg.bm25), ("dense", cfg.dense),
                                                   ("section boost", cfg.section_boost)) if on)
        lines.append(f"| `{config}` | {cfg.corpus} | {method} | {mean(rows, 'recall'):.2f} | {mean(rows, 'rr'):.2f} "
                     f"| {mean(rows, 'budget'):.2f} |")
    return lines


def type_table(scores: dict[str, list[dict]]) -> list[str]:
    counts = {t: sum(r["type"] == t for r in next(iter(scores.values()))) for t in QUESTION_TYPES}
    header = " | ".join(f"{t} (n={counts[t]})" for t in QUESTION_TYPES)
    lines = [f"| Config | {header} |", "|---|" + "---|" * len(QUESTION_TYPES)]
    for config, rows in scores.items():
        cells = " | ".join(f"{mean([r for r in rows if r['type'] == t], 'recall'):.2f}" for t in QUESTION_TYPES)
        lines.append(f"| `{config}` | {cells} |")
    return lines


def plot(scores: dict[str, list[dict]], path: Path) -> None:
    configs = list(scores)[::-1]   # first row on top
    panels = [("recall", "Recall@5"), ("rr", "MRR@10"), ("budget", "Recall @ 2,500 tokens")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 0.45 * len(configs) + 1.4), sharey=True, facecolor=SURFACE)
    for ax, (key, title) in zip(axes, panels):
        values = [mean(scores[c], key) for c in configs]
        ax.set_facecolor(SURFACE)
        ax.barh(configs, values, height=0.6, color=[CORPUS_COLOUR[CONFIGS[c].corpus] for c in configs])
        for y, value in enumerate(values):
            ax.text(value + 0.02, y, f"{value:.2f}", va="center", fontsize=9, color=TEXT_PRIMARY)
        ax.set_xlim(0, 1.12)
        ax.set_title(title, loc="left", fontsize=11, color=TEXT_PRIMARY)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=TEXT_SECONDARY, length=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colour) for colour in CORPUS_COLOUR.values()]
    fig.legend(handles, ["structure-aware chunks", "naive 500-token chunks"], loc="lower center", ncol=2,
               frameon=False, labelcolor=TEXT_SECONDARY, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def run_answers(retriever: Retriever, configs: list[str], questions: list, n: int,
                spans: dict) -> tuple[list[str], list[str]]:
    """Answer the first n answerable questions and every out-of-scope one; report citations and refusals."""
    sample = [q for q in questions if q.answerable][:n] + [q for q in questions if not q.answerable]
    models = default_models()
    summary = ["| Config | Answered | Refused (answerable) | Citation precision | Out-of-scope refused |",
               "|---|---|---|---|---|"]
    detail = []
    for config in configs:
        results = []
        for q in sample:
            try:
                results.append((q, answer(q.question, retriever, models, config)))
            except LLMUnavailable as error:
                results.append((q, error))
        answerable = [(q, r) for q, r in results if q.answerable and not isinstance(r, Exception)]
        precisions = [p for q, r in answerable if (p := citation_precision(r.cited, q.gold_units, spans)) is not None]
        out = [(q, r) for q, r in results if not q.answerable and not isinstance(r, Exception)]
        summary.append(f"| `{config}` | {sum(not r.refused for _, r in answerable)}/{len(answerable)} "
                       f"| {sum(r.refused for _, r in answerable)} "
                       f"| {statistics.fmean(precisions):.2f} (over {len(precisions)}) "
                       f"| {sum(r.refused for _, r in out)}/{len(out)} |")
        detail.append(f"\n## `{config}`\n")
        for q, r in results:
            gold = ", ".join(q.gold_sections + q.gold_paras) or "none (out of scope)"
            detail.append(f"### {q.id}: {q.question}\n\nGold: {gold}\n")
            if isinstance(r, Exception):
                detail.append(f"Error: {r}\n")
                continue
            precision = citation_precision(r.cited, q.gold_units, spans)
            detail.append(f"{r.text}\n\n*{r.model or 'no model'}; citation precision "
                          f"{'n/a' if precision is None else f'{precision:.2f}'}"
                          f"{'; dropped citations ' + str(r.invalid_citations) if r.invalid_citations else ''}*\n")
    return summary, detail


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--answers", type=int, default=0, help="answer this many questions per answer config")
    parser.add_argument("--answer-configs", nargs="+", default=["improved", "baseline"], choices=sorted(CONFIGS))
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    questions, spans = load_questions(QUESTIONS), load_spans(SPANS)
    answerable = [q for q in questions if q.answerable]
    try:
        embedder = CachedEmbedder(GeminiEmbedder(), INDEX / "query_embeddings.json")
    except MissingApiKey:
        embedder = None
    retriever = Retriever(INDEX, embedder)

    scores, pending = {}, {}
    for config in ROWS:
        try:
            scores[config] = score_config(retriever, config, answerable, spans)
            print(f"{config}: Recall@5 {mean(scores[config], 'recall'):.2f}  MRR@10 {mean(scores[config], 'rr'):.2f}")
        except (IncompleteIndex, MissingApiKey, QuotaExhausted) as error:
            pending[config] = str(error)
            print(f"{config}: pending ({pending[config]})")

    status = "DRAFT (not yet reviewed)" if any(q.status == "DRAFT" for q in questions) else "reviewed"
    lines = [
        "# Retrieval evaluation", "",
        f"Generated by `scripts/evaluate.py` on {date.today().isoformat()} from `eval/questions.jsonl`: "
        f"{len(questions)} questions, {len(answerable)} with gold labels, {len(questions) - len(answerable)} "
        f"out of scope. Question set status: **{status}**.", "",
        *metrics_table(scores), "",
        "![Retrieval comparison](comparison.png)", "",
    ]
    if pending:
        lines += ["**Pending** (rerun when the dense index is complete):", ""]
        lines += [f"- `{config}`: {reason}" for config, reason in pending.items()] + [""]
    lines += ["## Recall@5 by question type", "", *type_table(scores), "",
              "## How to read this", "",
              "- A chunk is relevant when it belongs to a gold Act section or guide paragraph; naive chunks, which "
              "have no labels, count when their character span overlaps a gold unit's span.",
              "- Recall@5 is the share of a question's gold units found in the top 5; MRR@10 is the mean of 1/rank of "
              "the first relevant chunk.",
              f"- Top-5 is not equal context: a naive chunk is {NAIVE_SIZE} tokens, a structured one ~80 (median). "
              f"Recall @ 2,500 tokens takes chunks in rank order until {BUDGET:,} tokens, the size of five naive "
              "chunks, so both chunkers get the same amount of text."]
    if args.answers:
        started = time.monotonic()
        summary, detail = run_answers(retriever, args.answer_configs, questions, args.answers, spans)
        lines += ["", "## Generated answers", "",
                  f"The first {args.answers} questions with gold labels plus every out-of-scope one, per config. "
                  "Citation precision is the share of an answer's citations that point at a gold unit; "
                  "the answers themselves are in [`answers.md`](answers.md) for manual review.", "", *summary]
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / "answers.md").write_text("# Generated answers\n" + "\n".join(detail) + "\n", encoding="utf-8")
        print(f"answers: {time.monotonic() - started:.0f} s")

    RESULTS.mkdir(exist_ok=True)
    if scores:
        plot(scores, RESULTS / "comparison.png")
    (RESULTS / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS / 'metrics.md'}")


if __name__ == "__main__":
    main()
