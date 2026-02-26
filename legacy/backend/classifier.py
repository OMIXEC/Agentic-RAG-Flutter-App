import re
from typing import Iterable

from .schemas import MemoryType


RULES: list[tuple[MemoryType, list[str]]] = [
    ("preferences", ["prefer", "favorite", "i like", "i dislike"]),
    ("hobbies", ["hobby", "i enjoy", "i love", "weekend", "practice"]),
    ("episodic_memory", ["yesterday", "last", "trip", "met", "went", "event"]),
    ("general_knowledge", ["how to", "guide", "definition", "reference"]),
    ("life_memory", ["family", "home", "birthday", "graduation", "wedding"]),
]


def classify_with_rules(text: str, media_type: str, hint: MemoryType | None = None) -> tuple[MemoryType, float, str]:
    if hint:
        return hint, 0.99, "user_hint"

    lowered = text.lower()
    for memory_type, keywords in RULES:
        if any(token in lowered for token in keywords):
            return memory_type, 0.72, f"keyword_rule:{memory_type}"

    if media_type in {"image", "video", "audio"}:
        return "episodic_memory", 0.60, "media_default"

    return "general_knowledge", 0.55, "text_default"


def normalize_memory_types(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return [value.strip() for value in values if value.strip()]


def classify_hybrid(text: str, media_type: str, hint: MemoryType | None = None) -> tuple[MemoryType, float, str]:
    # v1: deterministic rules first. LLM adjudication hook can be layered here.
    return classify_with_rules(text=text, media_type=media_type, hint=hint)
