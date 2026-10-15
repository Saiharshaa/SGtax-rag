"""Phase 4: score retrieval against gold Act sections and guide paragraphs.

A question's gold units are Act sections ("14R") and guide paragraphs ("GR:5.1"), written as
(doc id, unit) pairs: ("ITA", "14R"), ("GR", "5.1"). A retrieved chunk hits a unit when

- it is an Act chunk of that section, or a guide chunk of that paragraph (structured chunks), or
- its character span overlaps the unit's span in the same document (naive chunks, which carry no
  labels; both chunkers ran over the same extracted text, so the spans are comparable).

Recall@k is the share of a question's gold units hit by the top k; MRR is the mean of 1/rank of
the first chunk that hits any gold unit (0 when none of the ranked chunks does).
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from rag.chunk import count_tokens
from rag.schema import Chunk

Unit = tuple[str, str]   # ("ITA", "14R") or ("GR", "5.1")


@dataclass
class Question:
    id: str
    question: str
    gold_sections: list[str] = field(default_factory=list)
    gold_paras: list[str] = field(default_factory=list)
    evidence: str = ""
    type: str = "natural"      # natural | section_ref | old_number | out_of_scope
    status: str = "DRAFT"

    @property
    def gold_units(self) -> set[Unit]:
        return {("ITA", s) for s in self.gold_sections} | {tuple(p.split(":", 1)) for p in self.gold_paras}

    @property
    def answerable(self) -> bool:
        return self.type != "out_of_scope"


def load_questions(path: Path) -> list[Question]:
    with path.open(encoding="utf-8") as f:
        return [Question(**json.loads(line)) for line in f if line.strip()]


def load_spans(path: Path) -> dict[str, dict[str, tuple[int, int]]]:
    """Gold-unit character spans per document, keyed like the chunk ids ("Annex 1" -> "Annex1")."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {doc: {unit.replace(" ", ""): tuple(span) for unit, span in units.items()} for doc, units in raw.items()}


def chunk_doc(chunk: Chunk) -> str:
    """Document id from the chunk id: "ITA:s14R(2)#1" -> "ITA", "naive:GR#0003" -> "GR"."""
    prefix, rest = chunk.chunk_id.split(":", 1)
    return rest.split("#")[0] if prefix == "naive" else prefix


def units_hit(chunk: Chunk, gold: set[Unit], spans: dict) -> set[Unit]:
    doc = chunk_doc(chunk)
    if chunk.doc_type == "act":
        return {unit for unit in gold if unit == (doc, chunk.section)}
    if chunk.doc_type == "guide":
        para = re.sub(r"#\d+$", "", chunk.chunk_id.split(":", 1)[1])
        return {unit for unit in gold if unit == (doc, para)}
    hit = set()
    for unit in gold:
        span = spans.get(unit[0], {}).get(unit[1]) if unit[0] == doc else None
        if span and chunk.char_start < span[1] and chunk.char_end > span[0]:
            hit.add(unit)
    return hit


def recall_at_k(ranked: list[Chunk], gold: set[Unit], spans: dict, k: int = 5) -> float:
    if not gold:
        return 0.0
    covered = set().union(*(units_hit(chunk, gold, spans) for chunk in ranked[:k])) if ranked else set()
    return len(covered) / len(gold)


def reciprocal_rank(ranked: list[Chunk], gold: set[Unit], spans: dict) -> float:
    for rank, chunk in enumerate(ranked, start=1):
        if units_hit(chunk, gold, spans):
            return 1.0 / rank
    return 0.0


def citation_precision(cited: list[Chunk], gold: set[Unit], spans: dict) -> float | None:
    """Share of an answer's citations that point at a gold unit; None when it cites nothing."""
    if not cited:
        return None
    return sum(bool(units_hit(chunk, gold, spans)) for chunk in cited) / len(cited)


def within_budget(ranked: list[Chunk], tokens: int) -> list[Chunk]:
    """The leading chunks whose texts fit in `tokens` (always at least one). Comparing configs at
    equal context size is fairer than top-k: five naive chunks hold several times the text of five
    structured ones."""
    kept, used = [], 0
    for chunk in ranked:
        used += count_tokens(chunk.text)
        if kept and used > tokens:
            break
        kept.append(chunk)
    return kept
