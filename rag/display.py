"""Text helpers for showing answers and sources in the app."""

import re

EXCERPT_CHARS = 600   # sources are shown as short excerpts, never whole documents (IRAS copyright notice)

RETRIEVAL_LABELS = {
    "improved": "structure-aware chunks, BM25 + Gemini embeddings, section boost",
    "improved_bm25": "structure-aware chunks, BM25 + section boost (embeddings unavailable)",
    "baseline": "naive 500-token chunks, Gemini embeddings",
    "naive_bm25": "naive 500-token chunks, BM25 (embeddings unavailable)",
}


def markdown_safe(text: str) -> str:
    """Escape dollar signs: Streamlit renders "$150,000 ... $300,000" as LaTeX otherwise."""
    return text.replace("$", r"\$")


def excerpt(text: str, chars: int = EXCERPT_CHARS) -> str:
    """The first `chars` characters, cut at a word boundary, with line breaks flattened."""
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= chars:
        return flat
    return flat[:chars].rsplit(" ", 1)[0] + " …"
