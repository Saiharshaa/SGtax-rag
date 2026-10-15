from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from rag.embed import MissingApiKey
from rag.llm import GeminiChat, GroqChat, LLMUnavailable, complete_with_fallback, default_models


class FakeGroqCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = SimpleNamespace(content="answer [1]", reasoning="thinking")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeGeminiModels:
    def __init__(self):
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text="answer [1]")


class Failing:
    def __init__(self, name: str, error: Exception):
        self.name, self.error = name, error

    def complete(self, system, user):
        raise self.error


class Working:
    name = "working:model"

    def complete(self, system, user):
        return f"{system}|{user}"


def rate_limited() -> genai_errors.APIError:
    return genai_errors.APIError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})


def test_groq_sends_system_and_user_messages_deterministically():
    completions = FakeGroqCompletions()
    chat = GroqChat(model="openai/gpt-oss-120b", client=SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    assert chat.complete("rules", "question") == "answer [1]"
    assert completions.kwargs["messages"] == [{"role": "system", "content": "rules"},
                                              {"role": "user", "content": "question"}]
    assert completions.kwargs["temperature"] == 0
    assert completions.kwargs["reasoning_effort"] == "medium"
    assert chat.name == "groq:openai/gpt-oss-120b"


def test_reasoning_effort_only_for_reasoning_models():
    completions = FakeGroqCompletions()
    GroqChat(model="qwen/qwen3.8-27b", client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
             ).complete("rules", "question")
    assert "reasoning_effort" not in completions.kwargs


def test_gemini_puts_rules_in_the_system_instruction():
    models = FakeGeminiModels()
    chat = GeminiChat(model="gemini-x", client=SimpleNamespace(models=models))
    assert chat.complete("rules", "question") == "answer [1]"
    assert models.kwargs["contents"] == "question"
    assert models.kwargs["config"].system_instruction == "rules"
    assert models.kwargs["config"].temperature == 0


def test_fallback_uses_the_next_model_on_provider_errors():
    text, name = complete_with_fallback([Failing("groq:x", rate_limited()), Working()], "s", "u")
    assert (text, name) == ("s|u", "working:model")


def test_all_models_failing_is_reported():
    with pytest.raises(LLMUnavailable, match="groq:x"):
        complete_with_fallback([Failing("groq:x", rate_limited())], "s", "u")


def test_programming_errors_are_not_swallowed():
    with pytest.raises(KeyError):
        complete_with_fallback([Failing("groq:x", KeyError("bug")), Working()], "s", "u")


def test_default_models_skip_missing_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert [model.name.split(":")[0] for model in default_models()] == ["gemini"]
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(MissingApiKey):
        default_models()
