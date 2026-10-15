"""Parse an Act's extracted text into Part > section > subsection.

Layout of the Singapore Statutes Online 2020 Revised Edition, as extracted by
rag.pdf_text.extract_text(merge_headings=True) (verified against ITA_1947.pdf):

    ARRANGEMENT OF SECTIONS ...        <- table of contents: skipped
    An Act to impose a tax upon ...    <- long title: the body starts here
    PART 3                             <- Part number line
    IMPOSITION OF INCOME TAX           <- Part title line
    Charge of income tax               <- section heading (wrapped headings already joined)
    10.—(1) Income tax is ...          <- section number; may open subsection (1)
    (2) ...                            <- further subsections start a line
    [Act 33 of 2022 wef 26/04/2024]    <- amendment note: kept in the text
    [10B                               <- the section's pre-2020 number: kept as metadata
    FIRST SCHEDULE                     <- the body ends at the first schedule

Paragraphs such as (a) and (b) stay inside their subsection's text.
"""

import re
from dataclasses import dataclass, field

LONG_TITLE_RE = re.compile(r"(?m)^An Act to\b")
SCHEDULE_RE = re.compile(r"(?m)^(?:[A-Z]+\s+)?SCHEDULE$")
PART_RE = re.compile(r"^PART\s+(\d+[A-Z]?|[IVXLC]+[A-Z]?)$")
SECTION_RE = re.compile(r"^(\d+[A-Z]{0,3})\.(?:\s+|[—–-]+\s*)(.*)$")
SUBSECTION_RE = re.compile(r"^\((\d+[A-Z]{0,2})\)\s*(.*)$")
FORMER_NUMBER_RE = re.compile(r"^\[(\d+[A-Z]{0,3})$")
REPEALED_RE = re.compile(r"^\[Repealed\b", re.IGNORECASE)


@dataclass
class Subsection:
    label: str | None   # "1", "1A"; None when the section has no numbered subsections
    text: str


@dataclass
class Section:
    number: str          # "14Q"
    heading: str         # "" when no heading line was found (e.g. repealed sections)
    part: str            # "3"
    part_title: str      # "IMPOSITION OF INCOME TAX"
    subsections: list[Subsection] = field(default_factory=list)
    repealed: bool = False
    former_number: str = ""   # number before the 2020 Revised Edition, e.g. "14U"
    char_start: int = 0       # span of heading + body in the input text
    char_end: int = 0

    @property
    def text(self) -> str:
        return "\n".join(sub.text for sub in self.subsections)


def section_sort_key(number: str) -> tuple[int, str]:
    """"4" < "4A" < "4ZA" < "5"."""
    digits, suffix = re.match(r"(\d+)([A-Z]*)", number).groups()
    return int(digits), suffix


def act_body_span(text: str) -> tuple[int, int]:
    """Character span of the enacted sections: from the long title to the first schedule.

    Without a long title (e.g. a bare excerpt) the body starts at 0.
    """
    long_title = LONG_TITLE_RE.search(text)
    start = long_title.start() if long_title else 0
    schedule = SCHEDULE_RE.search(text, start)
    return start, schedule.start() if schedule else len(text)


def parse_act_text(text: str) -> list[Section]:
    """Return the Act's sections in order. The table of contents and schedules are skipped."""
    body_start, body_end = act_body_span(text)
    sections: list[Section] = []
    current: Section | None = None
    body: list[tuple[int, str]] = []   # (char offset, line) read since the last section/Part line
    part = part_title = ""
    awaiting_part_title = False

    offset = body_start
    for raw_line in text[body_start:body_end].splitlines(keepends=True):
        line_start, offset = offset, offset + len(raw_line)
        line = raw_line.strip()
        if not line:
            continue

        part_match = PART_RE.match(line)
        if part_match:
            _finish(current, body, end=line_start)
            current, body = None, []
            part, awaiting_part_title = part_match.group(1), True
            continue
        if awaiting_part_title:
            part_title, awaiting_part_title = line, False
            continue

        former = FORMER_NUMBER_RE.match(line)
        if former and current:
            current.former_number = former.group(1)
            continue

        section_match = SECTION_RE.match(line)
        if section_match and _is_next_section(section_match.group(1), sections):
            number, rest = section_match.groups()
            heading_start, heading = _pop_heading(body, default_start=line_start)
            _finish(current, body, end=heading_start)
            current = Section(number, heading, part, part_title,
                              repealed=bool(REPEALED_RE.match(rest)), char_start=heading_start)
            sections.append(current)
            body = [(line_start, rest)] if rest else []
            continue

        body.append((line_start, line))

    _finish(current, body, end=body_end)
    return sections


def _is_next_section(number: str, sections: list[Section]) -> bool:
    """A new section's number is unseen and its numeric part doesn't go down, so "2. companies ..."
    inside s 3's text is not a new section. (Letter suffixes can go down: 93AA precedes 93A.)"""
    if not sections:
        return True
    if any(section.number == number for section in sections):
        return False
    return section_sort_key(number)[0] >= section_sort_key(sections[-1].number)[0]


def _looks_like_heading(line: str) -> bool:
    """Headings are short, capitalised, and don't end like a sentence ("...notices, etc." is fine)."""
    ends_like_sentence = line[-1] in ".;:—–-" and not line.endswith("etc.")
    return len(line) <= 200 and line[0].isupper() and not ends_like_sentence


def _pop_heading(body: list[tuple[int, str]], default_start: int) -> tuple[int, str]:
    """A section's heading is the line just above its number; take it off the previous body."""
    if body and _looks_like_heading(body[-1][1]):
        return body.pop()
    return default_start, ""


def _finish(section: Section | None, body: list[tuple[int, str]], end: int) -> None:
    if section is None:
        return
    section.subsections = _split_subsections([line for _, line in body])
    section.char_end = end


def _starts_subsection(match: re.Match | None, seen: set[str | None]) -> bool:
    """A "(2A) ..." line opens a subsection only if its text starts like a sentence and the label is new.
    Cross-references wrap onto line starts too ("... under subsections (1),\n(1AA) and (2C).") and
    continue with ",", "and", "or", "(b)" or lower case; ~100 such lines in the ITA."""
    if not match or match.group(1) in seen:
        return False
    rest = match.group(2)
    return not rest or rest[0].isupper() or rest[0] in "[“\""


def _split_subsections(lines: list[str]) -> list[Subsection]:
    groups: list[tuple[str | None, list[str]]] = []
    for line in lines:
        match = SUBSECTION_RE.match(line)
        if _starts_subsection(match, {label for label, _ in groups}):
            groups.append((match.group(1), [match.group(2)] if match.group(2) else []))
        elif groups:
            groups[-1][1].append(line)
        else:
            groups.append((None, [line]))
    return [Subsection(label, "\n".join(group_lines)) for label, group_lines in groups]
