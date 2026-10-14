"""Parse an IRAS e-Tax guide's extracted text into numbered paragraphs.

Layout (verified against the five guides in data/raw/), after
rag.pdf_text.extract_text(min_font_size=10) has removed headers, footers and footnotes:

    Contents
    1 Aim ..........................          <- table of contents (dot leaders): skipped
    1 Aim                                     <- numbered heading; numbers go up by one
    1.1 This e-Tax Guide provides ...         <- numbered paragraph under heading 1
    2 At a glance
    2.1 ...
    Annex A – Examples illustrating ...       <- annexes: one unit each, after the numbered body

Each paragraph becomes one chunk (rag.chunk.guide_chunks). The Act sections it cites
become its cross_refs there.
"""

import re
from dataclasses import dataclass

DOT_LEADER_RE = re.compile(r"\.{5,}")
HEADING_RE = re.compile(r"^(\d{1,2})\s+([A-Z].{0,150})$")
PARAGRAPH_RE = re.compile(r"^(\d{1,2})\.(\d{1,2}(?:\.\d{1,2})?)\s+(.*)$")
ANNEX_RE = re.compile(r"^(Annex\s+[A-Z0-9]{1,2})\s*[–—-]\s*(.+)$")


@dataclass
class GuideParagraph:
    number: str        # "5.2"; the heading number ("5") for text before its first paragraph; "Annex A"
    heading: str       # "5 Group Relief System" or "Annex A – Examples ..."
    text: str
    char_start: int = 0
    char_end: int = 0


def parse_guide_text(text: str) -> list[GuideParagraph]:
    """Split a guide's extracted text into numbered paragraphs and annexes, in document order."""
    paragraphs: list[GuideParagraph] = []
    current: GuideParagraph | None = None
    lines: list[str] = []          # lines of the current paragraph
    heading_number = 0             # 0 until the body's first heading ("1 Aim") is seen
    heading = ""

    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line_start, offset = offset, offset + len(raw_line)
        line = raw_line.strip()
        if not line or DOT_LEADER_RE.search(line):
            continue

        annex = ANNEX_RE.match(line)
        heading_match = HEADING_RE.match(line)
        paragraph = PARAGRAPH_RE.match(line)

        if annex and heading_number:
            heading = f"{annex.group(1)} – {annex.group(2)}"
            number, first_line = annex.group(1), ""
        elif heading_match and _is_next_heading(heading_match, heading_number, line):
            heading_number = int(heading_match.group(1))
            heading = line
            number, first_line = str(heading_number), ""
        elif not heading_number:
            continue   # title page and contents
        elif paragraph and _is_body_paragraph(paragraph, heading_number, heading):
            if int(paragraph.group(1)) == heading_number + 1:   # heading line lost in extraction
                heading_number = int(paragraph.group(1))
                heading = str(heading_number)
            number, first_line = f"{paragraph.group(1)}.{paragraph.group(2)}", paragraph.group(3)
        else:
            lines.append(line)
            continue

        _finish(current, lines, end=line_start)
        current = GuideParagraph(number, heading, "", char_start=line_start)
        paragraphs.append(current)
        lines = [first_line] if first_line else []

    _finish(current, lines, end=len(text))
    return [p for p in paragraphs if p.text]


def _is_next_heading(match: re.Match, heading_number: int, line: str) -> bool:
    """Headings are numbered 1, 2, 3, ... and don't end like a sentence."""
    return int(match.group(1)) == heading_number + 1 and not line.endswith(".")


def _is_body_paragraph(match: re.Match, heading_number: int, heading: str) -> bool:
    """"5.2" belongs under heading 5; "6.1" also opens heading 6 if its heading line was lost."""
    return int(match.group(1)) in (heading_number, heading_number + 1) and not heading.startswith("Annex")


def _finish(paragraph: GuideParagraph | None, lines: list[str], end: int) -> None:
    if paragraph is not None:
        paragraph.text = "\n".join(lines)
        paragraph.char_end = end
