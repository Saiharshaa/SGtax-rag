import pytest

from rag.refs import SectionRef, cited_sections, find_section_refs


def canonical(text):
    return [ref.canonical for ref in find_section_refs(text)]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("What does s 14 allow?", ["14"]),
        ("see s. 14", ["14"]),
        ("S14Q", ["14Q"]),
        ("is it covered by section 14q", ["14Q"]),
        ("sec 37A(2)(b)(ii)", ["37A(2)(b)(ii)"]),
        ("Section 10(1)(a) taxes gains or profits", ["10(1)(a)"]),
        ("section 13(1)(za)", ["13(1)(za)"]),
        ("section 10 (1)", ["10(1)"]),
        ("section 19(1a)", ["19(1A)"]),
        ("sections 14 and 14A", ["14", "14A"]),
        ("ss 14, 14A and 14B", ["14", "14A", "14B"]),
        ("sections 14 to 14B", ["14", "14B"]),
        ("(s 14) and (s 15)", ["14", "15"]),
    ],
)
def test_detects_explicit_references(text, expected):
    assert canonical(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "The company's 14 employees",
        "The company’s 14 employees",
        "It took 14 days",
        "Revenue of S$14,000 in YA 2024",
        "see paragraph 5.2 of the guide",
        "under subsection (2) and paragraph (a)",
        "Is 5 enough?",
    ],
)
def test_ignores_non_references(text):
    assert find_section_refs(text) == []


def test_query_reference_is_parsed_into_section_and_labels():
    refs = find_section_refs("Under section 10(1)(a), is a gain on sale of shares taxable?")
    assert refs == [SectionRef("10", ("1", "a"))]


def test_words_glued_on_by_extraction_are_not_suffixes():
    assert canonical("under section 43C, 43U, 43Vor 43X") == ["43C", "43U", "43V", "43X"]


@pytest.mark.parametrize("text", [
    "under section 153 of the Criminal Procedure Code 2010",
    "section 97V of the Economic Expansion Incentives (Relief from Income Tax) Act 1967",
    "the Companies Act 1967; see section 7 of that Act",
])
def test_references_to_other_legislation_are_external(text):
    assert all(ref.is_external for ref in find_section_refs(text))


def test_repeated_references_are_reported_once():
    assert canonical("s 14 applies; see also s 14 and s 14(2)") == ["14", "14(2)"]


def test_reference_to_another_act_is_external():
    [ref] = find_section_refs("as defined in section 4 of the Goods and Services Tax Act 1993")
    assert ref.act == "Goods and Services Tax Act 1993"
    assert ref.is_external


@pytest.mark.parametrize(
    "text",
    [
        "section 14 of the Act",
        "section 14 of the Income Tax Act 1947",
        "section 14 of the ITA",
        "section 14 of this Act",
    ],
)
def test_reference_to_this_act_is_internal(text):
    [ref] = find_section_refs(text)
    assert not ref.is_external


def test_cited_sections_keeps_section_numbers_only():
    text = "Despite section 4(1) and section 4A, and section 9 of the Companies Act 1967"
    assert cited_sections(text) == ["4", "4A"]
    assert cited_sections(text, include_external=True) == ["4", "4A", "9"]
