"""Hybrid memory classifier.

v1: deterministic keyword rules (fast).
v2 hook: LLM adjudication for ambiguous cases (< 0.7 confidence).
"""

from __future__ import annotations

import re
from typing import Iterable

from synapsememo.models.schemas import MemoryType


RULES: list[tuple[MemoryType, list[str]]] = [
    ("preferences", ["prefer", "favorite", "i like", "i dislike", "love to"]),
    ("hobbies", ["hobby", "i enjoy", "weekend", "practice", "free time"]),
    ("episodic_memory", ["yesterday", "last", "trip", "met", "went", "event", "today"]),
    ("general_knowledge", ["how to", "guide", "definition", "reference", "explain"]),
    ("life_memory", ["family", "home", "birthday", "graduation", "wedding", "childhood"]),
]


def classify_with_rules(
    text: str,
    media_type: str,
    hint: MemoryType | None = None,
) -> tuple[MemoryType, float, str]:
    """Rule-based classification — fast path."""
    if hint:
        return hint, 0.99, "user_hint"

    lowered = text.lower()
    for memory_type, keywords in RULES:
        if any(token in lowered for token in keywords):
            return memory_type, 0.72, f"keyword_rule:{memory_type}"

    if media_type in {"image", "video", "audio"}:
        return "episodic_memory", 0.60, "media_default"

    return "general_knowledge", 0.55, "text_default"


def classify_hybrid(
    text: str,
    media_type: str,
    hint: MemoryType | None = None,
) -> tuple[MemoryType, float, str]:
    """Classify memory type using rules + optional LLM adjudication.

    Currently delegates to rule-based only.  The LLM hook can be layered
    here for cases where confidence < 0.7.
    """
    return classify_with_rules(text=text, media_type=media_type, hint=hint)


def normalize_memory_types(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return [v.strip() for v in values if v.strip()]
