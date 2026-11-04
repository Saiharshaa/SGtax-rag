"""A* dependency expansion: an alternative to `Corpus.expand` that adds what the retrieved chunks depend on.

`Corpus.expand` appends the first chunk of up to 3 sections the hits cite. This module instead searches a
graph of the structured chunks for the hits' dependencies, cheapest first, within a token allowance:

* REFERS_TO   "subsection (4)" -> that subsection of the same section; "subsection (1) of section 37B" ->
              s 37B(1); "paragraph 6.1" in a guide -> that paragraph; each section in `cross_refs` -> any
              chunk of that section.
* DEFINED_IN  an Act subsection -> the subsection of its section that defines its terms ("In this section
              ...", "In subsection (4) ...", "For the purposes of subsection (7) ...").
* CONTINUES   piece k of a split provision -> piece k - 1.

A dependency on a section, or on a subsection split into pieces, is resolved by any of its chunks. Chunks
added for a hit can have dependencies of their own, which the search then follows too.

The search is the A* of Experiment 3 (R6) in Khawpuneiei/Legal_RAG_Exp (docs/experiment3-results.md), adapted
to this corpus as condition R6y: f = g + h with
    g = sum over the path from a hit of (edge cost + tokens(added chunk) / budget), budget = hit tokens + allowance
    h = MU * unresolved dependencies(chunk) * C_MIN
The heuristic there also has a query-similarity term. The search there can also follow seed-only edges from the
hits: embedding neighbours, and guide paragraphs that cite an Act section. These are not dependencies, and R6y
leaves them out by design. Its two weights were then tuned on the held-out dev questions, and both came out 0.
So this is a cheapest-first search over dependency edges, and it needs no embeddings.
"""

import heapq
import re
from collections import defaultdict

from rag.chunk import count_tokens
from rag.schema import Chunk

ALLOWANCE = 450      # extra tokens after the hits: Corpus.expand's mean on the dev questions
MU = 0.0             # weight of the unresolved-dependency heuristic (tuned on dev)
C_MIN = 0.2          # the reference's scale for h (its cheapest dependency edge on the legal clause graph)
EDGE_COST = {"CONTINUES": 0.1, "DEFINED_IN": 0.2, "REFERS_TO": 0.3}

_LABELS = r"((?:\(\w+\)(?:\s*(?:,|and|or|to)\s*)?)+)"
SUBSECTION_REF = re.compile(rf"\bsubsections?\s+{_LABELS}(\s+of\s+section\s+(\d+[A-Z]{{0,3}}))?", re.I)
PARA_REF = re.compile(r"\bparagraphs?\s+(\d+\.\d+(?:\s*(?:,|and|or|to)\s*\d+\.\d+)*)", re.I)
LOCAL_DEFINITION = re.compile(r"^(?:In|For the purposes of)\s+(this section|this Part|subsections?\s+" + _LABELS + ")",
                              re.I)


def _labels(text: str) -> list[str]:
    return [label.upper() if label[0].isdigit() else label.lower() for label in re.findall(r"\((\w+)\)", text)]


