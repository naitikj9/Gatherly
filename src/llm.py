"""Builds the chat model and the embeddings model.

Keeping this in one file means swapping the provider later only touches here.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .config import settings

_NO_KEY = "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."


import os  # noqa: E402


def _base_url() -> str | None:
    """Optional OpenAI-compatible base URL (e.g. Emergent LLM proxy)."""
    return os.getenv("OPENAI_BASE_URL") or None


@lru_cache(maxsize=None)
def get_chat_llm(temperature: float = 0.0) -> ChatOpenAI:
    # temperature 0 keeps the agents' decisions deterministic
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(_NO_KEY)
    kwargs = dict(
        model=settings.CHAT_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        timeout=60,
        max_retries=2,
    )
    if _base_url():
        kwargs["base_url"] = _base_url()
    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=None)
def get_embeddings() -> OpenAIEmbeddings:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(_NO_KEY)
    kwargs = dict(
        model=settings.EMBED_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )
    if _base_url():
        kwargs["base_url"] = _base_url()
    return OpenAIEmbeddings(**kwargs)


# --- resilient structured calls --------------------------------------------

import random
import time

import openai

from .usage import current_tracker

# errors worth retrying: network blips, timeouts, rate limits, 5xx
_TRANSIENT = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)
_sleep = time.sleep  # swapped out in tests


class StructuredOutputError(RuntimeError):
    """The model kept returning output that didn't match the schema."""


def invoke_structured(llm, schema, messages, agent: str, attempts: int | None = None):
    """Call `llm` for a `schema` object with retries, backoff and usage tracking.

    Retries transient API errors and schema mismatches with exponential backoff
    plus jitter; anything else (bad key, bad request) fails fast. Token counts
    go to the current run's UsageTracker.
    """
    attempts = attempts or settings.LLM_MAX_ATTEMPTS
    runnable = llm.with_structured_output(schema, include_raw=True)
    tracker = current_tracker()
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            result = runnable.invoke(messages)
        except _TRANSIENT as e:
            last_error = e
        else:
            usage = getattr(result.get("raw"), "usage_metadata", None) or {}
            if tracker is not None:
                tracker.record(agent, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            if result.get("parsed") is not None and result.get("parsing_error") is None:
                return result["parsed"]
            last_error = StructuredOutputError(
                f"{agent}: model output didn't match {schema.__name__}: "
                f"{result.get('parsing_error')}"
            )
        if attempt < attempts:
            if tracker is not None:
                tracker.retries += 1
            _sleep(min(8.0, 0.5 * 2 ** (attempt - 1)) + random.uniform(0, 0.25))

    raise last_error  # type: ignore[misc]
