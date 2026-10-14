"""Parse an Act's extracted text into Part > section > subsection.

parse_act_text() works on plain text and is tested against tests/fixtures/sample_act.txt,
a synthetic Act laid out the way we ASSUME the Singapore Statutes Online revised
edition looks once extracted (to be checked against the real ITA_1947.pdf in Phase 1):

    ARRANGEMENT OF SECTIONS            <- table of contents; repeats "PART n" and "n. Heading"
    ...
    PART 3                             <- Part number line
    IMPOSITION OF INCOME TAX           <- Part title line
    Charge of income tax               <- section heading, on its own line above the number
    10.—(1) Income tax is payable ...  <- section number; may open subsection (1)
    (2) ...                            <- further subsections start a line
    FIRST SCHEDULE                     <- schedules follow the sections; skipped for now

Paragraphs such as (a) and (b) stay inside their subsection's text.
"""

import re
from dataclasses import dataclass, field

PART_RE = re.compile(r"^PART\s+(\d+[A-Z]?|[IVXLC]+[A-Z]?)$")
SECTION_RE = re.compile(r"^(\d+[A-Z]{0,3})\.(?:\s+|[—–-]+\s*)(.*)$")
SUBSECTION_RE = re.compile(r"^\((\d+[A-Z]{0,2})\)\s*(.*)$")
SCHEDULE_RE = re.compile(r"^(?:[A-Z]+\s+)?SCHEDULE\b")
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
    char_start: int = 0  # span of heading + body in the input text
    char_end: int = 0

    @property
    def text(self) -> str:
        return "\n".join(sub.text for sub in self.subsections)


def section_sort_key(number: str) -> tuple[int, str]:
    """"4" < "4A" < "4ZA" < "5"."""
    digits, suffix = re.match(r"(\d+)([A-Z]*)", number).groups()
    return int(digits), suffix


def parse_act_text(text: str) -> list[Section]:
    """Return the Act's sections in order. The table of contents and schedules are skipped."""
    sections: list[Section] = []
    current: Section | None = None
    body: list[tuple[int, str]] = []   # (char offset, line) read since the last section/Part line
    part = part_title = ""
    awaiting_part_title = in_schedule = False

    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line_start, offset = offset, offset + len(raw_line)
        line = raw_line.strip()
        if not line:
            continue

        part_match = PART_RE.match(line)
        if part_match:
            _finish(current, body, end=line_start)
            current, body = None, []
            part, awaiting_part_title, in_schedule = part_match.group(1), True, False
            continue
        if in_schedule:
            continue
        if SCHEDULE_RE.match(line):
            _finish(current, body, end=line_start)
            current, body, in_schedule = None, [], True
            continue
        if awaiting_part_title:
            part_title, awaiting_part_title = line, False
            continue

        section_match = SECTION_RE.match(line)
        if section_match and _is_next_section(section_match.group(1), sections):
            number, rest = section_match.groups()
            heading_start, heading = _pop_heading(body, default_start=line_start)
            _finish(current, body, end=heading_start)
            if number == "1":
                sections.clear()   # a second "section 1": everything so far was the table of contents
            current = Section(number, heading, part, part_title,
                              repealed=bool(REPEALED_RE.match(rest)), char_start=heading_start)
            sections.append(current)
            body = [(line_start, rest)] if rest else []
            continue

        body.append((line_start, line))

    _finish(current, body, end=len(text))
    return sections


def _is_next_section(number: str, sections: list[Section]) -> bool:
    """Section numbers only go up, so "2. companies ..." inside s 3's text is not a new section."""
    if number == "1" or not sections:
        return True
    return section_sort_key(number) > section_sort_key(sections[-1].number)


def _looks_like_heading(line: str) -> bool:
    return len(line) <= 120 and line[0].isupper() and line[-1] not in ".;:,—–-"


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


def _split_subsections(lines: list[str]) -> list[Subsection]:
    groups: list[tuple[str | None, list[str]]] = []
    for line in lines:
        match = SUBSECTION_RE.match(line)
        if match:
            groups.append((match.group(1), [match.group(2)] if match.group(2) else []))
        elif groups:
            groups[-1][1].append(line)
        else:
            groups.append((None, [line]))
    return [Subsection(label, "\n".join(group_lines)) for label, group_lines in groups]
