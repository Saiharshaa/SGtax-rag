"""Regression checks against the real PDFs; skipped when data/raw/ is empty."""

import re
from pathlib import Path

import pytest

from rag.chunk import act_chunks
from rag.parse_act import act_body_span, parse_act_text
from rag.parse_guide import parse_guide_text
from rag.pdf_text import extract_text

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
pytestmark = pytest.mark.skipif(not (RAW / "ITA_1947.pdf").exists(), reason="source PDFs not in data/raw/")


@pytest.fixture(scope="module")
def act_text():
    return extract_text(RAW / "ITA_1947.pdf", merge_headings=True)


def test_every_section_in_the_contents_is_parsed(act_text):
    contents = act_text[:act_body_span(act_text)[0]]
    expected = re.findall(r"(?m)^(\d+[A-Z]{0,3})\.(?=[\s—–A-Z-])", contents)
    parsed = [s.number for s in parse_act_text(act_text)]
    assert sorted(parsed) == sorted(expected)


def test_known_sections_and_former_numbers(act_text):
    sections = {s.number: s for s in parse_act_text(act_text)}
    assert sections["37B"].heading == "Group relief for Singapore companies"
    assert sections["14R"].heading.startswith("Deduction for expenses incurred before first dollar")
    assert (sections["14R"].former_number, sections["37B"].former_number) == ("14U", "37C")


@pytest.mark.parametrize("name, headings", [
    ("etax_group_relief.pdf", 20), ("etax_pre_commencement_expenses.pdf", 9),
    ("etax_date_of_commencement.pdf", 6), ("etax_carry_back_relief.pdf", 13),
    ("etax_renovation_refurbishment.pdf", 12),
])
def test_guide_headings_all_found(name, headings):
    paragraphs = parse_guide_text(extract_text(RAW / name, min_font_size=10))
    titled = {p.heading for p in paragraphs if not p.heading.startswith("Annex")}
    assert len(titled) == headings
    assert not any(h.isdigit() for h in titled)


def test_act_chunk_ids_are_unique(act_text):
    chunks = act_chunks(parse_act_text(act_text), "ITA", "Income Tax Act 1947", "ITA 1947", "ITA_1947.pdf")
    ids = [chunk.chunk_id for chunk in chunks]
    assert len(ids) == len(set(ids))
