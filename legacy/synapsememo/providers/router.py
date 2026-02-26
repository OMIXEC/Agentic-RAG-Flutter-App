"""Provider name resolution — canonical provider mapping.

Unifies all the alias variants (e.g. "aws" → "aws_nova", "azure" → "azure_openai")
so every other module can use a single canonical string.
"""

from __future__ import annotations


_ALIASES: dict[str, str] = {
    "openai": "openai",
    "openai_clip": "openai_clip",
    "azure": "azure_openai",
    "azure_openai": "azure_openai",
    "aws": "aws_nova",
    "aws_nova": "aws_nova",
    "bedrock_nova": "aws_nova",
    "vertex": "vertex",
    "gcp_vertex": "vertex",
    "legacy": "legacy_multimodal",
    "legacy_multimodal": "legacy_multimodal",
}


def canonical_provider_name(raw: str | None, default: str = "openai") -> str:
    """Resolve a user-supplied provider name to its canonical form."""
    if not raw:
        return _ALIASES.get(default, default)
    return _ALIASES.get(raw.lower().strip(), raw.lower().strip())


ALL_PROVIDERS = sorted(set(_ALIASES.values()))
