import unittest
from unittest import mock

from backend.service import MemoryService
from backend.schemas import IngestRequest


class ServiceTests(unittest.TestCase):
    def test_ingest_text_upserts_and_persists(self):
        service = MemoryService.__new__(MemoryService)
        service.runtime = mock.Mock()
        service.runtime.provider_name = "openai_clip"
        service.route = mock.Mock(expected_text_dim=3072, expected_media_dim=512)
        service.runtime.build_text_targets.return_value = [
            mock.Mock(
                index_name="idx-text",
                vector=[0.1] * 3072,
                metadata={"text": "chunk one", "modality": "text"},
            )
        ]
        service.storage = mock.Mock()
        service.storage.read_bytes.return_value = b"hello world text payload"
        service.pinecone = mock.Mock()
        service.pinecone.build_vector_id.return_value = "vec-1"

        payload = IngestRequest(
            gcs_path="gs://bucket/u1/note.txt",
            media_type="text",
            notes="note summary",
            title="Note",
            tags=["personal"],
        )

        with mock.patch("backend.service.classify_hybrid", return_value=("life_memory", 0.9, "rule")):
            with mock.patch("backend.service.validate_dim") as validate_dim:
                with mock.patch("backend.service.db.insert_vectors") as insert_vectors:
                    with mock.patch("backend.service.db.insert_memory") as insert_memory:
                        memory_id, memory_type, chunks, provider = service.ingest("u1", payload)

        self.assertTrue(memory_id)
        self.assertEqual(memory_type, "life_memory")
        self.assertEqual(chunks, 1)
        self.assertEqual(provider, "openai_clip")
        service.pinecone.upsert.assert_called_once()
        upsert_kwargs = service.pinecone.upsert.call_args.kwargs
        self.assertEqual(upsert_kwargs["index_name"], "idx-text")
        self.assertEqual(upsert_kwargs["namespace"], "u1")
        validate_dim.assert_called_once()
        insert_vectors.assert_called_once()
        insert_memory.assert_called_once()

    def test_ingest_raises_when_no_embeddings(self):
        service = MemoryService.__new__(MemoryService)
        service.runtime = mock.Mock()
        service.runtime.build_audio_targets.return_value = []
        service.storage = mock.Mock()
        service.storage.read_bytes.return_value = b"fake audio"
        service.pinecone = mock.Mock()

        payload = IngestRequest(
            gcs_path="gs://bucket/u1/audio.wav",
            media_type="audio",
        )

        with self.assertRaises(ValueError):
            service.ingest("u1", payload)

    def test_search_builds_namespace_filter(self):
        service = MemoryService.__new__(MemoryService)
        service.runtime = mock.Mock()
        service.runtime.query_targets.return_value = [
            mock.Mock(index_name="idx", vector=[0.1, 0.2]),
        ]
        service.pinecone = mock.Mock()
        service.pinecone.query.return_value = [
            {
                "score": 0.8,
                "metadata": {
                    "memory_id": "m1",
                    "summary": "hello",
                    "media_type": "text",
                    "memory_type": "preferences",
                    "source_uri": "gs://a",
                    "title": "A",
                },
            }
        ]

        with mock.patch("backend.service.db.increment_retrieval") as inc:
            results = service.search(
                user_id="u1",
                query="q",
                top_k=5,
                memory_types=["preferences"],
                media_types=["text"],
            )

        self.assertEqual(len(results), 1)
        service.pinecone.query.assert_called_once()
        kwargs = service.pinecone.query.call_args.kwargs
        self.assertEqual(kwargs["namespace"], "u1")
        self.assertIn("$and", kwargs["metadata_filter"])
        inc.assert_called_once_with(["m1"])

    def test_search_merges_multi_target_results(self):
        service = MemoryService.__new__(MemoryService)
        service.runtime = mock.Mock()
        service.runtime.query_targets.return_value = [
            mock.Mock(index_name="idx-text", vector=[0.1] * 4, label="text"),
            mock.Mock(index_name="idx-media", vector=[0.2] * 4, label="media"),
        ]
        service.pinecone = mock.Mock()
        service.pinecone.query.side_effect = [
            [
                {
                    "score": 0.8,
                    "metadata": {
                        "memory_id": "m1",
                        "summary": "from text",
                        "media_type": "text",
                        "memory_type": "preferences",
                        "source_uri": "gs://x/t",
                        "title": "T",
                    },
                }
            ],
            [
                {
                    "score": 0.7,
                    "metadata": {
                        "memory_id": "m1",
                        "summary": "from media",
                        "media_type": "image",
                        "memory_type": "preferences",
                        "source_uri": "gs://x/i",
                        "title": "I",
                    },
                }
            ],
        ]

        with mock.patch("backend.service.db.increment_retrieval") as inc:
            results = service.search(
                user_id="u1",
                query="q",
                top_k=3,
                memory_types=None,
                media_types=None,
            )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].memory_id, "m1")
        self.assertEqual(service.pinecone.query.call_count, 2)
        inc.assert_called_once()

    def test_search_uses_provider_override_runtime(self):
        service = MemoryService.__new__(MemoryService)
        service.runtime = mock.Mock()
        service.runtime.provider_name = "openai_clip"
        service._runtime_cache = {"openai_clip": service.runtime}

        aws_runtime = mock.Mock()
        aws_runtime.query_targets.return_value = [
            mock.Mock(index_name="idx-aws", vector=[0.3, 0.4], label="aws_nova"),
        ]
        service._runtime_cache["aws_nova"] = aws_runtime
        service.route = mock.Mock(expected_text_dim=3072, expected_media_dim=512)
        service.pinecone = mock.Mock()
        service.pinecone.query.return_value = []

        with mock.patch("backend.service.db.increment_retrieval"):
            _ = service.search(
                user_id="u1",
                query="q",
                top_k=5,
                memory_types=None,
                media_types=None,
                provider="aws",
            )

        aws_runtime.query_targets.assert_called_once_with("q")


if __name__ == "__main__":
    unittest.main()
