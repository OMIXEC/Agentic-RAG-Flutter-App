import unittest
from unittest import mock

from backend.auth import AuthUser
from backend.main import (
    create_upload_url,
    health,
    provider_search_memory,
    search_memory,
)
from backend.schemas import SearchRequest, UploadUrlRequest


class ApiTests(unittest.TestCase):
    def test_health(self):
        response = health()
        self.assertEqual(response["status"], "ok")

    def test_upload_with_user(self):
        with mock.patch("backend.main.StorageService") as storage_cls:
            storage = storage_cls.return_value
            storage.create_upload_url.return_value = mock.Mock(
                upload_url="https://upload", gcs_path="gs://bucket/user-123/a.txt", expires_in=900
            )

            result = create_upload_url(
                payload=UploadUrlRequest(filename="a.txt", content_type="text/plain"),
                user=AuthUser(user_id="user-123"),
            )

        self.assertEqual(result.gcs_path, "gs://bucket/user-123/a.txt")

    def test_search_calls_service(self):
        fake_result = {
            "memory_id": "m1",
            "score": 0.9,
            "summary": "sum",
            "media_type": "text",
            "memory_type": "general_knowledge",
            "source_uri": "gs://x",
            "title": "t",
        }
        with mock.patch("backend.main.MemoryService") as svc_cls:
            svc = svc_cls.return_value
            svc.search.return_value = [fake_result]

            response = search_memory(
                payload=SearchRequest(query="hello", top_k=5),
                user=AuthUser(user_id="user-1"),
            )

            svc.search.assert_called_once()
            kwargs = svc.search.call_args.kwargs
            self.assertEqual(kwargs["user_id"], "user-1")
            self.assertEqual(kwargs["top_k"], 5)
            self.assertEqual(len(response.results), 1)

    def test_search_passes_provider_override(self):
        with mock.patch("backend.main.MemoryService") as svc_cls:
            svc = svc_cls.return_value
            svc.search.return_value = []
            _ = search_memory(
                payload=SearchRequest(query="hello", top_k=5, provider="aws"),
                user=AuthUser(user_id="user-1"),
            )

            kwargs = svc.search.call_args.kwargs
            self.assertEqual(kwargs["provider"], "aws")

    def test_provider_search_endpoint_uses_path_provider(self):
        with mock.patch("backend.main.MemoryService") as svc_cls:
            svc = svc_cls.return_value
            svc.search.return_value = []
            _ = provider_search_memory(
                provider="vertex",
                payload=SearchRequest(query="hello", top_k=5),
                user=AuthUser(user_id="user-1"),
            )

            kwargs = svc.search.call_args.kwargs
            self.assertEqual(kwargs["provider"], "vertex")


if __name__ == "__main__":
    unittest.main()
