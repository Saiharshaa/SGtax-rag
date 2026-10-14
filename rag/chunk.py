"""Turn parsed documents into Chunks: structure-aware (Act, guides) and the naive baseline.

Token counts use a regex (words and punctuation marks) rather than a model tokenizer:
no extra dependency, and the same measure is used for both chunkers.
"""

import re

from rag.parse_act import Section
from rag.parse_guide import GuideParagraph
from rag.refs import cited_sections
from rag.schema import Chunk

MAX_TOKENS = 500          # cap for structured chunks, equal to the naive window
NAIVE_SIZE, NAIVE_OVERLAP = 500, 50

TOKEN_RE = re.compile(r"\w+|[^\w\s]")
DEFINITION_RE = re.compile(r"^“([^”]{1,80})”")


def count_tokens(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def split_text(text: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    """Split at line boundaries into pieces of at most max_tokens (a longer single line stays whole)."""
    pieces: list[list[str]] = [[]]
    size = 0
    for line in text.splitlines():
        line_tokens = count_tokens(line)
        if pieces[-1] and size + line_tokens > max_tokens:
            pieces.append([])
            size = 0
        pieces[-1].append(line)
        size += line_tokens
    return ["\n".join(piece) for piece in pieces if piece]


def split_definitions(text: str) -> list[tuple[str, str]]:
    """Split an Interpretation subsection into (term, text) pairs, one per “defined term”.
    Lines before the first definition ("In this Act, unless ...") form a pair with term ""."""
    groups: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        match = DEFINITION_RE.match(line)
        if match or not groups:
            groups.append((match.group(1) if match else "", [line]))
        else:
            groups[-1][1].append(line)
    return [(term, "\n".join(lines)) for term, lines in groups]


def act_chunks(sections: list[Section], doc_id: str, act_title: str, short_title: str,
               source_file: str) -> list[Chunk]:
    """One chunk per subsection (per section if it has none, per defined term in s 2(1)).

    Repealed sections are skipped. Chunks over MAX_TOKENS are split, each piece keeping the path.
    """
    chunks = []
    for section in sections:
        if section.repealed:
            continue
        for sub in section.subsections:
            label = sub.label or ""
            if section.number == "2" and label == "1":
                units = split_definitions(sub.text)
            else:
                units = [("", sub.text)]
            for term, unit_text in units:
                chunks += _act_unit_chunks(section, label, term, unit_text, doc_id, act_title,
                                           short_title, source_file)
    return chunks


def _act_unit_chunks(section: Section, label: str, term: str, text: str, doc_id: str,
                     act_title: str, short_title: str, source_file: str) -> list[Chunk]:
    ref = section.number + (f"({label})" if label else "")
    path = f"{act_title} > Part {section.part} {section.part_title.capitalize()} > s {ref}"
    heading = f"{section.heading}: “{term}”" if term else section.heading
    pieces = split_text(text)
    return [
        Chunk(
            chunk_id=f"{doc_id}:s{ref}" + (f":{term}" if term else "") + f"#{k}",
            doc_type="act", doc_title=act_title, source_file=source_file, text=piece,
            path=path, heading=heading, part=section.part, section=section.number,
            subsection=label, cite=f"{short_title}, s {ref}",
            cross_refs=[n for n in cited_sections(piece) if n != section.number],
            former_section=section.former_number, defined_term=term,
            split_index=k, split_total=len(pieces),
            char_start=section.char_start, char_end=section.char_end,
        )
        for k, piece in enumerate(pieces, start=1)
    ]


def guide_chunks(paragraphs: list[GuideParagraph], doc_id: str, guide_title: str,
                 short_title: str, source_file: str) -> list[Chunk]:
    """One chunk per numbered paragraph or annex (split if over MAX_TOKENS); Act sections
    cited in it become cross_refs."""
    chunks = []
    for paragraph in paragraphs:
        pieces = split_text(paragraph.text)
        label = paragraph.number if paragraph.number.startswith("Annex") else f"para {paragraph.number}"
        for k, piece in enumerate(pieces, start=1):
            chunks.append(Chunk(
                chunk_id=f"{doc_id}:{paragraph.number.replace(' ', '')}#{k}",
                doc_type="guide", doc_title=guide_title, source_file=source_file, text=piece,
                path=f"{guide_title} > {paragraph.heading} > {label}", heading=paragraph.heading,
                para=paragraph.number, cite=f"{short_title}, {label}",
                cross_refs=cited_sections(piece),
                split_index=k, split_total=len(pieces),
                char_start=paragraph.char_start, char_end=paragraph.char_end,
            ))
    return chunks


def naive_chunks(text: str, doc_id: str, doc_title: str, source_file: str,
                 span: tuple[int, int] | None = None,
                 size: int = NAIVE_SIZE, overlap: int = NAIVE_OVERLAP) -> list[Chunk]:
    """Baseline: windows of `size` tokens overlapping by `overlap`, no structure or metadata.

    `span` limits chunking to the same part of the text the structured parser reads, so the
    comparison isolates chunking. Character spans let naive chunks be scored against gold sections.
    """
    start, end = span or (0, len(text))
    tokens = list(TOKEN_RE.finditer(text, start, end))
    if not tokens:
        return []
    chunks = []
    step = size - overlap
    for k, first in enumerate(range(0, max(len(tokens) - overlap, 1), step), start=1):
        window = tokens[first:first + size]
        char_start, char_end = window[0].start(), window[-1].end()
        chunks.append(Chunk(
            chunk_id=f"naive:{doc_id}#{k:04d}", doc_type="naive", doc_title=doc_title,
            source_file=source_file, text=text[char_start:char_end],
            char_start=char_start, char_end=char_end,
        ))
    return chunks
