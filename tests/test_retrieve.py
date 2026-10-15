"""Retriever on a tiny synthetic Act (not real law) indexed into a temporary index/ folder.

Mirrors the renumbering in the real Act: s 37B used to be s 37C, and a different section is s 37C now.
"""

import pytest

from rag.bm25 import BM25Index
from rag.dense import DenseIndex
from rag.embed import HashEmbedder
from rag.fusion import RRF_K
from rag.retrieve import (CONFIGS, MAX_BOOSTED, MAX_EXPANDED, SECTION_BOOST, Corpus, IncompleteIndex,
                          RetrievalConfig, Retriever)
from rag.schema import Chunk, save_chunks


def act(section: str, subsection: str, text: str, heading: str, former: str = "", cross_refs=()) -> Chunk:
    label = f"{section}({subsection})" if subsection else section
    return Chunk(f"STA:s{label}#1", "act", "Sample Tax Act 2099", "sample.pdf", text,
                 path=f"Sample Tax Act 2099 > s {label}", heading=heading, section=section,
                 subsection=subsection, cite=f"STA 2099, s {label}", cross_refs=list(cross_refs),
                 former_section=former)


def guide(para: str, text: str, cross_refs=()) -> Chunk:
    return Chunk(f"GR:p{para}#1", "guide", "Group Relief Guide", "gr.pdf", text, path=f"Group Relief Guide > {para}",
                 para=para, cite=f"Group Relief Guide, para {para}", cross_refs=list(cross_refs))


STRUCTURED = [
    act("10", "1", "Income tax is payable on the income of any person accruing in Singapore.", "Charge of income tax"),
    act("10", "2", "In subsection (1), gains or profits means amounts received from a trade.", "Charge of income tax"),
    act("10", "10", "Interest paid by a bank is treated as income.", "Charge of income tax"),
    act("14R", "1", "A person who derives the first dollar of income may deduct previous expenses.",
        "Deduction for expenses incurred before first dollar of income", former="14U", cross_refs=["14X"]),
    act("14R", "2", "A previous expense is any outgoing incurred for that trade before the first dollar.",
        "Deduction for expenses incurred before first dollar of income", former="14U"),
    act("14X", "", "Deductible expenses incurred before commencement are attributed by basis period.",
        "Attribution of deductible expenses"),
    act("37B", "1", "A transferor company may transfer a qualifying deduction to a claimant company.",
        "Group relief for Singapore companies", former="37C"),
    act("37C", "", "A partnership may set off its losses against its partners' income.", "Partnership losses"),
    guide("5.1", "The group relief system allows a company to transfer loss items to another company "
                 "in the same group.", cross_refs=["37B"]),
]
NAIVE = [Chunk("naive:STA#0001", "naive", "Sample Tax Act 2099", "sample.pdf",
               "Income tax is payable ... a transferor company may transfer a qualifying deduction", char_start=0),
         Chunk("naive:STA#0002", "naive", "Sample Tax Act 2099", "sample.pdf",
               "previous expenses incurred before the first dollar of income", char_start=80)]


@pytest.fixture
def retriever(tmp_path):
    embedder = HashEmbedder(dim=128)
    for name, chunks in (("structured", STRUCTURED), ("naive", NAIVE)):
        (tmp_path / name).mkdir()
        save_chunks(tmp_path / name / "chunks.jsonl", chunks)
        BM25Index.build([c.chunk_id for c in chunks], [c.embed_text() for c in chunks]).save(tmp_path / name / "bm25.json")
        DenseIndex.open(tmp_path / "chroma", name, embedder.name).build(chunks, embedder)
    return Retriever(tmp_path, embedder)


def ids(result) -> list[str]:
    return [hit.chunk.chunk_id for hit in result.hits]


def test_named_configs():
    assert CONFIGS["baseline"] == RetrievalConfig("naive", bm25=False, dense=True)
    assert CONFIGS["improved"] == RetrievalConfig("structured", bm25=True, dense=True, section_boost=True,
                                                  expand_refs=True)


def test_hybrid_merges_both_retrievers(retriever):
    result = retriever.search("transfer loss items to another company in the same group", "structured_hybrid")
    top = result.hits[0]
    assert top.chunk.chunk_id in {"GR:p5.1#1", "STA:s37B(1)#1"}
    assert top.bm25_rank and top.dense_rank


