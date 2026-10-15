"""Dense index: chunk embeddings in a persistent Chroma collection (cosine space), one per corpus.

Building is resumable. Each chunk's vector is stored with a hash of its text, and a rebuild only
embeds chunks that are new or changed, so an interrupted run (e.g. on the Gemini free-tier
quota) picks up where it stopped. The embedder's name is stored on the collection; querying with
a different embedder raises instead of returning nonsense.
"""

import hashlib
from collections.abc import Callable
from pathlib import Path

import chromadb

from rag.embed import Embedder
from rag.schema import Chunk

BUILD_BATCH = 100


def text_hash(chunk: Chunk) -> str:
    return hashlib.sha1(chunk.embed_text().encode("utf-8")).hexdigest()


class EmbedderMismatch(RuntimeError):
    pass


class DenseIndex:
    def __init__(self, collection):
        self.collection = collection

    @classmethod
    def open(cls, path: Path, corpus: str, embedder_name: str) -> "DenseIndex":
        """Open the corpus collection, creating it if needed. Raises if it was built by another embedder."""
        client = chromadb.PersistentClient(path=str(path))
        collection = client.get_or_create_collection(
            corpus, embedding_function=None, configuration={"hnsw": {"space": "cosine"}},
            metadata={"embedder": embedder_name})
        built_with = (collection.metadata or {}).get("embedder")
        if built_with != embedder_name:
            raise EmbedderMismatch(f"collection '{corpus}' was built with {built_with}, not {embedder_name}; "
                                   f"delete {path} and rebuild")
        return cls(collection)

    def build(self, chunks: list[Chunk], embedder: Embedder,
              progress: Callable[[int, int], None] = lambda done, total: None) -> int:
        """Embed new or changed chunks and drop ids no longer in `chunks`. Returns how many were embedded."""
        hashes = {chunk.chunk_id: text_hash(chunk) for chunk in chunks}
        stored = self.collection.get(include=["metadatas"])
        stored_hashes = {id_: (meta or {}).get("text_hash") for id_, meta in zip(stored["ids"], stored["metadatas"])}

        stale = [id_ for id_ in stored_hashes if id_ not in hashes]
        if stale:
            self.collection.delete(ids=stale)
        todo = [chunk for chunk in chunks if stored_hashes.get(chunk.chunk_id) != hashes[chunk.chunk_id]]
        for start in range(0, len(todo), BUILD_BATCH):
            batch = todo[start:start + BUILD_BATCH]
            vectors = embedder.embed_documents([chunk.embed_text() for chunk in batch])
            self.collection.upsert(
                ids=[chunk.chunk_id for chunk in batch], embeddings=vectors,
                metadatas=[{"text_hash": hashes[chunk.chunk_id], "doc_type": chunk.doc_type} for chunk in batch])
            progress(start + len(batch), len(todo))
        return len(todo)

    def search(self, vector: list[float], k: int = 10) -> list[tuple[str, float]]:
        """Top-k (chunk_id, cosine similarity), best first."""
        k = min(k, self.collection.count())
        if k == 0:
            return []
        result = self.collection.query(query_embeddings=[vector], n_results=k, include=["distances"])
        return [(id_, 1.0 - distance) for id_, distance in zip(result["ids"][0], result["distances"][0])]
