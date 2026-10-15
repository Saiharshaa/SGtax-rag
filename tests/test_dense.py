"""DenseIndex against a real (temporary) Chroma store, with the offline hash embedder."""

import pytest

from rag.dense import DenseIndex, EmbedderMismatch
from rag.embed import HashEmbedder
from rag.schema import Chunk


def chunk(id_: str, text: str) -> Chunk:
    return Chunk(id_, "act", "Sample Tax Act 2099", "sample.pdf", text)


CHUNKS = [chunk("a", "group relief transfer of losses between companies"),
          chunk("b", "renovation and refurbishment expenditure cap"),
          chunk("c", "expenses incurred before commencement of business")]


class CountingEmbedder(HashEmbedder):
    def __init__(self):
        super().__init__(dim=64)
        self.embedded: list[str] = []

    def embed_documents(self, texts):
        self.embedded += texts
        return super().embed_documents(texts)


def test_build_then_search_finds_the_closest_chunk(tmp_path):
    embedder = HashEmbedder(dim=64)
    index = DenseIndex.open(tmp_path, "structured", embedder.name)
    assert index.build(CHUNKS, embedder) == 3
    hits = index.search(embedder.embed_query("refurbishment expenditure cap"), k=2)
    assert hits[0][0] == "b"
    assert hits[0][1] > hits[1][1]


def test_rebuild_embeds_only_new_or_changed_chunks_and_drops_removed_ones(tmp_path):
    embedder = CountingEmbedder()
    DenseIndex.open(tmp_path, "structured", embedder.name).build(CHUNKS, embedder)
    embedder.embedded.clear()

    changed = [CHUNKS[0], chunk("b", "renovation works by sole proprietors"), chunk("d", "carry-back relief")]
    index = DenseIndex.open(tmp_path, "structured", embedder.name)
    assert index.build(changed, embedder) == 2
    assert len(embedder.embedded) == 2
    assert sorted(index.collection.get()["ids"]) == ["a", "b", "d"]


def test_opening_with_another_embedder_raises(tmp_path):
    DenseIndex.open(tmp_path, "structured", "hash@64")
    with pytest.raises(EmbedderMismatch):
        DenseIndex.open(tmp_path, "structured", "gemini-embedding-001@768")


def test_search_on_an_empty_collection(tmp_path):
    assert DenseIndex.open(tmp_path, "structured", "hash@64").search([0.0] * 64) == []
