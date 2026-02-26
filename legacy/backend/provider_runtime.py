import importlib.util
import tempfile
from pathlib import Path
from typing import Any

from providers.router import canonical_provider_name


def _load_pipeline_module():
    path = Path(__file__).resolve().parents[1] / "pinecone-multimodal-pipeline.py"
    spec = importlib.util.spec_from_file_location("multimodal_pipeline_runtime", path)
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load multimodal pipeline module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProviderRuntime:
    def __init__(self, provider_name: str):
        self.mm = _load_pipeline_module()
        canonical = canonical_provider_name(provider_name, default="openai")
        self.config = self.mm.PipelineConfig.from_env(provider_override=canonical)
        self.provider = self.mm._build_provider(self.config)
        self.provider.validate()

    @property
    def provider_name(self) -> str:
        return self.config.provider

    @property
    def text_index(self) -> str:
        return self.provider.text_index()

    @property
    def media_index(self) -> str:
        return self.provider.media_index()

    def query_targets(self, query: str) -> list[Any]:
        return self.provider.build_query_targets(query)

    def build_text_targets(self, text: str, source_name: str, kind: str) -> list[Any]:
        source = Path(source_name)
        targets = []
        for chunk in self.mm._chunk_text(text):
            targets.extend(self.provider.build_text_targets(chunk, source, kind))
        return targets

    def build_image_targets(self, file_bytes: bytes, suffix: str, description: str, source_url: str) -> list[Any]:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            return self.provider.build_image_targets(Path(tmp.name), description, source_url)

    def build_video_targets(self, file_bytes: bytes, suffix: str, description: str) -> list[Any]:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            return self.provider.build_video_targets(Path(tmp.name), description)

    def build_audio_targets(self, file_bytes: bytes, suffix: str) -> list[Any]:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            return self.provider.build_audio_targets(Path(tmp.name))
