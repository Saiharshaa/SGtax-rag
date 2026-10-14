"""Phase 1b: data quality report -> results/data_quality.md + results/chunk_lengths.png.

    python scripts/build_chunks.py      # first
    python scripts/data_quality.py
"""

import json
import re
import statistics
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import matplotlib
import pymupdf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_chunks import ACT, GUIDE_MIN_FONT_SIZE, GUIDES  # noqa: E402
from rag.chunk import DELETED_RE, count_tokens  # noqa: E402
from rag.parse_act import act_body_span, parse_act_text  # noqa: E402
from rag.parse_guide import parse_guide_text  # noqa: E402
from rag.pdf_text import page_lines  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW, PROCESSED, RESULTS = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "results"

AMENDMENT_RE = re.compile(r"\[Act \d+ of \d{4} wef (\d{2}/\d{2}/\d{4})\]")
FORMULA_GLYPHS = "ðÞþ"
SHORT_CHUNK_TOKENS = 10

# Chart colours: validated categorical slots 1-2 (dataviz reference palette, light surface).
STRUCTURED_COLOUR, NAIVE_COLOUR = "#2a78d6", "#eb6834"
SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


def load_chunks(name: str) -> list[dict]:
    with (PROCESSED / f"chunks_{name}.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def processed_text(doc_id: str) -> str:
    return (PROCESSED / "text" / f"{doc_id}.txt").read_text(encoding="utf-8")


# ---------- 1. versions and dates ----------

def act_version() -> tuple[date, str]:
    with pymupdf.open(RAW / ACT["file"]) as doc:
        raw = doc[1].get_text()
    in_force = re.search(r"version in force from (\d{1,2}/\d{1,2}/\d{4})", raw).group(1)
    return datetime.strptime(in_force, "%d/%m/%Y").date(), "2020 Revised Edition"


def guide_version(doc_id: str) -> tuple[date, str]:
    text = processed_text(doc_id)
    published = re.search(r"Published on (\d{1,2} \w{3} \d{4})", text).group(1)
    edition = re.search(r"\((\w+) Edition\)", text, re.IGNORECASE)
    return datetime.strptime(published, "%d %b %Y").date(), (edition.group(1).title() if edition else "?")


def sections_amended_after(day: date) -> dict[str, list[str]]:
    """Act sections with an amendment note effective after `day` -> their effective dates."""
    text = processed_text(ACT["doc_id"])
    amended = {}
    for section in parse_act_text(text):
        dates = [datetime.strptime(d, "%d/%m/%Y").date()
                 for d in AMENDMENT_RE.findall(text[section.char_start:section.char_end])]
        later = sorted({d for d in dates if d > day})
        if later:
            amended[section.number] = [d.isoformat() for d in later]
    return amended


# ---------- 2. parse coverage ----------

def act_coverage() -> dict:
    text = processed_text(ACT["doc_id"])
    expected = re.findall(r"(?m)^(\d+[A-Z]{0,3})\.(?=[\s—–A-Z-])", text[:act_body_span(text)[0]])
    sections = parse_act_text(text)
    parsed = {s.number for s in sections}
    return {
        "expected": len(expected), "parsed": len(sections),
        "missing": [n for n in expected if n not in parsed],
        "extra": sorted(parsed - set(expected)),
        "repealed": [s.number for s in sections if s.repealed],
        "no_heading": [s.number for s in sections if not s.heading and not s.repealed],
        "renumbered": sum(bool(s.former_number) for s in sections),
        "deleted_subsections": sum(bool(DELETED_RE.match(sub.text)) for s in sections for sub in s.subsections),
        "formula_sections": [s.number for s in sections if any(g in s.text for g in FORMULA_GLYPHS)],
    }


def schedule_pages() -> tuple[int, int]:
    with pymupdf.open(RAW / ACT["file"]) as doc:
        first = next(p.number + 1 for p in reversed(doc)
                     if re.search(r"(?m)^\s*FIRST SCHEDULE\s*$", p.get_text()))
        return first, doc.page_count


def guide_coverage(guide: dict) -> dict:
    paragraphs = parse_guide_text(processed_text(guide["doc_id"]))
    headings = {p.heading for p in paragraphs if not p.heading.startswith("Annex")}
    with pymupdf.open(RAW / guide["file"]) as doc:
        all_lines = sum(len(page_lines(page)) for page in doc)
        kept_lines = sum(len(page_lines(page, GUIDE_MIN_FONT_SIZE)) for page in doc)
    return {
        "paragraphs": sum(not p.number.startswith("Annex") for p in paragraphs),
        "annexes": sum(p.number.startswith("Annex") for p in paragraphs),
        "headings": len(headings), "inferred_headings": sum(h.isdigit() for h in headings),
        "small_print_lines_dropped": all_lines - kept_lines,
    }


def chunk_stats(chunks: list[dict]) -> dict:
    tokens = [count_tokens(c["text"]) for c in chunks]
    ordered = sorted(tokens)
    return {
        "count": len(chunks), "empty": sum(t == 0 for t in tokens),
        "short": sum(0 < t < SHORT_CHUNK_TOKENS for t in tokens),
        "split": sum(c["split_total"] > 1 for c in chunks),
        "min": ordered[0], "median": statistics.median(ordered),
        "p95": ordered[int(0.95 * (len(ordered) - 1))], "max": ordered[-1], "tokens": tokens,
    }


# ---------- 3. cross-reference integrity ----------

def cross_ref_integrity(chunks: list[dict], parsed: set[str], repealed: set[str]) -> dict:
    refs = Counter()
    for chunk in chunks:
        source = "act" if chunk["doc_type"] == "act" else "guide"
        for number in chunk["cross_refs"]:
            refs[(source, number)] += 1
    total = sum(refs.values())
    unresolved = {k: n for k, n in refs.items() if k[1] not in parsed}
    to_repealed = {k: n for k, n in refs.items() if k[1] in repealed}
    return {"total": total, "resolved": total - sum(unresolved.values()),
            "unresolved": unresolved, "to_repealed": to_repealed}


# ---------- chart ----------

def plot_lengths(structured: list[int], naive: list[int], path: Path) -> None:
    bins = range(0, 525, 25)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharex=True, facecolor=SURFACE)
    panels = [(axes[0], structured, STRUCTURED_COLOUR, "Structure-aware chunks"),
              (axes[1], naive, NAIVE_COLOUR, "Naive 500-token chunks")]
    for ax, values, colour, title in panels:
        ax.set_facecolor(SURFACE)
        ax.hist(values, bins=bins, color=colour, edgecolor=SURFACE, linewidth=2)
        ax.set_title(f"{title} (n = {len(values):,}, median {statistics.median(values):.0f})",
                     loc="left", fontsize=11, color=TEXT_PRIMARY)
        ax.set_xlabel("Tokens per chunk", color=TEXT_SECONDARY)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=TEXT_SECONDARY, length=0)
    axes[0].set_ylabel("Chunks", color=TEXT_SECONDARY)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ---------- report ----------

