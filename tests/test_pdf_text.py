from rag.pdf_text import Line, join_same_height, merge_wrapped_headings, normalise


def test_normalise_replaces_non_breaking_hyphens_and_spaces():
    assert normalise("pre‑commencement   expenses \n  next") == "pre-commencement expenses\nnext"


def test_pieces_at_the_same_height_become_one_line():
    pieces = [Line("Aim", True, 12, y=122.4, x=100), Line("1", True, 12, y=122.0, x=77),
              Line("1.1 This guide", False, 12, y=150.0, x=77)]
    assert [line.text for line in join_same_height(pieces)] == ["1 Aim", "1.1 This guide"]


def test_wrapped_bold_heading_is_joined():
    lines = [Line("Deduction for expenses incurred before first dollar of income", True, 13, 1),
             Line("from trade, business, profession or vocation", True, 13, 2),
             Line("14R.—(1) Subject to section 14X, a person who —", False, 13, 3)]
    assert [line.text for line in merge_wrapped_headings(lines)] == [
        "Deduction for expenses incurred before first dollar of income from trade, business, profession or vocation",
        "14R.—(1) Subject to section 14X, a person who —",
    ]


def test_part_lines_and_titles_are_not_joined_to_headings():
    lines = [Line("PART 3", True, 13, 1), Line("IMPOSITION OF INCOME TAX", True, 13, 2),
             Line("Charge of income tax", True, 13, 3)]
    assert len(merge_wrapped_headings(lines)) == 3
