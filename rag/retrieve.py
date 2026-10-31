"""Phase 2 retrieval: BM25 and/or dense search over one corpus, merged by RRF, with an
exact-section boost and optional one-hop expansion along cross-references.

Named configs are the rows of the evaluation table. `baseline` is the naive-chunk dense
retriever the project argues against; `improved` is structured chunks + hybrid + section boost.
`improved_astar` is `improved` with the one-hop expansion replaced by A* dependency expansion (rag/graph.py).

    retriever = Retriever()
    result = retriever.search("Can a company deduct expenses before it started business?", "improved")
"""

from dataclasses import dataclass, field
from pathlib import Path

from rag.bm25 import BM25Index
from rag.chunk import count_tokens
from rag.dense import DenseIndex
from rag.embed import Embedder, GeminiEmbedder
from rag.fusion import RRF_K, rrf
from rag.graph import DependencyGraph
from rag.refs import find_section_refs
from rag.schema import Chunk, load_chunks

DEFAULT_INDEX_DIR = Path(__file__).resolve().parent.parent / "index"
CANDIDATES = 50                      # per retriever, before fusion
SECTION_BOOST = 1.0 / (RRF_K + 1)    # worth one extra first-place vote in the fusion
MAX_BOOSTED = 2                      # chunks per named section, so it can't crowd out the guide paragraphs on it
MAX_EXPANDED = 3                    # sections pulled in by one-hop expansion


def within_budget(ranked: list[Chunk], tokens: int) -> list[Chunk]:
    """The leading chunks whose texts fit in `tokens` (always at least one). Equal context is fairer than
    equal count: five naive chunks hold several times the text of five structured ones."""
    kept, used = [], 0
    for chunk in ranked:
        used += count_tokens(chunk.text)
        if kept and used > tokens:
            break
        kept.append(chunk)
    return kept


class IncompleteIndex(RuntimeError):
    """The dense index is missing chunks (e.g. the build stopped at the embedding quota)."""


@dataclass(frozen=True)
class RetrievalConfig:
    corpus: str              # "structured" | "naive"
    bm25: bool
    dense: bool
    section_boost: bool = False
    expand_refs: bool = False
    expand_astar: bool = False   # A* dependency expansion (rag/graph.py) instead of the one-hop one
    # Use BM25 only when the question names a section. On the eval set, dense alone did best on plain-language
    # questions (Recall@5 0.66 vs 0.57 hybrid) and hybrid on those naming a section (0.67-0.75 vs 0.50-0.56).
    bm25_only_for_section_refs: bool = False


CONFIGS = {
    "naive_bm25": RetrievalConfig("naive", bm25=True, dense=False),
    "naive_dense": RetrievalConfig("naive", bm25=False, dense=True),
    "structured_bm25": RetrievalConfig("structured", bm25=True, dense=False),
    "structured_bm25_boost": RetrievalConfig("structured", bm25=True, dense=False, section_boost=True),
    "structured_dense": RetrievalConfig("structured", bm25=False, dense=True),
    "structured_hybrid": RetrievalConfig("structured", bm25=True, dense=True),
    "structured_hybrid_boost": RetrievalConfig("structured", bm25=True, dense=True, section_boost=True),
    "structured_routed": RetrievalConfig("structured", bm25=True, dense=True, section_boost=True,
                                         bm25_only_for_section_refs=True),
}
CONFIGS["baseline"] = CONFIGS["naive_dense"]
CONFIGS["improved"] = RetrievalConfig("structured", bm25=True, dense=True, section_boost=True, expand_refs=True,
                                      bm25_only_for_section_refs=True)
CONFIGS["improved_astar"] = RetrievalConfig("structured", bm25=True, dense=True, section_boost=True, expand_astar=True,
                                            bm25_only_for_section_refs=True)
# What the app falls back to when dense search is unavailable (index still building, embedding quota used up)
CONFIGS["improved_bm25"] = RetrievalConfig("structured", bm25=True, dense=False, section_boost=True, expand_refs=True)


@dataclass
class Hit:
    chunk: Chunk
    score: float
    bm25_rank: int | None = None     # 1-based rank in each retriever's list, for explaining results
    dense_rank: int | None = None
    boosted: bool = False


@dataclass
class RetrievalResult:
    query: str
    hits: list[Hit]
    expanded: list[Chunk] = field(default_factory=list)   # cited sections (or A*'s additions): extra context
    query_sections: list[str] = field(default_factory=list)


