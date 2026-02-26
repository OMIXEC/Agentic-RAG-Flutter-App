"""LLM synthesis layer — Gemini, OpenAI, and Azure OpenAI.

Supports both blocking and streaming (SSE) responses.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI

from synapsememo.config import Settings, get_settings


SYSTEM_PROMPT = (
    "You are SynapseMemo, a personal life-memory recall assistant.  "
    "You answer questions using ONLY the retrieved memory context provided.  "
    "When citing memories, reference the memory title.  "
    "If no relevant context is found, say so honestly.  "
    "Be concise and helpful."
)


async def synthesize_answer(
    prompt: str,
    settings: Settings | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """Generate a non-streaming answer using the best available LLM."""
    settings = settings or get_settings()

    # Try Azure OpenAI first
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        result = await _azure_openai_answer(prompt, settings, system_prompt)
        if result:
            return result

    # Try Gemini
    if settings.google_api_key:
        result = await _gemini_answer(prompt, settings)
        if result:
            return result

    # Try OpenAI
    if settings.openai_api_key:
        result = await _openai_answer(prompt, settings, system_prompt)
        if result:
            return result

    return "I don't have enough information to answer."


async def synthesize_stream(
    prompt: str,
    settings: Settings | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> AsyncIterator[str]:
    """Stream answer chunks via the best available LLM.

    Yields text chunks suitable for SSE streaming.
    """
    settings = settings or get_settings()

    # Prefer Azure OpenAI for streaming
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        async for chunk in _azure_openai_stream(prompt, settings, system_prompt):
            yield chunk
        return

    # Then OpenAI
    if settings.openai_api_key:
        async for chunk in _openai_stream(prompt, settings, system_prompt):
            yield chunk
        return

    # Gemini fallback (non-streaming, yield all at once)
    if settings.google_api_key:
        result = await _gemini_answer(prompt, settings)
        yield result or "I don't have enough information to answer."
        return

    yield "I don't have enough information to answer."


# ── Azure OpenAI ────────────────────────────────────────────────────────

async def _azure_openai_answer(
    prompt: str, settings: Settings, system_prompt: str
) -> str | None:
    try:
        client = AsyncOpenAI(
            api_key=settings.azure_openai_api_key,
            base_url=f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_chat_deployment or settings.azure_openai_deployment_name}",
            default_headers={"api-key": settings.azure_openai_api_key},
            default_query={"api-version": settings.azure_openai_api_version},
        )
        response = await client.chat.completions.create(
            model=settings.azure_openai_chat_deployment or settings.azure_openai_deployment_name,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return None


async def _azure_openai_stream(
    prompt: str, settings: Settings, system_prompt: str
) -> AsyncIterator[str]:
    try:
        client = AsyncOpenAI(
            api_key=settings.azure_openai_api_key,
            base_url=f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_chat_deployment or settings.azure_openai_deployment_name}",
            default_headers={"api-key": settings.azure_openai_api_key},
            default_query={"api-version": settings.azure_openai_api_version},
        )
        stream = await client.chat.completions.create(
            model=settings.azure_openai_chat_deployment or settings.azure_openai_deployment_name,
            temperature=0.2,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except Exception:
        yield "Error: Azure OpenAI streaming failed."


# ── Gemini ──────────────────────────────────────────────────────────────

async def _gemini_answer(prompt: str, settings: Settings) -> str | None:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.google_api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=body)
        if response.is_success:
            payload = response.json()
            candidates = payload.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    text = part.get("text")
                    if text:
                        return text
    return None


# ── OpenAI ──────────────────────────────────────────────────────────────

async def _openai_answer(
    prompt: str, settings: Settings, system_prompt: str
) -> str | None:
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return None


async def _openai_stream(
    prompt: str, settings: Settings, system_prompt: str
) -> AsyncIterator[str]:
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        stream = await client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.2,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except Exception:
        yield "Error: OpenAI streaming failed."
