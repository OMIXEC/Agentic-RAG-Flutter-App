import argparse
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from pinecone import Pinecone
from tqdm import tqdm

load_dotenv()


@dataclass
class AppConfig:
    pinecone_api_key: str
    pinecone_index: str
    data_folder: str
    google_api_key: str
    google_cloud_project: str
    google_cloud_location: str
    google_vertex_model: str
    google_vertex_embedding_dimension: int
    google_vertex_access_token: str
    gemini_model: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            pinecone_api_key=(
                os.getenv("PINECONE_API_KEY")
                or os.getenv("PINECONE_KEY")
                or ""
            ),
            pinecone_index=os.getenv("PINECONE_INDEX", ""),
            data_folder=os.getenv("DATA_FOLDER", "txts"),
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            google_vertex_model=os.getenv("GOOGLE_VERTEX_MODEL", "multimodalembedding@001"),
            google_vertex_embedding_dimension=int(
                os.getenv("GOOGLE_VERTEX_EMBEDDING_DIMENSION", "1408")
            ),
            google_vertex_access_token=os.getenv("GOOGLE_VERTEX_ACCESS_TOKEN", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )


CONFIG = AppConfig.from_env()


class VertexEmbeddingService:
    def __init__(self, config: AppConfig):
        self.config = config

    def _access_token(self) -> str:
        if self.config.google_vertex_access_token:
            return self.config.google_vertex_access_token

        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "Missing credentials. Set GOOGLE_VERTEX_ACCESS_TOKEN or GOOGLE_APPLICATION_CREDENTIALS."
            )

        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(Request())
        if not creds.token:
            raise ValueError("Failed to acquire Google Cloud access token.")
        return creds.token

    def embed_text(self, text: str) -> list[float]:
        if not self.config.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for Vertex embeddings.")

        url = (
            "https://"
            f"{self.config.google_cloud_location}-aiplatform.googleapis.com/v1/"
            f"projects/{self.config.google_cloud_project}/"
            f"locations/{self.config.google_cloud_location}/publishers/google/models/"
            f"{self.config.google_vertex_model}:predict"
        )

        payload = {
            "instances": [{"text": text}],
            "parameters": {"dimension": self.config.google_vertex_embedding_dimension},
        }

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        prediction = response.json()["predictions"][0]
        return prediction.get("textEmbedding", [])


class GeminiService:
    def __init__(self, config: AppConfig):
        self.config = config

    def generate_response(self, query: str, context: str) -> str:
        if not self.config.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini responses.")

        prompt = (
            f"Context: {context}\n"
            f"Question: {query}\n"
            "If the context answers the question, provide a concise answer. "
            "If not, reply exactly: I don't have enough info to answer."
        )

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.gemini_model}:generateContent?key={self.config.google_api_key}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()

        candidates = body.get("candidates", [])
        if not candidates:
            return "I don't have enough info to answer."

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                return part["text"]

        return "I don't have enough info to answer."


class DocumentChunk:
    def __init__(self, chunk_text: str, embedding_service: VertexEmbeddingService):
        self.id = self._generate_id(chunk_text)
        self.embedding = embedding_service.embed_text(chunk_text)
        self.chunk_text = chunk_text

    def _generate_id(self, content: str) -> str:
        hash_obj = hashlib.sha256()
        hash_obj.update(content.encode("utf-8"))
        return hash_obj.hexdigest()


class Document:
    def __init__(self, title: str, filename: str, content: str):
        self.title = title
        self.filename = filename
        self.content = content
        self.chunks: list[DocumentChunk] = []


def read_text_file(filename: str) -> Document:
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
        split_filename: list[str] = re.split(r"[/.]", filename)

    return Document(
        title=split_filename[len(split_filename) - 2],
        filename=filename,
        content=content,
    )


