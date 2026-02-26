from pathlib import Path
from typing import Literal

CanonicalProvider = Literal["openai_clip", "aws_nova", "vertex", "legacy_multimodal"]
ProviderMode = Literal["ingest", "query"]

_ALIAS_TO_CANONICAL: dict[str, CanonicalProvider] = {
    "openai": "openai_clip",
    "openai_clip": "openai_clip",
    "aws": "aws_nova",
    "aws_nova": "aws_nova",
    "bedrock_nova": "aws_nova",
    "vertex": "vertex",
    "gcp_vertex": "vertex",
    "gcp": "vertex",
    "legacy": "legacy_multimodal",
    "legacy_multimodal": "legacy_multimodal",
}

_FOLDER_BY_PROVIDER: dict[CanonicalProvider, str] = {
    "openai_clip": "pinecone-openai",
    "aws_nova": "pinecone-aws",
    "vertex": "pinecone-gcp-vertex",
    "legacy_multimodal": "pinecone-openai",
}


def canonical_provider_name(value: str | None, default: str | None = None) -> CanonicalProvider:
    raw = (value or default or "").strip().lower()
    if not raw:
        raise ValueError("Provider name is required")
    canonical = _ALIAS_TO_CANONICAL.get(raw)
    if not canonical:
        allowed = ", ".join(sorted(_ALIAS_TO_CANONICAL.keys()))
        raise ValueError(f"Unsupported provider '{raw}'. Allowed: {allowed}")
    return canonical


def provider_entrypoint_path(provider: str, mode: ProviderMode) -> Path:
    canonical = canonical_provider_name(provider)
    folder = _FOLDER_BY_PROVIDER[canonical]
    filename = "entry_ingest.py" if mode == "ingest" else "entry_query.py"
    root = Path(__file__).resolve().parents[1]
    return root / "providers" / folder / filename
