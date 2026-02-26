import hashlib
from collections import defaultdict
from typing import Any

from pinecone import Pinecone


class PineconeStore:
    def __init__(self, api_key: str):
        self.pc = Pinecone(api_key=api_key)

    @staticmethod
    def build_vector_id(memory_id: str, source: str, text: str, chunk_index: int) -> str:
        payload = f"{memory_id}|{source}|{chunk_index}|{text}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def upsert(
        self,
        index_name: str,
        namespace: str,
        vectors: list[dict[str, Any]],
    ) -> None:
        if not vectors:
            return
        index = self.pc.Index(index_name)
        index.upsert(vectors=vectors, namespace=namespace, show_progress=True)

    def query(
        self,
        index_name: str,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        index = self.pc.Index(index_name)
        response = index.query(
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )
        return response.get("matches", [])

    def delete_ids(self, namespace: str, by_index: dict[str, list[str]]) -> None:
        for index_name, ids in by_index.items():
            if not ids:
                continue
            index = self.pc.Index(index_name)
            index.delete(ids=ids, namespace=namespace)


def group_ids_by_index(rows: list[Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[row["index_name"]].append(row["vector_id"])
    return dict(grouped)
