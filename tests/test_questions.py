"""eval/questions.jsonl stays consistent with the chunks: every gold label exists, and every evidence
quote appears word for word in one of its gold chunks. Skipped when the chunks haven't been built."""

import re
from pathlib import Path

import pytest

from rag.evaluate import load_questions, load_spans, units_hit
from rag.schema import load_chunks

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
QUESTIONS = load_questions(ROOT / "eval" / "questions.jsonl") if (ROOT / "eval" / "questions.jsonl").exists() else []
pytestmark = pytest.mark.skipif(not (PROCESSED / "chunks_structured.jsonl").exists() or not QUESTIONS,
                                reason="chunks or questions missing")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@pytest.fixture(scope="module")
def chunks():
    return load_chunks(PROCESSED / "chunks_structured.jsonl")


@pytest.fixture(scope="module")
def spans():
    return load_spans(PROCESSED / "spans.json")


def test_ids_are_unique_and_types_known():
    assert len({q.id for q in QUESTIONS}) == len(QUESTIONS)
    assert {q.type for q in QUESTIONS} <= {"natural", "section_ref", "old_number", "out_of_scope"}


def test_out_of_scope_questions_have_no_gold_and_the_rest_do():
    for q in QUESTIONS:
        assert bool(q.gold_units) == q.answerable, q.id


ANSWERABLE = [q for q in QUESTIONS if q.answerable]


@pytest.mark.parametrize("q", ANSWERABLE, ids=[q.id for q in ANSWERABLE])
def test_gold_units_exist_and_evidence_is_quoted_from_them(q, chunks, spans):
    gold_chunks = [chunk for chunk in chunks if units_hit(chunk, q.gold_units, spans)]
    found = set().union(*(units_hit(chunk, q.gold_units, spans) for chunk in gold_chunks))
    assert found == q.gold_units, f"no chunk for {q.gold_units - found}"
    assert any(squash(q.evidence) in squash(chunk.text) for chunk in gold_chunks), "evidence not in a gold chunk"
