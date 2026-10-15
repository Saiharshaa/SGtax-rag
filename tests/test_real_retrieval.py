"""BM25 retrieval over the real chunks (no API key needed); skipped when data/processed/ is empty.

Sanity checks, not the evaluation: Phase 4 measures Recall@5 and MRR on the full question set.
"""

from pathlib import Path

import pytest

from rag.bm25 import BM25Index
from rag.retrieve import Retriever
from rag.schema import load_chunks, save_chunks

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
pytestmark = pytest.mark.skipif(not (PROCESSED / "chunks_structured.jsonl").exists(),
                                reason="chunks not built: run python scripts/build_chunks.py")


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    index_dir = tmp_path_factory.mktemp("index")
    chunks = load_chunks(PROCESSED / "chunks_structured.jsonl")
    (index_dir / "structured").mkdir()
    save_chunks(index_dir / "structured" / "chunks.jsonl", chunks)
    BM25Index.build([c.chunk_id for c in chunks], [c.embed_text() for c in chunks]).save(
        index_dir / "structured" / "bm25.json")
    return Retriever(index_dir)


def sections(result) -> list[str]:
    return [hit.chunk.section for hit in result.hits]


def test_pre_commencement_question_finds_s14R(retriever):
    result = retriever.search("Can a company deduct expenses it incurred before it started its business?",
                              "structured_bm25")
    assert "14R" in sections(result)


def test_group_loss_transfer_question_finds_group_relief(retriever):
    result = retriever.search("What are the conditions for transferring unabsorbed losses to another company "
                              "in the same group?", "structured_bm25")
    assert any(hit.chunk.section == "37B" or hit.chunk.source_file == "etax_group_relief.pdf" for hit in result.hits)


def test_named_subsection_comes_first(retriever):
    result = retriever.search("What does s 14R(2) say?", "structured_bm25_boost")
    assert result.hits[0].chunk.cite == "ITA 1947, s 14R(2)"


def test_pre_2020_number_still_finds_group_relief(retriever):
    assert "37B" in sections(retriever.search("group relief under section 37C", "structured_bm25_boost"))
