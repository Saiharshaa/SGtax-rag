import math
from types import SimpleNamespace

import pytest
from google.genai import errors

from rag.embed import GeminiEmbedder, HashEmbedder, MissingApiKey, QuotaExhausted, suggested_wait


class FakeModels:
    """Stands in for client.models: records calls, can fail the first `failures` calls."""

    def __init__(self, failures: list[int] = ()):
        self.calls, self.failures = [], list(failures)

    def embed_content(self, model, contents, config):
        self.calls.append((model, list(contents), config.task_type, config.output_dimensionality))
        if self.failures:
            code = self.failures.pop(0)
            raise errors.APIError(code, {"error": {"code": code, "message": "fake", "status": "FAKE"}})
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0]) for _ in contents])


def embedder(models: FakeModels, sleeps: list | None = None) -> GeminiEmbedder:
    return GeminiEmbedder(model="m", dim=2, batch_size=2, per_minute=0, client=SimpleNamespace(models=models),
                          sleep=(sleeps if sleeps is not None else []).append)


def test_documents_are_batched_with_the_document_task_type():
    models = FakeModels()
    vectors = embedder(models).embed_documents(["a", "b", "c"])
    assert [call[1] for call in models.calls] == [["a", "b"], ["c"]]
    assert {call[2] for call in models.calls} == {"RETRIEVAL_DOCUMENT"}
    assert vectors == [[0.6, 0.8]] * 3     # unit length


def test_query_uses_the_query_task_type():
    models = FakeModels()
    embedder(models).embed_query("q")
    assert models.calls == [("m", ["q"], "RETRIEVAL_QUERY", 2)]


def test_rate_limit_waits_a_minute_and_server_errors_back_off():
    models, sleeps = FakeModels(failures=[429, 503, 503]), []
    assert embedder(models, sleeps).embed_query("q") == [0.6, 0.8]
    assert sleeps == [61, 4, 8]


def test_client_errors_are_not_retried():
    with pytest.raises(errors.APIError):
        embedder(FakeModels(failures=[400])).embed_query("q")


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingApiKey):
        GeminiEmbedder()


def test_name_records_model_and_dimension():
    assert embedder(FakeModels()).name == "m@2"


def test_hash_embedder_is_deterministic_and_puts_shared_words_closer():
    hashed = HashEmbedder(dim=64)
    a, b, c = hashed.embed_documents(["group relief for companies", "group relief claim", "renovation cap"])
    assert hashed.embed_query("group relief for companies") == a
    assert math.isclose(sum(x * x for x in a), 1.0)
    assert sum(x * y for x, y in zip(a, b)) > sum(x * y for x, y in zip(a, c))


def test_one_vector_for_a_batch_raises():
    class MergingModels(FakeModels):   # gemini-embedding-2 merges a list into one input
        def embed_content(self, model, contents, config):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0])])

    with pytest.raises(ValueError, match="2 texts"):
        embedder(MergingModels()).embed_documents(["a", "b"])


def test_rate_limit_waits_as_long_as_the_error_asks():
    class QuotaModels(FakeModels):
        def embed_content(self, model, contents, config):
            if not self.calls:
                self.calls.append(model)
                message = "Quota exceeded for metric: embed_content_free_tier_requests.\nPlease retry in 829.5ms."
                raise errors.APIError(429, {"error": {"code": 429, "message": message, "status": "RESOURCE_EXHAUSTED"}})
            return super().embed_content(model, contents, config)

    sleeps = []
    embedder(QuotaModels(), sleeps).embed_query("q")
    assert sleeps == [pytest.approx(1.8295)]


def test_batches_are_paced_to_the_per_minute_quota():
    now, sleeps = [0.0], []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    paced = GeminiEmbedder(model="m", dim=2, batch_size=2, per_minute=4, client=SimpleNamespace(models=FakeModels()),
                           sleep=sleep, clock=lambda: now[0])
    paced.embed_documents(["a", "b", "c", "d", "e"])   # batches of 2, 2, 1 at 4 texts a minute
    assert sleeps == [30.0, 30.0]


def quota_error(hint: str) -> errors.APIError:
    message = f"Quota exceeded for metric: embed_content_free_tier_requests.\nPlease retry in {hint}."
    return errors.APIError(429, {"error": {"code": 429, "message": message, "status": "RESOURCE_EXHAUSTED"}})


@pytest.mark.parametrize("hint, seconds", [("829.5ms", 0.8295), ("15.49s", 15.49), ("17h5m5.5s", 61505.5)])
def test_retry_hints_are_parsed(hint, seconds):
    assert suggested_wait(quota_error(hint)) == pytest.approx(seconds)


def test_daily_quota_stops_at_once():
    class DailyQuotaModels(FakeModels):
        def embed_content(self, model, contents, config):
            raise quota_error("17h5m5.9s")

    sleeps = []
    with pytest.raises(QuotaExhausted, match="resets in 17.1 h"):
        embedder(DailyQuotaModels(), sleeps).embed_documents(["a"])
    assert sleeps == []


def test_cached_embedder_embeds_each_query_once_across_runs(tmp_path):
    from rag.embed import CachedEmbedder

    class Counting(HashEmbedder):
        calls = 0

        def embed_query(self, text):
            Counting.calls += 1
            return super().embed_query(text)

    path = tmp_path / "queries.json"
    first = CachedEmbedder(Counting(dim=8), path).embed_query("group relief")
    again = CachedEmbedder(Counting(dim=8), path)   # a later run, reading the file
    assert again.embed_query("group relief") == first and Counting.calls == 1
    assert again.name == "hash@8"