class Corpus:
    """One corpus's chunks, BM25 index and (lazily) dense index, loaded from index/<name>/."""

    def __init__(self, name: str, chunks: list[Chunk], bm25: BM25Index, dense: DenseIndex | None = None):
        self.name, self.bm25, self.dense = name, bm25, dense
        self._graph: DependencyGraph | None = None
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.order = {chunk.chunk_id: i for i, chunk in enumerate(chunks)}
        self.by_section: dict[str, list[str]] = {}       # "14R" -> chunk ids in document order
        self.current_for_former: dict[str, set[str]] = {}   # "14U" -> {"14R"}
        for chunk in chunks:
            if chunk.doc_type == "act" and chunk.section:
                self.by_section.setdefault(chunk.section, []).append(chunk.chunk_id)
                if chunk.former_section:
                    self.current_for_former.setdefault(chunk.former_section, set()).add(chunk.section)

    @classmethod
    def load(cls, index_dir: Path, name: str) -> "Corpus":
        folder = index_dir / name
        if not (folder / "bm25.json").exists():
            raise FileNotFoundError(f"no index in {folder}: run python scripts/build_index.py")
        return cls(name, load_chunks(folder / "chunks.jsonl"), BM25Index.load(folder / "bm25.json"))

    def section_chunks(self, section: str, labels: tuple[str, ...] = ()) -> list[str]:
        """Chunk ids of a section; "s 14R(2)" narrows to subsection (2) when it is a chunk of its own."""
        ids = self.by_section.get(section, [])
        if labels:
            ids = [id_ for id_ in ids if self.chunks[id_].subsection == labels[0]] or ids
        return ids

    def sections_meant(self, number: str) -> set[str]:
        """The section a number in a question refers to. Current numbering wins (71 of the 98 pre-2020
        numbers are also current numbers, and the guides use 2020 numbering); a number that exists only
        as a former one ("14U") means the section it became."""
        if number in self.by_section:
            return {number}
        return self.current_for_former.get(number, set())

    def section_bonuses(self, query: str, scores: dict[str, float]) -> tuple[dict[str, float], list[str]]:
        """Chunk id -> bonus for the best-scoring retrieved chunks (at most MAX_BOOSTED) of each section
        named in the query, and the sections named. Only chunks the retrievers found are boosted: injecting
        whole sections flooded the top 5 (evaluation, 2026-10-15)."""
        bonuses: dict[str, float] = {}
        refs = [ref for ref in find_section_refs(query) if not ref.is_external]
        for ref in refs:
            for section in self.sections_meant(ref.section):
                found = [id_ for id_ in self.section_chunks(section, ref.labels) if id_ in scores]
                for id_ in sorted(found, key=lambda id_: (-scores[id_], self.order[id_]))[:MAX_BOOSTED]:
                    bonuses[id_] = SECTION_BOOST
        return bonuses, [ref.canonical for ref in refs]

    def dependency_graph(self) -> DependencyGraph:
        """Built from the chunks on first use."""
        if self._graph is None:
            self._graph = DependencyGraph(list(self.chunks.values()))
        return self._graph

    def expand(self, hits: list[Chunk]) -> list[Chunk]:
        """First chunk of each section the hits cite that isn't already among them (one hop, capped)."""
        have = {chunk.section for chunk in hits if chunk.doc_type == "act"}
        expanded = []
        for chunk in hits:
            for section in chunk.cross_refs:
                if section not in have and section in self.by_section and len(expanded) < MAX_EXPANDED:
                    have.add(section)
                    expanded.append(self.chunks[self.by_section[section][0]])
        return expanded


class Retriever:
    def __init__(self, index_dir: Path = DEFAULT_INDEX_DIR, embedder: Embedder | None = None):
        self.index_dir, self._embedder = index_dir, embedder
        self._corpora: dict[str, Corpus] = {}

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = GeminiEmbedder()
        return self._embedder

    def corpus(self, name: str, dense: bool = False) -> Corpus:
        if name not in self._corpora:
            self._corpora[name] = Corpus.load(self.index_dir, name)
        corpus = self._corpora[name]
        if dense and corpus.dense is None:
            index = DenseIndex.open(self.index_dir / "chroma", name, self.embedder.name)
            if index.count() != len(corpus.chunks):
                raise IncompleteIndex(f"the dense index for '{name}' has {index.count()} of {len(corpus.chunks)} "
                                      "chunks: finish python scripts/build_index.py, or use a BM25 config")
            corpus.dense = index
        return corpus

    def search(self, query: str, config: str | RetrievalConfig = "improved", k: int = 5,
               budget: int | None = None) -> RetrievalResult:
        """The top k chunks, or with `budget`, the leading chunks that fit in that many tokens."""
        cfg = CONFIGS[config] if isinstance(config, str) else config
        corpus = self.corpus(cfg.corpus, dense=cfg.dense)
        rankings: dict[str, list[str]] = {}
        names_section = any(not ref.is_external for ref in find_section_refs(query))
        if cfg.bm25 and (names_section or not cfg.bm25_only_for_section_refs or not cfg.dense):
            rankings["bm25"] = [id_ for id_, _ in corpus.bm25.search(query, CANDIDATES)]
        if cfg.dense:
            rankings["dense"] = [id_ for id_, _ in corpus.dense.search(self.embedder.embed_query(query), CANDIDATES)]
        scores = rrf(list(rankings.values()))

        bonuses, sections = corpus.section_bonuses(query, scores) if cfg.section_boost else ({}, [])
        for id_, bonus in bonuses.items():
            scores[id_] += bonus

        # Ties keep document order: s 10(2) before s 10(10).
        ordered = sorted(scores, key=lambda id_: (-scores[id_], corpus.order[id_]))
        if budget is None:
            best = ordered[:k]
        else:
            best = [chunk.chunk_id for chunk in within_budget([corpus.chunks[id_] for id_ in ordered], budget)]
        positions = {name: {id_: rank for rank, id_ in enumerate(ids, start=1)} for name, ids in rankings.items()}
        hits = [Hit(corpus.chunks[id_], scores[id_], positions.get("bm25", {}).get(id_),
                    positions.get("dense", {}).get(id_), id_ in bonuses)
                for id_ in best]
        if cfg.expand_astar:
            expanded = corpus.dependency_graph().expand([hit.chunk for hit in hits])
        else:
            expanded = corpus.expand([hit.chunk for hit in hits]) if cfg.expand_refs else []
        return RetrievalResult(query, hits, expanded, sections)
