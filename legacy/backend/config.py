from dataclasses import dataclass
import os


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key)
    return value if value else default


@dataclass(frozen=True)
class Settings:
    api_title: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_audience: str
    jwt_issuer: str

    pinecone_api_key: str
    pinecone_index: str
    pinecone_text_index: str
    pinecone_media_index: str

    multimodal_provider: str

    openai_api_key: str
    openai_chat_model: str
    gemini_api_key: str
    gemini_model: str

    gcs_bucket: str
    local_storage_root: str

    db_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        pinecone_index = _env("PINECONE_INDEX")
        pinecone_text = _env("PINECONE_TEXT_INDEX", pinecone_index)
        pinecone_media = _env("PINECONE_MEDIA_INDEX", pinecone_text)
        return cls(
            api_title=_env("API_TITLE", "Search Memory API"),
            jwt_secret=_env("JWT_SECRET", "dev-secret-change-me"),
            jwt_algorithm=_env("JWT_ALGORITHM", "HS256"),
            jwt_audience=_env("JWT_AUDIENCE", "search-memory"),
            jwt_issuer=_env("JWT_ISSUER", "search-memory-backend"),
            pinecone_api_key=_env("PINECONE_API_KEY"),
            pinecone_index=pinecone_index,
            pinecone_text_index=pinecone_text,
            pinecone_media_index=pinecone_media,
            multimodal_provider=_env("MULTIMODAL_PROVIDER", "vertex"),
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_chat_model=_env("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
            gemini_api_key=_env("GOOGLE_API_KEY"),
            gemini_model=_env("GEMINI_MODEL", "gemini-2.5-flash"),
            gcs_bucket=_env("GCS_BUCKET", _env("VERTEX_VIDEO_GCS_BUCKET")),
            local_storage_root=_env("LOCAL_STORAGE_ROOT", "local_uploads"),
            db_path=_env("MEMORY_DB_PATH", "search_memory.db"),
        )


settings = Settings.from_env()
