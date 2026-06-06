"""OpenAI text-embedding-3-small wrapper.

Import-safe without a live API key: the client is constructed per-call.
Tests mock this module via ``monkeypatch`` or ``unittest.mock.patch``.
"""
from __future__ import annotations

import openai

from app.core.config import get_settings

settings = get_settings()


async def get_embedding(text: str) -> list[float]:
    """Return a 1536-dimensional embedding for *text* (text-embedding-3-small)."""
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key or "sk-no-key-configured")
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return list(resp.data[0].embedding)