def build_edges(chunks: list[Chunk]) -> list[dict]:
    """Dependency edges src -> dst with a type and a group: any chunk of the group resolves the dependency."""
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    by_section: dict[str, list[str]] = defaultdict(list)          # "37B" -> chunk ids
    by_sub: dict[tuple[str, str], list[str]] = defaultdict(list)  # ("37B", "1") -> chunk ids (split pieces)
    by_para: dict[tuple[str, str], list[str]] = defaultdict(list) # (guide, "6.1") -> chunk ids
    for chunk in chunks:
        if chunk.doc_type == "act":
            by_section[chunk.section].append(chunk.chunk_id)
            if chunk.subsection:
                by_sub[(chunk.section, chunk.subsection)].append(chunk.chunk_id)
        else:
            by_para[(chunk.chunk_id.split(":", 1)[0], chunk.para)].append(chunk.chunk_id)
    edges: list[dict] = []

    def add(src: str, dsts: list[str], etype: str, group: str) -> None:
        for dst in dsts:
            if dst != src:
                edges.append(dict(src=src, dst=dst, type=etype, group=group))

    for chunk in chunks:
        if chunk.doc_type == "act":
            for m in SUBSECTION_REF.finditer(chunk.text):
                section = m.group(3) or chunk.section
                for label in _labels(m.group(1)):
                    if (section, label) in by_sub and not (section == chunk.section and label == chunk.subsection):
                        add(chunk.chunk_id, by_sub[(section, label)], "REFERS_TO", f"sub:{section}({label})")
            if chunk.split_index > 1:
                pieces = by_sub.get((chunk.section, chunk.subsection)) or by_section[chunk.section]
                i = pieces.index(chunk.chunk_id)
                if i > 0:
                    add(chunk.chunk_id, [pieces[i - 1]], "CONTINUES", pieces[i - 1])
        else:
            doc = chunk.chunk_id.split(":", 1)[0]
            for m in PARA_REF.finditer(chunk.text):
                for para in re.findall(r"\d+\.\d+", m.group(1)):
                    if (doc, para) in by_para and para != chunk.para:
                        add(chunk.chunk_id, by_para[(doc, para)], "REFERS_TO", f"para:{doc}:{para}")
            if chunk.split_index > 1:
                pieces = by_para[(doc, chunk.para)]
                i = pieces.index(chunk.chunk_id)
                if i > 0:
                    add(chunk.chunk_id, [pieces[i - 1]], "CONTINUES", pieces[i - 1])
        own = chunk.section if chunk.doc_type == "act" else None
        for section in chunk.cross_refs:
            if section != own and section in by_section:
                add(chunk.chunk_id, by_section[section], "REFERS_TO", f"sec:{section}")
    for section, ids in by_section.items():   # section-local definitions
        for definition in ids:
            m = LOCAL_DEFINITION.match(by_id[definition].text.strip())
            if not m:
                continue
            scope = m.group(1).lower()
            if scope.startswith("subsection"):
                targets = [id_ for label in _labels(m.group(2) or "") for id_ in by_sub.get((section, label), [])]
            elif scope == "this part":
                targets = [c.chunk_id for c in chunks if c.doc_type == "act" and c.part == by_id[definition].part]
            else:
                targets = ids
            for id_ in targets:
                if id_ != definition:
                    edges.append(dict(src=id_, dst=definition, type="DEFINED_IN", group=definition))
    return edges


class DependencyGraph:
    """The structured chunks and their dependency edges, with the A* expansion."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.tokens = {chunk.chunk_id: count_tokens(chunk.text) for chunk in chunks}
        self.out: dict[str, list[tuple[str, float]]] = defaultdict(list)
        groups: dict[str, dict[str, set[str]]] = defaultdict(dict)
        for e in build_edges(chunks):
            self.out[e["src"]].append((e["dst"], EDGE_COST[e["type"]]))
            groups[e["src"]].setdefault(e["group"], set()).add(e["dst"])
        # chunk id -> its dependencies; each is a set of chunks, any one of which resolves it
        self.deps: dict[str, list[set[str]]] = {id_: list(groups[id_].values()) for id_ in self.chunks}

    def unresolved(self, chunk_id: str, evidence: set[str]) -> int:
        return sum(1 for group in self.deps.get(chunk_id, ()) if not group & evidence)

    def expand(self, hits: list[Chunk], allowance: int = ALLOWANCE, mu: float = MU) -> list[Chunk]:
        """Chunks the hits depend on, in the order A* adds them, within `allowance` tokens after the hits.
        The hits stay first and unchanged. The search stops when no dependency of the evidence is unresolved,
        or when the allowance or the frontier runs out; a chunk too long for what is left is skipped."""
        seeds = list(dict.fromkeys(chunk.chunk_id for chunk in hits))
        used = sum(self.tokens[id_] for id_ in seeds)
        budget = used + allowance
        evidence, have = list(seeds), set(seeds)

        def h(id_: str) -> float:
            return mu * self.unresolved(id_, have) * C_MIN

        frontier = [(h(s), i, s, 0.0) for i, s in enumerate(seeds)]
        heapq.heapify(frontier)
        tie = len(seeds)
        while frontier and used < budget:
            _, _, id_, g = heapq.heappop(frontier)
            if id_ in have and not (id_ in seeds and g == 0.0):
                continue
            if id_ not in have:
                if used + self.tokens[id_] > budget:
                    continue
                evidence.append(id_)
                have.add(id_)
                used += self.tokens[id_]
            if all(self.unresolved(e, have) == 0 for e in evidence):
                break
            for dst, cost in self.out[id_]:
                if dst in have:
                    continue
                g2 = g + cost + self.tokens[dst] / budget
                heapq.heappush(frontier, (g2 + h(dst), tie, dst, g2))
                tie += 1
        return [self.chunks[id_] for id_ in evidence[len(seeds):]]
