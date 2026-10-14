"""PDF -> plain text, shared by the Act and e-Tax guide parsers (Phase 1)."""

from pathlib import Path


def extract_text(pdf_path: Path) -> str:
    """Return the document's text, one line per visual line, with running page
    headers/footers removed.

    Written in Phase 1, after inspecting the real PDFs: the header/footer patterns
    (e.g. "Income Tax Act 1947 ... 2020 Ed.", page numbers, "Informal Consolidation"
    banners) can only be decided from the actual files.
    """
    raise NotImplementedError("Phase 1: needs the real PDFs in data/raw/")
