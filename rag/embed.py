"""Text embedders: Gemini via API for the real index, a hashing embedder for tests and offline runs.

Both return unit-length vectors, so cosine similarity is a dot product. `name` identifies the
model and dimension; the dense index records it so queries are never embedded by a different model.
"""

import hashlib
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Callable, Protocol

from google.genai import errors, types

from rag.bm25 import tokenize

GEMINI_MODEL = "gemini-embedding-001"   # override with GEMINI_EMBED_MODEL in .env
GEMINI_DIM = 768        # the model supports 768/1536/3072; 768 keeps the index small at little cost
# The free tier allows 100 embedding requests a minute and 1,000 a day, and counts every text in a batch
# as one. A batch of 100 only fits an empty window, so retrying one livelocks; batches of 50 paced to 100
# texts a minute never hit the minute limit. Set GEMINI_EMBED_PER_MINUTE on a paid tier (0: no pacing).
GEMINI_BATCH = 50
GEMINI_PER_MINUTE = 100
MAX_RETRIES = 10        # a 429 waits for its "retry in N s" hint or a full minute; 5xx back off 2, 4, ... 60 s
MAX_QUOTA_WAIT = 300    # a 429 asking for longer is the daily quota: stop instead of waiting
RETRY_IN_RE = re.compile(r"retry in ((?:[\d.]+(?:h|ms|m|s))+)")   # "829.7ms", "15.4s", "17h5m5.9s"
DURATION_PART_RE = re.compile(r"([\d.]+)(h|ms|m|s)")
UNIT_SECONDS = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}

log = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class MissingApiKey(RuntimeError):
    pass


class QuotaExhausted(RuntimeError):
    pass


def suggested_wait(error: errors.APIError) -> float | None:
    """Seconds a 429 asks us to wait ("Please retry in 15.49s.", "... in 17h5m5.9s."), if it says."""
    match = RETRY_IN_RE.search(f"{error.message} {error}")
    if not match:
        return None
    return sum(float(value) * UNIT_SECONDS[unit] for value, unit in DURATION_PART_RE.findall(match.group(1)))


def normalise(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector] if length else list(vector)


class GeminiEmbedder:
    """Gemini embeddings with task types (documents vs queries), batching, pacing and retry on 429/5xx."""

    def __init__(self, api_key: str | None = None, model: str | None = None, dim: int = GEMINI_DIM,
                 batch_size: int = GEMINI_BATCH, per_minute: int | None = None, client=None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        model = model or os.environ.get("GEMINI_EMBED_MODEL") or GEMINI_MODEL
        if per_minute is None:
            per_minute = int(os.environ.get("GEMINI_EMBED_PER_MINUTE") or GEMINI_PER_MINUTE)
        self.per_minute, self.clock, self._ready_at = per_minute, clock, 0.0
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

    def _pace(self, n_texts: int) -> None:
        """Wait until sending n_texts keeps us under per_minute texts a minute."""
        if self.per_minute <= 0:
            return
        now = self.clock()
        if now < self._ready_at:
            self.sleep(self._ready_at - now)
        self._ready_at = max(now, self._ready_at) + n_texts * 60 / self.per_minute

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dim)
        for attempt in range(MAX_RETRIES + 1):
            self._pace(len(texts))
            try:
                response = self.client.models.embed_content(model=self.model, contents=texts, config=config)
            except errors.APIError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == MAX_RETRIES:
                    raise
                suggested = suggested_wait(error)
                if suggested is not None and suggested > MAX_QUOTA_WAIT:
                    raise QuotaExhausted(
                        f"{self.model}: daily quota used up (free tier: 1,000 texts a day); it resets in "
                        f"{suggested / 3600:.1f} h. Rerun then, or enable billing on the API key's project.") from error
                if suggested is not None:
                    wait = suggested + 1
                elif error.code == 429:
                    wait = 61   # rejected requests count against the quota too: let the minute window empty
                else:
                    wait = min(60, 2 ** (attempt + 1))
                log.warning("Gemini embedding returned %s; retrying in %s s", error.code, wait)
                self.sleep(wait)
                continue
            if len(response.embeddings) != len(texts):
                # gemini-embedding-2 merges a list of texts into one multimodal input: one vector, not n
                raise ValueError(f"{self.model} returned {len(response.embeddings)} vectors for {len(texts)} "
                                 "texts; it may not support batches (use gemini-embedding-001)")
            return [normalise(embedding.values) for embedding in response.embeddings]
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


class CachedEmbedder:
    """Keeps query vectors on disk, so re-running the evaluation doesn't spend embedding quota
    (the free tier's 1,000 a day is shared with the index build). Documents pass straight through."""

    def __init__(self, inner: Embedder, path: Path):
        self.inner, self.path, self.name = inner, path, inner.name
        stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.vectors: dict[str, list[float]] = stored.get(self.name, {})

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if text not in self.vectors:
            self.vectors[text] = self.inner.embed_query(text)
            stored = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            stored[self.name] = self.vectors
            self.path.write_text(json.dumps(stored), encoding="utf-8")
        return self.vectors[text]
