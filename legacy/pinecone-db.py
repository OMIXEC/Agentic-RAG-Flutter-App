import os
import runpy
import sys


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _select_multimodal_provider() -> str:
    explicit = os.getenv("MULTIMODAL_PROVIDER", "").strip().lower()
    if explicit in {"openai_clip", "vertex", "aws_nova", "legacy_multimodal", "legacy"}:
        return explicit

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
    if embedding_provider == "vertex":
        return "vertex"
    if embedding_provider in {"aws", "aws_nova", "bedrock_nova"}:
        return "aws_nova"
    if embedding_provider == "openai":
        return "openai_clip"

    # auto mode
    has_vertex_context = bool(os.getenv("GOOGLE_CLOUD_PROJECT")) and bool(
        os.getenv("GOOGLE_VERTEX_ACCESS_TOKEN") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    return "vertex" if has_vertex_context else "openai_clip"


def main() -> None:
    # Escape hatch for exact old behavior.
    if _is_truthy(os.getenv("LEGACY_TXT_ONLY", "false")):
        runpy.run_path("pinecone-legacy-rag.py", run_name="__main__")
        return

    provider = _select_multimodal_provider()
    os.environ["MULTIMODAL_PROVIDER"] = provider
    args = sys.argv[1:]
    is_query = "--query" in args or "-Q" in args or "-q" in args

    dispatch = {
        "openai_clip": ("query-openai.py" if is_query else "ingest-openai.py"),
        "vertex": ("query-vertex.py" if is_query else "ingest-vertex.py"),
        "aws_nova": ("query-aws.py" if is_query else "ingest-aws.py"),
        "legacy_multimodal": ("query-legacy.py" if is_query else "ingest-legacy.py"),
        "legacy": ("query-legacy.py" if is_query else "ingest-legacy.py"),
    }
    target = dispatch.get(provider, "pinecone-multimodal-pipeline.py")
    sys.argv = [target, *args]
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
