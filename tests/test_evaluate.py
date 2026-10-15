import json

import pytest

from rag.evaluate import (Question, chunk_doc, citation_precision, load_spans, recall_at_k, reciprocal_rank,
                          units_hit)
from rag.retrieve import within_budget
from rag.schema import Chunk

SPANS = {"ITA": {"14R": (1000, 2000), "37B": (5000, 6000)}, "GR": {"5.1": (100, 300), "Annex1": (900, 950)}}


def act(section: str, subsection: str = "1") -> Chunk:
    return Chunk(f"ITA:s{section}({subsection})#1", "act", "Income Tax Act 1947", "ITA_1947.pdf", "...",
                 section=section, subsection=subsection)


def guide(para: str, split: int = 1) -> Chunk:
    return Chunk(f"GR:{para.replace(' ', '')}#{split}", "guide", "Group Relief", "gr.pdf", "...", para=para)


def naive(doc: str, start: int, end: int) -> Chunk:
    return Chunk(f"naive:{doc}#0001", "naive", doc, "x.pdf", "...", char_start=start, char_end=end)


GOLD = Question("q1", "?", gold_sections=["14R"], gold_paras=["GR:5.1"]).gold_units


def test_gold_units_and_answerability():
    assert GOLD == {("ITA", "14R"), ("GR", "5.1")}
    assert not Question("q2", "GST rate?", type="out_of_scope").answerable


def test_doc_ids_from_chunk_ids():
    assert [chunk_doc(c) for c in (act("14R"), guide("5.1"), naive("GR", 0, 1))] == ["ITA", "GR", "GR"]


def test_structured_chunks_hit_by_label():
    assert units_hit(act("14R", "2"), GOLD, SPANS) == {("ITA", "14R")}
    assert units_hit(act("14"), GOLD, SPANS) == set()
    assert units_hit(guide("5.1", split=2), GOLD, SPANS) == {("GR", "5.1")}
    assert units_hit(guide("5.10"), GOLD, SPANS) == set()


def test_naive_chunks_hit_by_span_overlap_in_the_same_document():
    assert units_hit(naive("ITA", 1900, 2600), GOLD, SPANS) == {("ITA", "14R")}
    assert units_hit(naive("ITA", 2000, 2600), GOLD, SPANS) == set()     # touching is not overlapping
    assert units_hit(naive("GR", 1900, 2600), GOLD, SPANS) == set()      # same offsets, other document
    assert units_hit(naive("GR", 0, 5000), GOLD, SPANS) == {("GR", "5.1")}


def test_recall_counts_gold_units_covered_by_the_top_k():
    ranked = [act("10"), act("14R"), act("14R", "2"), act("2"), act("3"), guide("5.1")]
    assert recall_at_k(ranked, GOLD, SPANS, k=5) == 0.5
    assert recall_at_k(ranked, GOLD, SPANS, k=6) == 1.0
    assert recall_at_k([], GOLD, SPANS) == 0.0


def test_reciprocal_rank_of_the_first_hit():
    assert reciprocal_rank([act("10"), act("2"), guide("5.1")], GOLD, SPANS) == pytest.approx(1 / 3)
    assert reciprocal_rank([act("10")], GOLD, SPANS) == 0.0


def test_citation_precision():
    assert citation_precision([act("14R"), act("10")], GOLD, SPANS) == 0.5
    assert citation_precision([], GOLD, SPANS) is None


def test_spans_are_keyed_like_chunk_ids(tmp_path):
    path = tmp_path / "spans.json"
    path.write_text(json.dumps({"GR": {"Annex 1": [900, 950]}}), encoding="utf-8")
    assert load_spans(path) == {"GR": {"Annex1": (900, 950)}}


def test_budget_keeps_leading_chunks_that_fit_and_at_least_one():
    short, long = Chunk("a#1", "act", "", "", "one two three"), Chunk("b#1", "act", "", "", "word " * 10)
    assert within_budget([short, short, long], tokens=6) == [short, short]
    assert within_budget([long, short], tokens=3) == [long]
