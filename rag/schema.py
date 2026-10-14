"""One chunk schema shared by the Act parser, the e-Tax guide parser and the naive baseline.

Empty strings (not None) mark "not applicable" because ChromaDB metadata values
must be str/int/float/bool.
"""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str      # "ITA:s14Q(2)#1", "etax_group_relief:p5.2#1", "naive:ITA_1947.pdf#0042"
    doc_type: str      # "act" | "guide" | "naive"
    doc_title: str     # "Income Tax Act 1947", or the e-Tax guide's title
    source_file: str   # file name in data/raw/
    text: str          # chunk body, as shown to users and passed to the LLM

    path: str = ""         # "Income Tax Act 1947 > Part 3 > s 10 > (1)"; empty for naive chunks
    heading: str = ""      # Act section heading, or the guide heading the paragraph sits under
    part: str = ""         # Act Part number, e.g. "3"
    section: str = ""      # Act section number, e.g. "14Q"
    subsection: str = ""   # Act subsection label, e.g. "2"
    para: str = ""         # guide paragraph number, e.g. "5.2"
    cite: str = ""         # citation the answer must use, e.g. "ITA 1947, s 14Q(2)"
    cross_refs: list[str] = field(default_factory=list)  # Act sections cited in the text, e.g. ["10", "14N"]
    former_section: str = ""   # Act section number before the 2020 Revised Edition, e.g. "14U"
    defined_term: str = ""     # for Interpretation chunks: the term defined, e.g. "company"
    split_index: int = 1   # k of n when a long section/paragraph is split
    split_total: int = 1
    repealed: bool = False

    # Span in the extracted document text. Both chunkers run over the same text, so a naive
    # chunk can be scored against gold sections by overlap even though it has no metadata.
    char_start: int = -1
    char_end: int = -1

    def embed_text(self) -> str:
        """Text indexed by BM25 and the embedder: hierarchy path and heading first, then the body."""
        header = "\n".join(part for part in (self.path, self.heading) if part)
        return f"{header}\n\n{self.text}" if header else self.text