def test_named_subsection_is_boosted_to_the_top(retriever):
    result = retriever.search("What does s 10(2) say?", "structured_bm25_boost")
    assert ids(result)[0] == "STA:s10(2)#1"
    assert [hit.boosted for hit in result.hits].count(True) == 1
    assert result.query_sections == ["10(2)"]


def test_subsection_without_its_own_chunk_boosts_the_whole_section(retriever):
    assert ids(retriever.search("explain s 14X(3)", "structured_bm25_boost"))[0] == "STA:s14X#1"


def test_a_number_that_exists_only_as_a_former_one_means_the_section_it_became(retriever):
    result = retriever.search("deducting previous expenses under section 14U", "structured_bm25_boost")
    assert [hit.chunk.section for hit in result.hits if hit.boosted] == ["14R", "14R"]
    assert ids(result)[0].startswith("STA:s14R")


def test_current_numbering_wins_when_a_number_is_both(retriever):
    result = retriever.search("section 37C", "structured_bm25_boost")
    assert ids(result)[0] == "STA:s37C#1"
    assert result.hits[0].score == pytest.approx(SECTION_BOOST + 1 / (RRF_K + 1))   # + BM25 rank 1: "37C" is in its path
    assert not any(hit.boosted for hit in result.hits if hit.chunk.section == "37B")


def test_boost_never_adds_chunks_the_retrievers_missed(retriever):
    # "14U" maps to s 14R, but nothing in the question matches s 14R's text or path
    assert retriever.search("section 14U", "structured_bm25_boost").hits == []


def test_at_most_two_chunks_of_a_named_section_are_boosted(retriever):
    result = retriever.search("What does s 10 say about income?", "structured_bm25_boost", k=9)
    assert sum(hit.boosted for hit in result.hits) == MAX_BOOSTED == 2
    assert {hit.chunk.section for hit in result.hits if hit.boosted} == {"10"}


def test_sections_of_other_acts_and_unboosted_configs_get_no_bonus(retriever):
    assert not any(hit.boosted for hit in retriever.search("s 10 of the Companies Act 1967", "improved").hits)
    assert not any(hit.boosted for hit in retriever.search("What does s 10(2) say?", "structured_bm25").hits)


def test_expansion_adds_cited_sections_that_are_not_already_hits(retriever):
    corpus = retriever.corpus("structured")
    guide_51, s37b = corpus.chunks["GR:p5.1#1"], corpus.chunks["STA:s37B(1)#1"]
    assert corpus.expand([guide_51]) == [s37b]
    assert corpus.expand([guide_51, s37b]) == []
    assert len(corpus.expand(list(corpus.chunks.values()))) <= MAX_EXPANDED


def test_improved_returns_expanded_context(retriever):
    result = retriever.search("group relief system loss items", "improved", k=1)
    assert ids(result) == ["GR:p5.1#1"]
    assert [chunk.chunk_id for chunk in result.expanded] == ["STA:s37B(1)#1"]


def test_baseline_searches_naive_chunks(retriever):
    result = retriever.search("previous expenses before the first dollar", "baseline", k=1)
    assert ids(result) == ["naive:STA#0002"]


def test_corpus_without_sections_has_nothing_to_boost():
    corpus = Corpus("naive", NAIVE, BM25Index.build([c.chunk_id for c in NAIVE], [c.text for c in NAIVE]))
    assert corpus.section_bonuses("s 10(2)", {"naive:STA#0001": 0.5}) == ({}, ["10(2)"])


def test_missing_index_says_how_to_build_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_index"):
        Retriever(tmp_path).search("anything", "structured_bm25")


def test_a_partly_built_dense_index_is_refused(tmp_path):
    embedder = HashEmbedder(dim=128)
    (tmp_path / "structured").mkdir()
    save_chunks(tmp_path / "structured" / "chunks.jsonl", STRUCTURED)
    BM25Index.build([c.chunk_id for c in STRUCTURED], [c.embed_text() for c in STRUCTURED]).save(
        tmp_path / "structured" / "bm25.json")
    DenseIndex.open(tmp_path / "chroma", "structured", embedder.name).build(STRUCTURED[:3], embedder)
    retriever = Retriever(tmp_path, embedder)
    with pytest.raises(IncompleteIndex, match="3 of 9"):
        retriever.search("group relief", "structured_hybrid")
    assert retriever.search("group relief", "structured_bm25").hits   # BM25 configs still work
