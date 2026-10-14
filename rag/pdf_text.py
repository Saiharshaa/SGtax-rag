"""PDF -> normalised plain text, shared by the Act and e-Tax guide parsers.

What the source PDFs need (see docs/PLAN.md, "Document structure"):
- PyMuPDF with sort=True keeps word spacing (pypdf runs words together on these files).
- Running headers and footers sit in fixed bands at the top and bottom of every page.
- Pieces of one visual line can come out as separate lines ("1" and "Aim"), so lines at the
  same height are joined.
- Act section headings are bold and can wrap onto two lines; they are joined so the
  parser sees one heading line.
- Non-breaking hyphens (U+2011) become "-" so "pre-commencement" is searchable.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

HEADER_LIMIT = 60.0   # points from the top: running headers sit at y≈48-53, body text starts at y≥68
FOOTER_BAND = 0.92    # below 92% of the page height: footer / page number
SAME_LINE_TOLERANCE = 3.0   # points

_REPLACEMENTS = {"‑": "-", " ": " ", "­": ""}
_SECTION_START = re.compile(r"^\d+[A-Z]{0,3}\.")


@dataclass
class Line:
    text: str
    bold: bool
    size: float
    y: float
    x: float = 0.0


def extract_text(pdf_path: Path, min_font_size: float = 0.0, merge_headings: bool = False) -> str:
    """Return the document's text, one visual line per line, headers and footers removed.

    min_font_size drops smaller text (e.g. footnotes and disclaimers in the e-Tax guides).
    merge_headings joins consecutive bold heading lines (for the Act).
    """
    lines: list[Line] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            lines += page_lines(page, min_font_size)
    if merge_headings:
        lines = merge_wrapped_headings(lines)
    return normalise("\n".join(line.text for line in lines))


def page_lines(page: pymupdf.Page, min_font_size: float = 0.0) -> list[Line]:
    """Visual lines of one page, top to bottom, outside the header/footer bands."""
    top, bottom = HEADER_LIMIT, page.rect.height * FOOTER_BAND
    pieces = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        for raw in block.get("lines", []):
            # Superscripts are footnote markers ("activity1"); dropping them keeps words clean.
            all_spans = [span for span in raw["spans"] if not span["flags"] & pymupdf.TEXT_FONT_SUPERSCRIPT]
            spans = [span for span in all_spans if span["text"].strip()]
            if not spans:
                continue
            y, x = raw["bbox"][1], raw["bbox"][0]
            size = max(span["size"] for span in spans)
            if y < top or y > bottom or size < min_font_size:
                continue
            text = "".join(span["text"] for span in all_spans).strip()
            bold = all(span["flags"] & pymupdf.TEXT_FONT_BOLD for span in spans)
            pieces.append(Line(text, bold, size, y, x))
    return join_same_height(pieces)


def join_same_height(pieces: list[Line]) -> list[Line]:
    """Join pieces whose tops are within SAME_LINE_TOLERANCE into one line, left to right."""
    lines: list[list[Line]] = []
    for piece in sorted(pieces, key=lambda p: (p.y, p.x)):
        if lines and abs(piece.y - lines[-1][0].y) <= SAME_LINE_TOLERANCE:
            lines[-1].append(piece)
        else:
            lines.append([piece])
    joined = []
    for group in lines:
        group.sort(key=lambda p: p.x)
        joined.append(Line(" ".join(p.text for p in group), all(p.bold for p in group),
                           max(p.size for p in group), group[0].y, group[0].x))
    return joined


def merge_wrapped_headings(lines: list[Line]) -> list[Line]:
    """Join a bold heading that wraps onto a second bold line ("... first dollar of income" +
    "from trade, business, ...")."""
    merged: list[Line] = []
    for line in lines:
        if merged and _is_heading_line(merged[-1]) and _is_heading_line(line):
            previous = merged[-1]
            merged[-1] = Line(f"{previous.text} {line.text}", True, previous.size, previous.y, previous.x)
        else:
            merged.append(line)
    return merged


def _is_heading_line(line: Line) -> bool:
    # Part lines ("PART 3") and Part titles are upper case; section lines start with "10."
    return line.bold and not line.text.isupper() and not _SECTION_START.match(line.text)


def normalise(text: str) -> str:
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines())
