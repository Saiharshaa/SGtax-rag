from pathlib import Path

import pytest

from rag.parse_act import Subsection, parse_act_text, section_sort_key
from rag.refs import cited_sections

FIXTURE = Path(__file__).parent / "fixtures" / "sample_act.txt"


@pytest.fixture(scope="module")
def text():
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sections(text):
    return {section.number: section for section in parse_act_text(text)}


def test_every_section_parsed_once_in_order_skipping_contents_and_schedule(text):
    numbers = [section.number for section in parse_act_text(text)]
    assert numbers == ["1", "2", "3", "4", "4A", "5", "6"]


def test_headings_and_parts(sections):
    assert sections["1"].heading == "Short title"
    assert (sections["1"].part, sections["1"].part_title) == ("1", "PRELIMINARY")
    assert sections["4A"].heading == "Deduction for pre-commencement expenditure"
    assert (sections["4A"].part, sections["4A"].part_title) == ("2", "CHARGE OF TAX")


def test_subsections_keep_their_paragraphs(sections):
    group_relief = sections["6"]
    assert [sub.label for sub in group_relief.subsections] == ["1", "2"]
    assert "(a) both companies are incorporated in Singapore" in group_relief.subsections[0].text
    assert group_relief.subsections[1].text.startswith("For the purposes of subsection (1)(b)")


def test_section_without_subsections(sections):
    assert sections["1"].subsections == [Subsection(None, "This Act is the Sample Tax Act 2099.")]


def test_definitions_stay_in_interpretation_section(sections):
    assert "“company” means" in sections["2"].subsections[0].text


def test_repealed_section(sections):
    assert sections["5"].repealed
    assert sections["5"].heading == ""
    assert not sections["4"].repealed


def test_amendment_note_stays_with_its_section(sections):
    assert sections["4"].subsections[-1].text.endswith("[Act 5 of 2099 wef 01/01/2099]")


def test_char_spans_cover_heading_and_body(text, sections):
    span = text[sections["6"].char_start:sections["6"].char_end]
    assert span.startswith("Group relief\n6.—(1)")
    assert span.rstrip().endswith("ordinary shares of the other.")
    assert text[sections["5"].char_start:].startswith("5. [Repealed")


def test_schedule_is_not_parsed_as_sections(sections):
    assert not any("town council" in section.text for section in sections.values())


def test_numbered_line_inside_a_section_is_not_a_new_section():
    text = "Charge of tax\n3.—(1) Tax is payable on the income of\n2. companies listed below.\n"
    [section] = parse_act_text(text)
    assert section.text.endswith("2. companies listed below.")


def test_section_sort_key_orders_letter_suffixes():
    assert sorted(["5", "4ZA", "4", "4A", "10"], key=section_sort_key) == ["4", "4A", "4ZA", "5", "10"]


def test_cross_refs_from_parsed_text(sections):
    assert cited_sections(sections["4A"].text) == ["4"]
    assert cited_sections(sections["6"].text) == []   # only relative refs ("subsection (2)")
