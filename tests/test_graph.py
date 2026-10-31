"""A* dependency expansion (rag/graph.py) on a tiny synthetic Act and guide (not real law)."""

import pytest

from rag.bm25 import BM25Index
from rag.dense import DenseIndex
from rag.embed import HashEmbedder
from rag.graph import DependencyGraph, build_edges
from rag.retrieve import CONFIGS, RetrievalConfig, Retriever
from rag.schema import Chunk, save_chunks


def act(section: str, subsection: str, text: str, part: str = "1", cross_refs=(), split=(1, 1)) -> Chunk:
    label = f"{section}({subsection})" if subsection else section
    return Chunk(f"STA:s{label}#{split[0]}", "act", "Sample Tax Act 2099", "sample.pdf", text,
                 path=f"Sample Tax Act 2099 > s {label}", heading=f"Section {section}", part=part, section=section,
                 subsection=subsection, cite=f"STA 2099, s {label}", cross_refs=list(cross_refs),
                 split_index=split[0], split_total=split[1])


def guide(para: str, text: str, cross_refs=(), split=(1, 1)) -> Chunk:
    return Chunk(f"GR:p{para}#{split[0]}", "guide", "Group Relief Guide", "gr.pdf", text,
                 path=f"Group Relief Guide > {para}", para=para, cite=f"Group Relief Guide, para {para}",
                 cross_refs=list(cross_refs), split_index=split[0], split_total=split[1])


CHUNKS = [   # tokens: 12, 16, 14, 17, 17, 13, 16, 13
    act("10", "1", "Income tax is payable on gains or profits from any trade."),
    act("10", "2", "In subsection (1), gains or profits means amounts received from a trade."),
    act("37B", "1", "A transferor company may transfer a qualifying deduction under subsection (3).", part="2"),
    act("37B", "3", "A qualifying deduction is a trade loss of the year, and capital allowances under section 19A",
        part="2", cross_refs=["19A"], split=(1, 2)),
    act("37B", "3", "of that year, to the extent not deducted against the transferor's own income.", part="2",
        split=(2, 2)),
    act("19A", "1", "An allowance is made for plant and machinery used in the trade.", part="3"),
    guide("6.1", "A claimant company may claim the deduction as set out in paragraph 6.2.", cross_refs=["37B"]),
    guide("6.2", "The claim is made in the return for the year of assessment."),
]


def ids(chunks) -> list[str]:
    return [chunk.chunk_id for chunk in chunks]


@pytest.fixture
def graph() -> DependencyGraph:
    return DependencyGraph(CHUNKS)


def edges_of(edge_type: str) -> set[tuple[str, str]]:
    return {(e["src"], e["dst"]) for e in build_edges(CHUNKS) if e["type"] == edge_type}


def test_definitions_cross_references_and_split_pieces_are_edges():
    assert edges_of("DEFINED_IN") == {("STA:s10(1)#1", "STA:s10(2)#1")}
    refers = edges_of("REFERS_TO")
    assert ("STA:s37B(1)#1", "STA:s37B(3)#1") in refers and ("STA:s37B(1)#1", "STA:s37B(3)#2") in refers
    assert ("STA:s37B(3)#1", "STA:s19A(1)#1") in refers                      # cross_refs: section 19A
    assert ("GR:p6.1#1", "GR:p6.2#1") in refers                              # paragraph 6.2 in the same guide
    assert ("GR:p6.1#1", "STA:s37B(1)#1") in refers                          # cross_refs of a guide paragraph
    assert edges_of("CONTINUES") == {("STA:s37B(3)#2", "STA:s37B(3)#1")}
    assert {e["type"] for e in build_edges(CHUNKS)} == {"REFERS_TO", "DEFINED_IN", "CONTINUES"}


def test_expansion_adds_the_definition_a_hit_depends_on(graph):
    assert ids(graph.expand([CHUNKS[0]])) == ["STA:s10(2)#1"]


def test_any_piece_of_a_split_subsection_resolves_a_reference_to_it(graph):
    assert graph.unresolved("STA:s37B(1)#1", {"STA:s37B(1)#1"}) == 1
    assert graph.unresolved("STA:s37B(1)#1", {"STA:s37B(1)#1", "STA:s37B(3)#2"}) == 0


def test_expansion_follows_dependencies_of_dependencies_until_all_are_resolved(graph):
    added = graph.expand([CHUNKS[2]])
    assert {"STA:s37B(3)#1", "STA:s19A(1)#1"} <= set(ids(added))   # s 37B(3) cites s 19A
    evidence = {CHUNKS[2].chunk_id} | set(ids(added))
    assert all(graph.unresolved(id_, evidence) == 0 for id_ in evidence)


def test_hits_are_never_repeated_and_dependencies_already_present_add_nothing(graph):
    assert graph.expand([CHUNKS[0], CHUNKS[1]]) == []
    assert graph.expand([CHUNKS[0], CHUNKS[0]]) == [CHUNKS[1]]


def test_nothing_is_added_beyond_the_allowance_and_a_chunk_too_long_for_it_is_skipped(graph):
    assert graph.expand([CHUNKS[0]], allowance=0) == []
    assert graph.expand([CHUNKS[0]], allowance=12) == []                   # its definition has 16 tokens
    assert ids(graph.expand([CHUNKS[0]], allowance=20)) == ["STA:s10(2)#1"]
    assert ids(graph.expand([CHUNKS[2], CHUNKS[6]], allowance=20)) == ["GR:p6.2#1"]   # then s 37B(3) does not fit


