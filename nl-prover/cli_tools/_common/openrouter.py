"""Helpers for calling OpenRouter through the OpenAI Python SDK."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_openrouter_api_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def openrouter_client(api_key: str | None = None) -> OpenAI:
    key = api_key or get_openrouter_api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)


def normalize_model(model: str, provider: str | None = None) -> str:
    if "/" in model:
        return model
    if provider:
        return f"{provider}/{model}"
    return model


def extract_response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            chunk = getattr(content, "text", None)
            if chunk:
                parts.append(chunk)
    return "".join(parts)