def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    structured, naive = load_chunks("structured"), load_chunks("naive")

    act_date, act_edition = act_version()
    guides = [(g, *guide_version(g["doc_id"])) for g in GUIDES]
    oldest_guide = min(d for _, d, _ in guides)
    amended_later = sections_amended_after(oldest_guide)
    guide_cited = {n for c in structured if c["doc_type"] == "guide" for n in c["cross_refs"]}

    act = act_coverage()
    first_schedule_page, last_page = schedule_pages()
    sections = parse_act_text(processed_text(ACT["doc_id"]))
    parsed = {s.number for s in sections}
    repealed = {s.number for s in sections if s.repealed}
    former_numbers = {s.former_number: s.number for s in sections if s.former_number}
    integrity = cross_ref_integrity(structured, parsed, repealed)

    s_stats, n_stats = chunk_stats(structured), chunk_stats(naive)
    plot_lengths(s_stats["tokens"], n_stats["tokens"], RESULTS / "chunk_lengths.png")

    lines = ["# Data quality report", "",
             "Generated by `scripts/data_quality.py` from the files listed in `data/raw/SOURCES.md`.", "",
             "## 1. Document versions", "",
             "| Document | Edition | Date | vs Act version |", "|---|---|---|---|",
             f"| {ACT['title']} | {act_edition} | in force from {act_date:%d %b %Y} | - |"]
    for guide, published, edition in guides:
        gap = (act_date - published).days
        relation = f"pre-dates by {gap} days" if gap > 0 else f"post-dates by {-gap} days"
        lines.append(f"| {guide['short']} | {edition} | published {published:%d %b %Y} | {relation} |")
    later_cited = sorted(set(amended_later) & guide_cited)
    lines += ["",
              f"- All guides post-date the 2020 Revised Edition (operative 31 Dec 2021) and cite its section numbers.",
              f"- {len(amended_later)} Act sections carry amendments effective after {oldest_guide:%d %b %Y} "
              f"(the guides' publication date), so the guides may not reflect them: "
              + ", ".join(f"s {n} ({', '.join(d)})" for n, d in amended_later.items()) + ".",
              f"- Of those, cited by the guides: {', '.join('s ' + n for n in later_cited) or 'none'}.",
              "", "## 2. Parse coverage", "",
              f"- **Act sections:** {act['parsed']} parsed of {act['expected']} listed in the Arrangement of "
              f"Sections (missing: {', '.join(act['missing']) or 'none'}; extra: {', '.join(act['extra']) or 'none'}).",
              f"- **Repealed** (not indexed): {len(act['repealed'])} sections ({', '.join(act['repealed'])}), "
              f"plus {act['deleted_subsections']} deleted subsections (\"[Deleted by Act ...]\").",
              f"- **No heading found:** {', '.join('s ' + n for n in act['no_heading']) or 'none'}.",
              f"- **Renumbered in 2020:** {act['renumbered']} sections carry their pre-2020 number as metadata.",
              "", "| Guide | Numbered paragraphs | Annexes | Headings (inferred) | Footnote/small-print lines dropped (< 10 pt) |",
              "|---|---|---|---|---|"]
    for guide in GUIDES:
        cov = guide_coverage(guide)
        lines.append(f"| {guide['short']} | {cov['paragraphs']} | {cov['annexes']} | "
                     f"{cov['headings']} ({cov['inferred_headings']}) | {cov['small_print_lines_dropped']} |")
    lines += ["", "| Chunks | Count | Empty | < 10 tokens | Split (> 500 tokens) | Min | Median | P95 | Max |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name, stats in (("Structure-aware", s_stats), ("Naive", n_stats)):
        lines.append(f"| {name} | {stats['count']:,} | {stats['empty']} | {stats['short']} | {stats['split']} | "
                     f"{stats['min']} | {stats['median']:.0f} | {stats['p95']} | {stats['max']} |")
    lines += ["", "![Chunk length distribution](chunk_lengths.png)", "",
              "## 3. Cross-reference integrity", "",
              f"- {integrity['resolved']:,} of {integrity['total']:,} section references in chunks "
              f"({integrity['resolved'] / integrity['total']:.1%}) resolve to a parsed Act section."]
    unresolved = sorted(integrity["unresolved"].items(), key=lambda kv: -kv[1])
    if unresolved:
        lines.append("- Unresolved: " + ", ".join(f"s {n} ({src}, {c}×)" for (src, n), c in unresolved) + ".")
    if integrity["to_repealed"]:
        lines.append("- Point to repealed sections: " + ", ".join(
            f"s {n} ({src}, {c}×)" for (src, n), c in sorted(integrity["to_repealed"].items())) + ".")
    reused = sorted(n for n in guide_cited if n in former_numbers and former_numbers[n] != n)
    lines += [f"- {len(reused)} of the {len(guide_cited)} distinct section numbers the guides cite were used for a "
              "different provision before 2020 (e.g. s 14Q was renovation and refurbishment, now s 14N). The guides "
              "use 2020 numbering, so references resolve under it; the one explicit legacy citation is the renovation "
              "guide's \"unabsorbed S14Q (S14N of the 2020 Revised Edition)\".",
              "", "## 4. Known gaps and limitations", "",
              f"- **Schedules not indexed:** the 12 schedules (PDF pages {first_schedule_page}-{last_page}) are "
              "outside the parsed body.",
              f"- **Formulas:** symbol-font glyphs (ð, Þ, þ) extract as Latin letters in "
              f"{len(act['formula_sections'])} sections ({', '.join('s ' + n for n in act['formula_sections'])}); "
              "their formulas are unreadable in chunks.",
              "- **Guide footnotes and tables:** footnotes are dropped with other text under 10 pt; "
              "tables are flattened to lines, so cells lose their column.",
              "- **Residual spacing errors:** a few guide words run together (e.g. \"systemallows\" in Group "
              "Relief para 5.1); not measured.",
              "- **Outside the corpus:** subsidiary legislation (rules, regulations, orders), other e-Tax guides, "
              "IRAS web pages and case law. Questions on these must be answered \"not covered\".",
              "- **Guides are IRAS's interpretation, not law;** where a guide and the Act differ, the Act governs.",
              ""]
    (RESULTS / "data_quality.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", RESULTS / "data_quality.md", "and chunk_lengths.png")


if __name__ == "__main__":
    main()