# Expected additions computed with the reference implementation, the experiments' TaxGraph.expand with
# dependency edges only and a zero similarity weight (condition R6y), on these chunks.
REFERENCE = [
    ([2], 450, 0.0, ["STA:s37B(3)#1", "STA:s37B(3)#2", "STA:s19A(1)#1"]),
    ([2], 450, 2.0, ["STA:s37B(3)#1", "STA:s19A(1)#1"]),     # the heuristic avoids the piece that needs another
    ([6], 450, 0.0, ["GR:p6.2#1", "STA:s37B(1)#1", "STA:s37B(3)#1", "STA:s37B(3)#2", "STA:s19A(1)#1"]),
    ([6], 450, 2.0, ["GR:p6.2#1", "STA:s37B(1)#1", "STA:s37B(3)#1", "STA:s19A(1)#1"]),
    ([2, 6], 450, 0.0, ["GR:p6.2#1", "STA:s37B(3)#1", "STA:s37B(3)#2", "STA:s19A(1)#1"]),
    ([0, 2], 450, 0.0, ["STA:s10(2)#1", "STA:s37B(3)#1", "STA:s37B(3)#2", "STA:s19A(1)#1"]),
    ([4], 450, 0.0, ["STA:s37B(3)#1", "STA:s19A(1)#1"]),
]


@pytest.mark.parametrize("hits, allowance, mu, expected", REFERENCE)
def test_expansion_matches_the_reference_implementation(graph, hits, allowance, mu, expected):
    assert ids(graph.expand([CHUNKS[i] for i in hits], allowance=allowance, mu=mu)) == expected


SCOPES = [   # tokens: 13, 14, 7, 14, 8, 20, 18, 16, 6
    act("50", "1", "In this section, relevant person means a company resident in Singapore."),
    act("50", "2", "A relevant person may claim the allowance in the year it is incurred."),
    act("50", "3", "The claim is made in writing."),
    act("60", "1", "In this Part, approved fund means a fund approved by the Minister.", part="9"),
    act("61", "1", "Contributions to an approved fund are deductible.", part="9"),
    act("70", "1", "In subsection (2), qualifying cost means the cost of plant and machinery used in the trade."),
    act("70", "2", "A deduction is allowed for qualifying cost under subsection (3) and subsection (4)."),
    act("70", "3", "The deduction is spread over three years of assessment starting from the year of purchase."),
    act("70", "4", "No deduction is allowed twice."),
]


def test_definitions_apply_to_their_section_part_or_subsections():
    defined = {(e["src"], e["dst"]) for e in build_edges(SCOPES) if e["type"] == "DEFINED_IN"}
    assert defined == {("STA:s50(2)#1", "STA:s50(1)#1"), ("STA:s50(3)#1", "STA:s50(1)#1"),   # "In this section"
                       ("STA:s61(1)#1", "STA:s60(1)#1"),                                     # "In this Part"
                       ("STA:s70(2)#1", "STA:s70(1)#1")}                                     # "In subsection (2)"


def test_cheaper_edges_go_first_and_a_dependency_that_does_not_fit_is_skipped_not_the_end():
    graph = DependencyGraph(SCOPES)
    # the definition (DEFINED_IN, 0.2) before the referred subsections (REFERS_TO, 0.3), although it is the longest
    assert ids(graph.expand([SCOPES[6]])) == ["STA:s70(1)#1", "STA:s70(4)#1", "STA:s70(3)#1"]
    # with 17 tokens to spare the 20-token definition is skipped and the 6-token s 70(4) still added
    assert ids(graph.expand([SCOPES[6]], allowance=17)) == ["STA:s70(4)#1"]


def test_the_search_goes_on_past_a_dependency_too_long_for_what_is_left():
    long = " ".join(["for that expenditure in each year of assessment"] * 18)
    split = [   # tokens: 23, 152, 6
        act("90", "1", "Where a company incurs expenditure on the provision of plant or machinery for the purposes "
                       "of its trade, the company may claim", split=(1, 2)),
        act("90", "1", f"an allowance under subsection (2) {long}.", split=(2, 2)),
        act("90", "2", "The allowance is one third."),
    ]
    graph = DependencyGraph(split)
    assert ids(graph.expand([split[1]])) == ["STA:s90(1)#1", "STA:s90(2)#1"]
    # the earlier piece (CONTINUES, 0.1) comes off the frontier first but needs 23 tokens; s 90(2) still fits
    assert ids(graph.expand([split[1]], allowance=20)) == ["STA:s90(2)#1"]


@pytest.fixture
def retriever(tmp_path):
    embedder = HashEmbedder(dim=128)
    (tmp_path / "structured").mkdir()
    save_chunks(tmp_path / "structured" / "chunks.jsonl", CHUNKS)
    BM25Index.build(ids(CHUNKS), [c.embed_text() for c in CHUNKS]).save(tmp_path / "structured" / "bm25.json")
    DenseIndex.open(tmp_path / "chroma", "structured", embedder.name).build(CHUNKS, embedder)
    return Retriever(tmp_path, embedder)


def test_improved_astar_keeps_the_hits_of_improved_and_only_changes_the_expansion(retriever):
    assert CONFIGS["improved_astar"] == RetrievalConfig("structured", bm25=True, dense=True, section_boost=True,
                                                        expand_astar=True, bm25_only_for_section_refs=True)
    question = "May a transferor company transfer a qualifying deduction?"
    improved = retriever.search(question, "improved", k=1)
    astar = retriever.search(question, "improved_astar", k=1)
    assert ids(h.chunk for h in astar.hits) == ids(h.chunk for h in improved.hits) == ["STA:s37B(1)#1"]
    assert ids(improved.expanded) == []                                      # s 37B(1) cites no other section
    assert ids(astar.expanded) == ["STA:s37B(3)#1", "STA:s37B(3)#2", "STA:s19A(1)#1"]
