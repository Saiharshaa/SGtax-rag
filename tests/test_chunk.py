from pathlib import Path

import pytest

from rag.chunk import (act_chunks, count_tokens, guide_chunks, naive_chunks, split_definitions,
                       split_text)
from rag.parse_act import parse_act_text
from rag.parse_guide import parse_guide_text

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def act():
    sections = parse_act_text((FIXTURES / "sample_act.txt").read_text(encoding="utf-8"))
    chunks = act_chunks(sections, "SAMPLE", "Sample Tax Act 2099", "STA 2099", "sample.pdf")
    return {c.chunk_id: c for c in chunks}


def test_count_tokens_counts_words_and_punctuation():
    assert count_tokens("s 14R(1) applies.") == 7


def test_split_text_respects_budget_and_keeps_every_line():
    text = "\n".join(f"line {i} has exactly seven tokens ." for i in range(12))
    pieces = split_text(text, max_tokens=20)
    assert all(count_tokens(piece) <= 20 for piece in pieces)
    assert "\n".join(pieces) == text


def test_split_definitions_one_unit_per_term():
    text = "In this Act —\n“company” means a body;\n“trade” includes\nmanufacture;"
    assert split_definitions(text) == [("", "In this Act —"), ("company", "“company” means a body;"),
                                       ("trade", "“trade” includes\nmanufacture;")]


def test_act_chunk_metadata(act):
    chunk = act["SAMPLE:s4A(1)#1"]
    assert chunk.cite == "STA 2099, s 4A(1)"
    assert chunk.path == "Sample Tax Act 2099 > Part 2 Charge of tax > s 4A(1)"
    assert chunk.heading == "Deduction for pre-commencement expenditure"
    assert chunk.cross_refs == ["4"]
    assert chunk.embed_text().startswith(chunk.path + "\n" + chunk.heading + "\n\n")


def test_definitions_get_their_own_chunks(act):
    company = act["SAMPLE:s2(1):company#1"]
    assert company.defined_term == "company"
    assert company.heading == "Interpretation: “company”"
    assert "SAMPLE:s2(1):year of assessment#1" in act


def test_repealed_sections_are_not_chunked_and_former_numbers_are_kept(act):
    assert not any(c.section == "5" for c in act.values())
    assert act["SAMPLE:s6(1)#1"].former_section == "7"


def test_guide_chunk_metadata():
    paragraphs = parse_guide_text((FIXTURES / "sample_guide.txt").read_text(encoding="utf-8"))
    chunks = {c.chunk_id: c for c in guide_chunks(paragraphs, "SG", "Sample guide", "Sample guide", "g.pdf")}
    chunk = chunks["SG:2.1#1"]
    assert chunk.cite == "Sample guide, para 2.1"
    assert chunk.path == "Sample guide > 2 Conditions > para 2.1"
    assert chunk.cross_refs == ["37B", "37C"]
    assert chunks["SG:AnnexA#1"].cite == "Sample guide, Annex A"


def test_naive_windows_overlap_and_point_into_the_text():
    text = " ".join(f"w{i}" for i in range(1200))
    chunks = naive_chunks(text, "D", "Doc", "d.pdf", size=500, overlap=50)
    assert len(chunks) == 3
    assert all(text[c.char_start:c.char_end] == c.text for c in chunks)
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert len(first) == 500 and first[-50:] == second[:50]
    assert chunks[-1].text.endswith("w1199")


def test_naive_respects_span_and_empty_text():
    text = "skip me " + "keep " * 10
    [chunk] = naive_chunks(text, "D", "Doc", "d.pdf", span=(8, len(text)))
    assert chunk.text.split() == ["keep"] * 10
    assert naive_chunks("", "D", "Doc", "d.pdf") == []
