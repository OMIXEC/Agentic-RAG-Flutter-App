import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "pinecone-multimodal-pipeline.py"
spec = importlib.util.spec_from_file_location("multimodal_pipeline", MODULE_PATH)
mm = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mm)


class _FakeResponse:
    def __init__(self, ok, status_code, payload=None, text=""):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _FakeClip:
    def encode(self, items, normalize_embeddings=True):
        if len(items) == 0:
            return []
        return [[0.2] * 512]


def _cfg(provider: str) -> object:
    env = {
        "MULTIMODAL_PROVIDER": provider,
        "PINECONE_API_KEY": "pc",
        "PINECONE_INDEX": "idx-generic",
        "PINECONE_INDEX_VERTEX_1408": "idx-vertex",
        "PINECONE_INDEX_OPENAI_TEXT_3072": "idx-openai-text",
        "PINECONE_INDEX_OPENAI_CLIP_512": "idx-openai-clip",
        "PINECONE_INDEX_AWS_NOVA_1024": "idx-aws",
        "PINECONE_INDEX_LEGACY_TEXT": "idx-legacy-text",
        "PINECONE_INDEX_LEGACY_MEDIA": "idx-legacy-media",
        "PINECONE_NAMESPACE": "ns-test",
        "OPENAI_API_KEY": "sk-test",
        "OPENAI_TEXT_EMBEDDING_DIMENSION": "3072",
        "OPENAI_CLIP_EMBEDDING_DIMENSION": "512",
        "GOOGLE_CLOUD_PROJECT": "project",
        "GOOGLE_VERTEX_ACCESS_TOKEN": "token",
        "GOOGLE_VERTEX_EXPECTED_DIMENSION": "1408",
        "AWS_REGION": "us-east-1",
        "AWS_NOVA_EXPECTED_DIMENSION": "1024",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        return mm.PipelineConfig.from_env()


class MultimodalPipelineTests(unittest.TestCase):
    def test_openai_provider_load_and_query_targets(self):
        cfg = _cfg("openai_clip")
        provider = mm.OpenAIClipProvider(cfg)

        with mock.patch.object(
            provider, "_embed_text_openai", return_value=[0.1] * 3072
        ):
            with mock.patch.object(
                provider, "_embed_image_clip", return_value=[0.2] * 512
            ):
                with mock.patch.object(
                    provider, "_embed_video_clip", return_value=[0.2] * 512
                ):
                    with mock.patch.object(
                        provider, "_clip_model", return_value=_FakeClip()
                    ):
                        text_targets = provider.build_text_targets(
                            "hello memory", Path("a.txt"), kind="text"
                        )
                        image_targets = provider.build_image_targets(
                            Path("a.jpg"), "desc", ""
                        )
                        query_targets = provider.build_query_targets("find memory")

        self.assertEqual(text_targets[0].index_name, "idx-openai-text")
        self.assertEqual(len(text_targets[0].vector), 3072)
        self.assertEqual(image_targets[0].index_name, "idx-openai-clip")
        self.assertEqual(len(image_targets[0].vector), 512)
        self.assertEqual(len(query_targets), 2)

    def test_openai_text_embedding_uses_3072_for_text_embedding_3_large(self):
        cfg = _cfg("openai_clip")
        provider = mm.OpenAIClipProvider(cfg)

        fake_resp = mock.Mock()
        fake_item = mock.Mock()
        fake_item.embedding = [0.1] * 3072
        fake_resp.data = [fake_item]

        with mock.patch.object(
            provider.openai.embeddings, "create", return_value=fake_resp
        ) as create_mock:
            vector = provider._embed_text_openai("hello")

        self.assertEqual(len(vector), 3072)
        self.assertEqual(create_mock.call_args.kwargs.get("dimensions"), 3072)

    def test_validate_common_rejects_non_3072_for_text_embedding_3_large(self):
        cfg = _cfg("openai_clip")
        with mock.patch.dict(
            os.environ, {"OPENAI_TEXT_EMBEDDING_DIMENSION": "1024"}, clear=False
        ):
            with self.assertRaises(ValueError):
                mm.validate_common(cfg)

    def test_vertex_provider_load_and_query_targets(self):
        cfg = _cfg("vertex")
        provider = mm.VertexProvider(cfg)

        with mock.patch.object(provider, "_embed_text", return_value=[0.2] * 1408):
            text_targets = provider.build_text_targets(
                "hello", Path("v.txt"), kind="text"
            )
            query_targets = provider.build_query_targets("q")

        self.assertEqual(text_targets[0].index_name, "idx-vertex")
        self.assertEqual(len(text_targets[0].vector), 1408)
        self.assertEqual(query_targets[0].index_name, "idx-vertex")

    def test_vertex_provider_splits_long_text_for_load(self):
        cfg = _cfg("vertex")
        provider = mm.VertexProvider(cfg)
        long_text = "x" * 1500
        calls: list[str] = []

        def _fake_embed(text: str):
            calls.append(text)
            return [0.2] * 1408

        with mock.patch.object(provider, "_embed_text", side_effect=_fake_embed):
            targets = provider.build_text_targets(
                long_text, Path("long.txt"), kind="text"
            )

        self.assertGreater(len(targets), 1)
        self.assertEqual(len(calls), len(targets))
        self.assertTrue(all(len(value) <= 1000 for value in calls))

    def test_vertex_provider_limits_query_text(self):
        cfg = _cfg("vertex")
        provider = mm.VertexProvider(cfg)
        long_query = "q" * 5000
        calls: list[str] = []

        def _fake_embed(text: str):
            calls.append(text)
            return [0.2] * 1408

        with mock.patch.object(provider, "_embed_text", side_effect=_fake_embed):
            provider.build_query_targets(long_query)

        self.assertEqual(len(calls), 1)
        self.assertLessEqual(len(calls[0]), 1000)

    def test_aws_provider_load_and_query_targets(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with mock.patch.object(provider, "_embed_text", return_value=[0.3] * 1024):
            text_targets = provider.build_text_targets(
                "hello", Path("a.txt"), kind="text"
            )
            query_targets = provider.build_query_targets("q")

        self.assertEqual(text_targets[0].index_name, "idx-aws")
        self.assertEqual(len(text_targets[0].vector), 1024)
        self.assertEqual(query_targets[0].index_name, "idx-aws")

    def test_aws_nova_image_embed_returns_1024d_target(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG header
            img_path = Path(f.name)

        try:
            with mock.patch.object(provider, "_embed_image", return_value=[0.5] * 1024):
                targets = provider.build_image_targets(
                    img_path, "a photo", "http://example.com"
                )
        finally:
            img_path.unlink(missing_ok=True)

        self.assertEqual(len(targets), 1)
        self.assertEqual(len(targets[0].vector), 1024)
        self.assertEqual(targets[0].metadata["modality"], "image")
        self.assertEqual(targets[0].metadata["media_type"], "image")

    def test_aws_nova_video_embed_returns_1024d_target(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"\x00" * 100)
            vid_path = Path(f.name)

        try:
            with mock.patch.object(provider, "_embed_video", return_value=[0.4] * 1024):
                targets = provider.build_video_targets(vid_path, "a short video")
        finally:
            vid_path.unlink(missing_ok=True)

        self.assertEqual(len(targets), 1)
        self.assertEqual(len(targets[0].vector), 1024)
        self.assertEqual(targets[0].metadata["modality"], "video")

    def test_aws_nova_audio_native_embed_skips_transcript(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * 100)
            audio_path = Path(f.name)

        try:
            with mock.patch.object(provider, "_embed_audio", return_value=[0.6] * 1024):
                with mock.patch.object(
                    provider, "_transcribe_fallback"
                ) as mock_transcribe:
                    targets = provider.build_audio_targets(audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

        self.assertEqual(len(targets), 1)
        self.assertEqual(len(targets[0].vector), 1024)
        self.assertEqual(targets[0].metadata["modality"], "audio")
        mock_transcribe.assert_not_called()  # native embed succeeded, no transcription needed

    def test_aws_nova_audio_fallback_uses_chunk_config(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * 100)
            audio_path = Path(f.name)

        # Use a long enough transcript to exceed min_chars (80) so chunking produces output
        long_transcript = "This is a detailed audio transcript containing enough text to exceed the minimum chunk character threshold for testing purposes."
        # Force native embed to fail → trigger fallback transcript path
        with mock.patch.object(provider, "_embed_audio", return_value=[]):
            with mock.patch.object(
                provider, "_transcribe_fallback", return_value=long_transcript
            ):
                with mock.patch.object(
                    provider, "_embed_text", return_value=[0.3] * 1024
                ):
                    with mock.patch.object(
                        mm,
                        "chunk_text_with_strategy",
                        wraps=mm.chunk_text_with_strategy,
                    ) as mock_chunk:
                        try:
                            targets = provider.build_audio_targets(audio_path)
                        finally:
                            audio_path.unlink(missing_ok=True)

        # chunk_text_with_strategy must be called with the config values (not hardcoded)
        mock_chunk.assert_called_once()
        call_args = mock_chunk.call_args
        self.assertEqual(call_args.args[1], cfg.chunk_strategy)
        self.assertEqual(call_args.args[2], cfg.chunk_max_chars)
        self.assertTrue(len(targets) > 0)
        self.assertEqual(targets[0].metadata["modality"], "audio")

    def test_aws_nova_video_size_guard_returns_empty_for_large_file(self):
        cfg = _cfg("aws_nova")
        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"\x00" * 100)
            vid_path = Path(f.name)

        try:
            # Simulate a 30MB file (over the 20MB default).
            # Must patch at class level since PosixPath instances are read-only.
            mock_stat = mock.Mock()
            mock_stat.st_size = 30 * 1024 * 1024
            with mock.patch.object(Path, "stat", return_value=mock_stat):
                targets = provider.build_video_targets(vid_path, "big video")
        finally:
            vid_path.unlink(missing_ok=True)

        self.assertEqual(targets, [])  # size guard → build_video_targets returns []

    def test_legacy_provider_routes_to_legacy_indexes(self):
        cfg = _cfg("legacy_multimodal")
        provider = mm._build_provider(cfg)
        self.assertEqual(provider.__class__.__name__, "LegacyMultimodalProvider")
        self.assertEqual(provider.text_index(), "idx-legacy-text")
        self.assertEqual(provider.media_index(), "idx-legacy-media")

    def test_vertex_predict_fallback_payload(self):
        cfg = _cfg("vertex")
        provider = mm.VertexProvider(cfg)

        responses = [
            _FakeResponse(ok=False, status_code=400, text="bad payload"),
            _FakeResponse(
                ok=True,
                status_code=200,
                payload={"predictions": [{"textEmbedding": [0.1, 0.2]}]},
            ),
        ]

        with mock.patch.object(provider, "_access_token", return_value="token"):
            with mock.patch("requests.post", side_effect=responses):
                body = provider._predict({"text": "hello"})

        self.assertIn("predictions", body)

    def test_dimension_guard_raises_before_upsert(self):
        cfg = _cfg("openai_clip")
        vectors = [{"id": "1", "values": [0.1] * 3072, "metadata": {}}]

        with self.assertRaises(ValueError):
            mm._upsert(
                index_name="idx-vertex",
                vectors=vectors,
                pinecone_api_key="pc",
                namespace="ns",
                expected_dim=1408,
                config=cfg,
            )

    def test_openai_expected_dim_with_shared_index_name(self):
        cfg = _cfg("openai_clip")
        cfg.pinecone_index_openai_text_3072 = "multimodal-embedding-demo"
        cfg.pinecone_index_openai_clip_512 = "multimodal-embedding-demo"
        cfg.pinecone_index_vertex_1408 = "multimodal-embedding-demo"
        expected = mm._expected_dim_for_index(cfg, "multimodal-embedding-demo")
        self.assertEqual(expected, 3072)

    def test_validate_common_rejects_openai_vertex_same_index_with_dim_mismatch(self):
        cfg = _cfg("openai_clip")
        cfg.pinecone_index_openai_text_3072 = "shared-index"
        cfg.pinecone_index_vertex_1408 = "shared-index"
        with self.assertRaises(ValueError):
            mm.validate_common(cfg)

    def test_validate_common_rejects_openai_text_media_shared_index(self):
        cfg = _cfg("openai_clip")
        cfg.pinecone_index_openai_text_3072 = "shared-openai-index"
        cfg.pinecone_index_openai_clip_512 = "shared-openai-index"
        with self.assertRaises(ValueError):
            mm.validate_common(cfg)

    def test_preflight_detects_dimension_mismatch(self):
        cfg = _cfg("openai_clip")
        provider = mm.OpenAIClipProvider(cfg)

        class _Info:
            def __init__(self, dim):
                self.dimension = dim

        fake_pc = mock.Mock()
        fake_pc.describe_index.side_effect = [_Info(1024), _Info(512)]

        with mock.patch.object(mm, "Pinecone", return_value=fake_pc):
            with self.assertRaises(RuntimeError):
                mm._preflight_pinecone_indexes(cfg, provider)

    def test_index_client_prefers_host_when_configured(self):
        cfg = _cfg("openai_clip")
        cfg.pinecone_index_openai_text_3072 = "idx-openai-text"
        cfg.pinecone_index_host_openai_text_3072 = (
            "idx-openai-text-abc.svc.us-east1-gcp.pinecone.io"
        )
        pc = mock.Mock()
        mm._index_client(pc, cfg, "idx-openai-text")
        pc.Index.assert_called_once_with(
            host="idx-openai-text-abc.svc.us-east1-gcp.pinecone.io"
        )

    def test_load_all_dispatches_all_modalities(self):
        cfg = _cfg("openai_clip")

        class FakeProvider(mm.BaseProvider):
            def validate(self):
                return None

            def text_index(self):
                return "idx-openai-text"

            def media_index(self):
                return "idx-openai-clip"

            def build_text_targets(self, chunk, source_file, kind):
                return [
                    mm.IndexTarget(
                        "idx-openai-text",
                        [0.1] * 3072,
                        {"filename": str(source_file), "modality": kind, "text": chunk},
                    )
                ]

            def build_image_targets(self, file_path, description, source_url):
                return [
                    mm.IndexTarget(
                        "idx-openai-clip",
                        [0.2] * 512,
                        {
                            "filename": str(file_path),
                            "modality": "image",
                            "text": description,
                        },
                    )
                ]

            def build_video_targets(self, file_path, description):
                return [
                    mm.IndexTarget(
                        "idx-openai-clip",
                        [0.2] * 512,
                        {
                            "filename": str(file_path),
                            "modality": "video",
                            "text": description,
                        },
                    )
                ]

            def build_audio_targets(self, file_path):
                return [
                    mm.IndexTarget(
                        "idx-openai-text",
                        [0.1] * 3072,
                        {
                            "filename": str(file_path),
                            "modality": "audio",
                            "text": "audio",
                        },
                    )
                ]

            def build_query_targets(self, query):
                return []

        provider = FakeProvider(cfg)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            text_dir = root / "txt"
            image_dir = root / "image"
            video_dir = root / "video"
            audio_dir = root / "audio"
            for folder in (text_dir, image_dir, video_dir, audio_dir):
                folder.mkdir(parents=True, exist_ok=True)

            (text_dir / "a.txt").write_text(
                "This is a text file with enough content." * 3, encoding="utf-8"
            )
            (text_dir / "b.pdf").write_text("fake pdf content", encoding="utf-8")
            (image_dir / "img.png").write_text("img", encoding="utf-8")
            (video_dir / "vid.mp4").write_text("vid", encoding="utf-8")
            (audio_dir / "aud.mp3").write_text("aud", encoding="utf-8")

            cfg.text_folder = text_dir
            cfg.image_folder = image_dir
            cfg.video_folder = video_dir
            cfg.audio_folder = audio_dir

            upserts = []
            with mock.patch.object(
                mm,
                "_extract_document_text",
                return_value="Document text with enough body. " * 4,
            ):
                with mock.patch.object(
                    mm,
                    "_upsert",
                    side_effect=lambda index_name,
                    vectors,
                    pinecone_api_key,
                    namespace,
                    expected_dim,
                    config: upserts.append(
                        (index_name, list(vectors), namespace, expected_dim)
                    ),
                ):
                    mm.load_all(cfg, provider, namespace="ns-test")

            self.assertEqual(len(upserts), 2)
            indexes = {entry[0] for entry in upserts}
            self.assertEqual(indexes, {"idx-openai-text", "idx-openai-clip"})

    def test_query_all_prints_retrieved_context_without_openai_key(self):
        cfg = _cfg("openai_clip")
        cfg.openai_api_key = ""
        provider = mock.Mock()
        provider.build_query_targets.return_value = [
            mm.QueryTarget(
                index_name="idx-openai-text", vector=[0.1] * 3072, label="text"
            )
        ]

        fake_index = mock.Mock()
        fake_index.query.return_value = {
            "matches": [
                {
                    "metadata": {
                        "text": "retrieved fact",
                        "filename": "data/txt/test.txt",
                        "modality": "text",
                    }
                }
            ]
        }
        fake_pc = mock.Mock()
        fake_pc.Index.return_value = fake_index

        with mock.patch.object(mm, "Pinecone", return_value=fake_pc):
            with mock.patch("builtins.print") as print_mock:
                mm.query_all(cfg, provider, query="what?", top_k=2, namespace="ns-test")

        print_calls = [args[0] for args, _ in print_mock.call_args_list if args]
        self.assertTrue(any("retrieved fact" in call for call in print_calls))

    def test_aws_nova_validate_warns_on_dimension_mismatch(self):
        """Mismatched AWS_NOVA_EMBEDDING_DIMENSION vs AWS_NOVA_EXPECTED_DIMENSION triggers warning."""
        cfg = _cfg("aws_nova")
        # Deliberately set a mismatch
        cfg.aws_nova_embedding_dimension = 1024
        cfg.aws_nova_expected_dim = 3072

        with mock.patch("boto3.client", return_value=mock.Mock()):
            provider = mm.AwsNovaProvider(cfg)

        with mock.patch("builtins.print") as mock_print:
            provider.validate()

        print_calls = [str(args[0]) for args, _ in mock_print.call_args_list if args]
        self.assertTrue(
            any("[nova] WARNING" in call for call in print_calls),
            f"Expected [nova] WARNING in print output, got: {print_calls}",
        )

    def test_aws_nova_defaults_to_3072d(self):
        """PipelineConfig.from_env() defaults Nova embedding dimension to 3072 when env vars are absent."""
        # Use a minimal env — do NOT set AWS_NOVA_EMBEDDING_DIMENSION or AWS_NOVA_EXPECTED_DIMENSION
        env = {
            "MULTIMODAL_PROVIDER": "aws_nova",
            "PINECONE_API_KEY": "pc",
            "PINECONE_INDEX": "idx-generic",
            "PINECONE_INDEX_AWS_NOVA_1024": "idx-aws",
            "PINECONE_NAMESPACE": "ns-test",
        }
        # Temporarily clear any existing Nova dim env vars so defaults apply
        clear_keys = ["AWS_NOVA_EMBEDDING_DIMENSION", "AWS_NOVA_EXPECTED_DIMENSION"]
        with mock.patch.dict(os.environ, env, clear=False):
            for key in clear_keys:
                os.environ.pop(key, None)
            cfg = mm.PipelineConfig.from_env()

        self.assertEqual(
            cfg.aws_nova_embedding_dimension,
            3072,
            f"Expected default 3072, got {cfg.aws_nova_embedding_dimension}",
        )
        self.assertEqual(
            cfg.aws_nova_expected_dim,
            3072,
            f"Expected default 3072, got {cfg.aws_nova_expected_dim}",
        )

    def test_vertex_validate_warns_invalid_dimension(self):
        """Invalid GOOGLE_VERTEX_EMBEDDING_DIMENSION triggers warning and falls back to 1408."""
        env_overrides = {
            "MULTIMODAL_PROVIDER": "vertex",
            "GOOGLE_VERTEX_EMBEDDING_DIMENSION": "999",  # not in {128, 256, 512, 1408}
        }
        cfg = _cfg("vertex")
        cfg.google_vertex_embedding_dimension = 999  # simulate invalid parsed value

        with mock.patch("builtins.print") as mock_print:
            mm.VertexProvider(cfg).validate()

        print_calls = [str(args[0]) for args, _ in mock_print.call_args_list if args]
        self.assertTrue(
            any("[vertex] WARNING" in call for call in print_calls),
            f"Expected [vertex] WARNING in print output, got: {print_calls}",
        )
        self.assertEqual(
            cfg.google_vertex_embedding_dimension,
            1408,
            "validate() should fall back to 1408d on invalid dimension",
        )

    def test_vertex_validate_accepts_all_valid_dims(self):
        """128, 256, 512, 1408 are all accepted without printing any warning."""
        cfg = _cfg("vertex")
        valid_dims = [128, 256, 512, 1408]
        for dim in valid_dims:
            cfg.google_vertex_embedding_dimension = dim
            with mock.patch("builtins.print") as mock_print:
                mm.VertexProvider(cfg).validate()
            print_calls = [
                str(args[0]) for args, _ in mock_print.call_args_list if args
            ]
            self.assertFalse(
                any("[vertex] WARNING" in call for call in print_calls),
                f"Unexpected warning for valid dim={dim}: {print_calls}",
            )


if __name__ == "__main__":
    unittest.main()
