"""Chat models for answer generation: Groq first, Gemini as the fallback, behind one interface.

Both SDKs retry rate limits and server errors themselves; when a provider still fails,
`complete_with_fallback` moves on to the next model, so a Groq quota error doesn't take the app down.
"""

import os
from typing import Protocol

import groq
import httpx
from google.genai import errors as genai_errors
from google.genai import types

from rag.embed import MissingApiKey

GROQ_MODEL = "openai/gpt-oss-120b"     # override with GROQ_MODEL in .env
GEMINI_CHAT_MODEL = "gemini-3.8-flash"  # override with GEMINI_CHAT_MODEL in .env (2.5-flash is closed to new keys)
MAX_ANSWER_TOKENS = 2000                # includes gpt-oss reasoning tokens
PROVIDER_ERRORS = (groq.GroqError, genai_errors.APIError, httpx.HTTPError)


class ChatModel(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class LLMUnavailable(RuntimeError):
    pass


class GroqChat:
    last_finish_reason = None   # of the latest reply: "length" when it stopped at MAX_ANSWER_TOKENS

    def __init__(self, api_key: str | None = None, model: str | None = None, client=None):
        self.model = model or os.environ.get("GROQ_MODEL") or GROQ_MODEL
        if client is None:
            api_key = api_key or os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise MissingApiKey("GROQ_API_KEY is not set: add it to .env (see .env.example)")
            client = groq.Groq(api_key=api_key)
        self.client, self.name = client, f"groq:{self.model}"

    def complete(self, system: str, user: str) -> str:
        # gpt-oss reasons before answering; "medium" effort is a fair trade between answer quality and
        # the free tier's tokens-per-minute limit. The reasoning comes back separately from the content.
        extra = {"reasoning_effort": "medium"} if self.model.startswith("openai/gpt-oss") else {}
        response = self.client.chat.completions.create(
            model=self.model, temperature=0, max_completion_tokens=MAX_ANSWER_TOKENS,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **extra)
        # "length": the cap was reached, often by the reasoning alone, which leaves the content empty
        self.last_finish_reason = getattr(response.choices[0], "finish_reason", None)
        return response.choices[0].message.content or ""


class GeminiChat:
    last_finish_reason = None   # of the latest reply: MAX_TOKENS when it stopped at MAX_ANSWER_TOKENS

    def __init__(self, api_key: str | None = None, model: str | None = None, client=None):
        self.model = model or os.environ.get("GEMINI_CHAT_MODEL") or GEMINI_CHAT_MODEL
        if client is None:
            from google import genai
            api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise MissingApiKey("GEMINI_API_KEY is not set: add it to .env (see .env.example)")
            # Unlike the Groq SDK, google-genai doesn't retry by default; Gemini Flash often answers
            # 503 "high demand" for a few seconds at a time.
            retry = types.HttpRetryOptions(attempts=4, initial_delay=2, http_status_codes=[429, 500, 503, 504])
            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(retry_options=retry))
        self.client, self.name = client, f"gemini:{self.model}"

    def complete(self, system: str, user: str) -> str:
        config = types.GenerateContentConfig(system_instruction=system, temperature=0,
                                             max_output_tokens=MAX_ANSWER_TOKENS)
        response = self.client.models.generate_content(model=self.model, contents=user, config=config)
        candidates = getattr(response, "candidates", None) or []
        reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        self.last_finish_reason = getattr(reason, "name", reason)
        return response.text or ""


def default_models() -> list[ChatModel]:
    """Groq then Gemini, skipping any whose API key is missing."""
    models = []
    for make in (GroqChat, GeminiChat):
        try:
            models.append(make())
        except MissingApiKey:
            pass
    if not models:
        raise MissingApiKey("neither GROQ_API_KEY nor GEMINI_API_KEY is set: add one to .env")
    return models


def complete_with_fallback(models: list[ChatModel], system: str, user: str) -> tuple[str, str]:
    """(answer text, name of the model that gave it). Tries each model in turn on provider errors."""
    failures = []
    for model in models:
        try:
            return model.complete(system, user), model.name
        except PROVIDER_ERRORS as error:
            failures.append(f"{model.name}: {type(error).__name__}: {error}")
    raise LLMUnavailable("every model failed:\n" + "\n".join(failures))
