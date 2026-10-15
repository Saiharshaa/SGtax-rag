"""Text embedders: Gemini via API for the real index, a hashing embedder for tests and offline runs.

Both return unit-length vectors, so cosine similarity is a dot product. `name` identifies the
model and dimension; the dense index records it so queries are never embedded by a different model.
"""

import hashlib
import math
import os
import time
from typing import Callable, Protocol

from google.genai import errors, types

from rag.bm25 import tokenize

GEMINI_MODEL = "gemini-embedding-001"   # override with GEMINI_EMBED_MODEL in .env
GEMINI_DIM = 768        # the model supports 768/1536/3072; 768 keeps the index small at little cost
GEMINI_BATCH = 100      # texts per request (the API maximum)
MAX_RETRIES = 8         # rate-limit waits back off 2, 4, ... 60 s: enough to ride out a per-minute quota


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class MissingApiKey(RuntimeError):
    pass


def normalise(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector] if length else list(vector)


class GeminiEmbedder:
    """Gemini embeddings with task types (documents vs queries), batching and retry on 429/5xx."""

    def __init__(self, api_key: str | None = None, model: str | None = None, dim: int = GEMINI_DIM,
                 batch_size: int = GEMINI_BATCH, client=None, sleep: Callable[[float], None] = time.sleep):
        model = model or os.environ.get("GEMINI_EMBED_MODEL") or GEMINI_MODEL
        if client is None:
            from google import genai
            api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise MissingApiKey("GEMINI_API_KEY is not set: add it to .env (see .env.example)")
            client = genai.Client(api_key=api_key)
        self.client, self.model, self.dim, self.batch_size, self.sleep = client, model, dim, batch_size, sleep
        self.name = f"{model}@{dim}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), self.batch_size):
            vectors += self._embed_batch(texts[start:start + self.batch_size], "RETRIEVAL_DOCUMENT")
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text], "RETRIEVAL_QUERY")[0]

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dim)
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.models.embed_content(model=self.model, contents=texts, config=config)
                return [normalise(embedding.values) for embedding in response.embeddings]
            except errors.APIError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == MAX_RETRIES:
                    raise
                self.sleep(min(60, 2 ** (attempt + 1)))
        raise AssertionError("unreachable")


class HashEmbedder:
    """Bag of stemmed words hashed into `dim` buckets. No API, deterministic: for tests and dry runs.
    Texts sharing words land close together, which is all the retrieval tests need."""

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.name = f"hash@{dim}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim] += 1.0
        return normalise(vector)