def recursive_split(paragraph: str, max_chunk_size: int) -> list[str]:
    if len(paragraph) <= max_chunk_size:
        return [paragraph]

    split_point = paragraph.find(".", len(paragraph) // 2)
    if split_point == -1:
        split_point = len(paragraph) // 2

    left = paragraph[:split_point].strip()
    right = paragraph[split_point:].strip()
    return recursive_split(left, max_chunk_size) + recursive_split(right, max_chunk_size)


def chunk_document(
    doc: Document,
    min_chunk_size: int,
    max_chunk_size: int,
    embedding_service: VertexEmbeddingService,
) -> list[DocumentChunk]:
    content = doc.content
    if not content.endswith("\n\n"):
        content += "\n\n"

    paragraphs = content.split("\n\n")
    chunks: list[DocumentChunk] = []

    for paragraph in tqdm(
        paragraphs,
        total=len(paragraphs),
        desc=f"Embedding chunks from {doc.filename}",
    ):
        normalized = paragraph.strip()
        if not normalized:
            continue

        if len(normalized) > max_chunk_size:
            split_chunks = recursive_split(normalized, max_chunk_size)
            chunks.extend(
                DocumentChunk(chunk_text=x, embedding_service=embedding_service)
                for x in split_chunks
                if len(x) >= min_chunk_size
            )
        elif len(normalized) >= min_chunk_size:
            chunks.append(
                DocumentChunk(chunk_text=normalized, embedding_service=embedding_service)
            )

    return chunks


def load_document_to_index(document: Document, config: AppConfig) -> None:
    pc = Pinecone(api_key=config.pinecone_api_key)
    index = pc.Index(config.pinecone_index)

    vectors: list[dict[str, Any]] = []
    for chunk in document.chunks:
        vectors.append(
            {
                "id": chunk.id,
                "values": chunk.embedding,
                "metadata": {
                    "title": document.title,
                    "filename": document.filename,
                    "text": chunk.chunk_text,
                },
            }
        )

    index.upsert(vectors=vectors, show_progress=True)


def load_text_files_to_documents(folder_path: str) -> list[Document]:
    data_path = Path(folder_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")

    documents = [
        read_text_file(str(file_path)) for file_path in sorted(data_path.glob("*.txt"))
    ]

    if not documents:
        raise ValueError("No .txt files found in DATA_FOLDER.")

    return documents


def load_data(config: AppConfig) -> None:
    embedding_service = VertexEmbeddingService(config)
    documents = load_text_files_to_documents(folder_path=config.data_folder)

    for document in documents:
        print(f"Loading {document.filename} into {config.pinecone_index}")
        document.chunks = chunk_document(
            document,
            min_chunk_size=40,
            max_chunk_size=500,
            embedding_service=embedding_service,
        )
        load_document_to_index(document, config)
        print(f"Loaded {document.filename}")


def query_pinecone_index(
    config: AppConfig,
    query_embeddings: list[float],
    top_k: int = 3,
    include_metadata: bool = True,
) -> dict[str, Any]:
    pc = Pinecone(api_key=config.pinecone_api_key)
    index = pc.Index(config.pinecone_index)
    return index.query(
        vector=query_embeddings,
        top_k=top_k,
        include_metadata=include_metadata,
    )


def query_data(config: AppConfig, query: str) -> None:
    embedding_service = VertexEmbeddingService(config)
    gemini_service = GeminiService(config)

    query_embedding = embedding_service.embed_text(query)
    search_results = query_pinecone_index(config=config, query_embeddings=query_embedding)

    matches = search_results.get("matches", [])
    if not matches:
        print("I don't have enough info to answer.")
        return

    context = "\n\n".join(
        match.get("metadata", {}).get("text", "") for match in matches if match
    ).strip()

    if not context:
        print("I don't have enough info to answer.")
        return

    print(gemini_service.generate_response(query=query, context=context))


def validate_config(config: AppConfig) -> None:
    missing = []
    if not config.pinecone_api_key:
        missing.append("PINECONE_API_KEY")
    if not config.pinecone_index:
        missing.append("PINECONE_INDEX")
    if not config.google_cloud_project:
        missing.append("GOOGLE_CLOUD_PROJECT")

    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG Demo v2 pipeline")
    parser.add_argument("-L", "--load", action="store_true", help="Load documents")
    parser.add_argument("-Q", "--query", type=str, help="Query documents")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_config(CONFIG)

    if args.load:
        load_data(CONFIG)
        return

    if args.query:
        query_data(CONFIG, args.query)
        return

    print("Usage: python pinecone-db.py --load | --query \"your question\"")


if __name__ == "__main__":
    main()
