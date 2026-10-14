from pathlib import Path

import pytest

from rag.parse_guide import parse_guide_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample_guide.txt"


@pytest.fixture(scope="module")
def text():
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def paragraphs(text):
    return {p.number: p for p in parse_guide_text(text)}


def test_paragraphs_in_order_skipping_title_page_and_contents(text):
    assert [p.number for p in parse_guide_text(text)] == ["1.1", "2.1", "2.2", "3.1", "4.1", "Annex A"]


def test_paragraph_keeps_its_wrapped_lines_and_heading(paragraphs):
    assert paragraphs["1.1"].heading == "1 Aim"
    assert paragraphs["1.1"].text.endswith("Income Tax Act 1947 (“ITA”).")


def test_numbers_inside_text_and_tables_do_not_start_paragraphs(paragraphs):
    assert "11.1 of another guide." in paragraphs["2.2"].text
    assert "1 Same group Both companies are in the same group" in paragraphs["2.2"].text


def test_lost_heading_line_is_inferred_from_paragraph_number(paragraphs):
    assert paragraphs["3.1"].heading == "3"
    assert paragraphs["4.1"].heading == "4 Contact Information"


def test_annex_is_one_unit(paragraphs):
    annex = paragraphs["Annex A"]
    assert annex.heading == "Annex A – Worked example"
    assert annex.text.endswith("5.2 Not a paragraph: an annex is one unit.")


def test_char_spans_point_into_the_text(text, paragraphs):
    assert text[paragraphs["2.1"].char_start:].startswith("2.1 A company may claim")
