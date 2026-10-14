"""Parse an IRAS e-Tax guide's text into numbered paragraphs (Phase 1).

Guides are laid out as numbered headings and paragraphs (1, 2, 2.1, 2.1.1), with
worked examples and annexes, and cite Act sections inline ("section 14(1) of the
ITA"). Each paragraph becomes one chunk in the shared schema (rag.schema.Chunk);
the Act sections it cites (rag.refs.cited_sections) become its cross_refs.
"""

from dataclasses import dataclass


@dataclass
class GuideParagraph:
    number: str        # "5.2"
    heading: str       # nearest heading above, e.g. "Conditions for group relief"
    text: str
    char_start: int = 0
    char_end: int = 0


def parse_guide_text(text: str) -> list[GuideParagraph]:
    """Split a guide's extracted text into numbered paragraphs, in document order."""
    raise NotImplementedError("Phase 1: needs the real etax_*.pdf files to fix the numbering patterns")
