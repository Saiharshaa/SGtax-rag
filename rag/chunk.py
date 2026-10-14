"""Turn parsed documents into Chunks (Phase 1)."""

from rag.parse_act import Section
from rag.parse_guide import GuideParagraph
from rag.schema import Chunk


def act_chunks(sections: list[Section], act_title: str, source_file: str) -> list[Chunk]:
    """One chunk per subsection (one per section if it has no subsections).

    Overly long chunks are split, each piece keeping the parent path. cross_refs come
    from rag.refs.cited_sections on the chunk text.
    """
    raise NotImplementedError("Phase 1")


def guide_chunks(paragraphs: list[GuideParagraph], guide_title: str, source_file: str) -> list[Chunk]:
    """One chunk per numbered paragraph; Act sections cited in it become cross_refs."""
    raise NotImplementedError("Phase 1")


def naive_chunks(text: str, source_file: str, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Baseline: fixed windows of ~size tokens with overlap, no structure or metadata."""
    raise NotImplementedError("Phase 1")
