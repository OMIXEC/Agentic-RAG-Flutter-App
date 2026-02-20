---
phase: "03"
plan: "02"
subsystem: test-coverage
tags: [vertex, nova, validation, dimension, tests, regression-prevention]

dependency-graph:
  requires:
    - "03-01"  # VertexProvider.validate() dimension guard + Nova 3072d defaults (behavior under test)
  provides:
    - "4 regression-prevention tests for Vertex dimension validation"
    - "4 regression-prevention tests for Nova dimension defaults and mismatch warnings"
    - "Full 26-test suite covering all providers and validation paths"
  affects:
    - "Any future plan modifying VertexProvider.validate() or PipelineConfig.from_env()"
    - "04-provider-abstraction (Vertex provider is now fully test-covered)"

tech-stack:
  added: []
  patterns:
    - "mock.patch('builtins.print') to assert provider warning output"
    - "mock.patch.dict(os.environ, ...) + os.environ.pop() to isolate default-value tests"
    - "Direct attribute mutation on cfg object to set up dimension mismatch scenarios"

key-files:
  created: []
  modified:
    - "tests/test_multimodal_pipeline.py"

decisions:
  - "4 new tests appended before the if __name__ block — consistent with existing test ordering pattern"
  - "Nova defaults test uses os.environ.pop() inside patch.dict context to clear keys while isolating from shell env"
  - "Vertex warning test mutates cfg.google_vertex_embedding_dimension directly rather than patching env — simulates post-parse invalid value in the simplest way"

metrics:
  duration: "1 minute"
  completed: "2026-02-20"
---

# Phase 03 Plan 02: Validation Test Coverage Summary

**One-liner:** 4 targeted tests added to lock in Vertex dimension validation (warn+fallback to 1408d) and Nova 3072d defaults, bringing the suite from 22 to 26 passing tests.

## What Was Built

Added 4 new test methods to `MultimodalPipelineTests` in `tests/test_multimodal_pipeline.py`:

1. **`test_vertex_validate_warns_invalid_dimension`** — Verifies that setting `cfg.google_vertex_embedding_dimension = 999` (not in `{128, 256, 512, 1408}`) causes `VertexProvider.validate()` to print a `[vertex] WARNING` and mutate the config back to `1408`.

2. **`test_vertex_validate_accepts_all_valid_dims`** — Iterates over `[128, 256, 512, 1408]`, confirming that each valid dimension produces zero `[vertex] WARNING` print calls.

3. **`test_aws_nova_validate_warns_on_dimension_mismatch`** — Deliberately mismatches `cfg.aws_nova_embedding_dimension = 1024` vs `cfg.aws_nova_expected_dim = 3072` and confirms `AwsNovaProvider.validate()` prints `[nova] WARNING`.

4. **`test_aws_nova_defaults_to_3072d`** — Calls `PipelineConfig.from_env()` with a minimal env that omits `AWS_NOVA_EMBEDDING_DIMENSION` and `AWS_NOVA_EXPECTED_DIMENSION`, asserting both default to `3072`.

All 4 tests follow the Phase 2 established patterns: `mock.patch.dict(os.environ, ...)`, `mock.patch('builtins.print')`, and `mock.patch("boto3.client", ...)`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Vertex dimension validation tests | 73c2255 | tests/test_multimodal_pipeline.py |
| 2 | Add Nova dimension warning and default tests | 11efe0f | tests/test_multimodal_pipeline.py |
| 3 | Run full test suite — confirm 26 tests pass | (no commit — verification only) | — |

## Key Changes

### tests/test_multimodal_pipeline.py

**Added `test_vertex_validate_warns_invalid_dimension`:**
```python
cfg = _cfg("vertex")
cfg.google_vertex_embedding_dimension = 999
with mock.patch("builtins.print") as mock_print:
    mm.VertexProvider(cfg).validate()
# asserts [vertex] WARNING in print output
# asserts cfg.google_vertex_embedding_dimension == 1408
```

**Added `test_vertex_validate_accepts_all_valid_dims`:**
```python
for dim in [128, 256, 512, 1408]:
    cfg.google_vertex_embedding_dimension = dim
    # asserts NO [vertex] WARNING in print output
```

**Added `test_aws_nova_validate_warns_on_dimension_mismatch`:**
```python
cfg.aws_nova_embedding_dimension = 1024
cfg.aws_nova_expected_dim = 3072
provider.validate()
# asserts [nova] WARNING in print output
```

**Added `test_aws_nova_defaults_to_3072d`:**
```python
# omit AWS_NOVA_EMBEDDING_DIMENSION and AWS_NOVA_EXPECTED_DIMENSION from env
cfg = mm.PipelineConfig.from_env()
# asserts cfg.aws_nova_embedding_dimension == 3072
# asserts cfg.aws_nova_expected_dim == 3072
```

## Verification Results

```
$ python -m pytest tests/test_multimodal_pipeline.py -v
collected 26 items

test_aws_nova_audio_fallback_uses_chunk_config PASSED
test_aws_nova_audio_native_embed_skips_transcript PASSED
test_aws_nova_defaults_to_3072d PASSED
test_aws_nova_image_embed_returns_1024d_target PASSED
test_aws_nova_validate_warns_on_dimension_mismatch PASSED
test_aws_nova_video_embed_returns_1024d_target PASSED
test_aws_nova_video_size_guard_returns_empty_for_large_file PASSED
test_aws_provider_load_and_query_targets PASSED
test_dimension_guard_raises_before_upsert PASSED
test_index_client_prefers_host_when_configured PASSED
test_legacy_provider_routes_to_legacy_indexes PASSED
test_load_all_dispatches_all_modalities PASSED
test_openai_expected_dim_with_shared_index_name PASSED
test_openai_provider_load_and_query_targets PASSED
test_openai_text_embedding_uses_3072_for_text_embedding_3_large PASSED
test_preflight_detects_dimension_mismatch PASSED
test_query_all_prints_retrieved_context_without_openai_key PASSED
test_validate_common_rejects_non_3072_for_text_embedding_3_large PASSED
test_validate_common_rejects_openai_text_media_shared_index PASSED
test_validate_common_rejects_openai_vertex_same_index_with_dim_mismatch PASSED
test_vertex_predict_fallback_payload PASSED
test_vertex_provider_limits_query_text PASSED
test_vertex_provider_load_and_query_targets PASSED
test_vertex_provider_splits_long_text_for_load PASSED
test_vertex_validate_accepts_all_valid_dims PASSED
test_vertex_validate_warns_invalid_dimension PASSED

============================== 26 passed in 0.41s ==============================
```

## Decisions Made

1. **Vertex warning test mutates cfg directly** — `cfg.google_vertex_embedding_dimension = 999` bypasses `PipelineConfig.from_env()` entirely; tests the validate path in isolation without needing env var patching.

2. **Nova defaults test uses `os.environ.pop()` inside `patch.dict` context** — `mock.patch.dict(clear=False)` only adds/updates, doesn't remove. The `pop()` call inside the context manager ensures any pre-existing shell env vars for those keys don't bleed into the default assertion.

3. **Test order: Nova tests precede Vertex tests** — Inserted in the order matching the plan's task sequence (Nova → Vertex for Task 2 methods, then Vertex validate for Task 1).

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Phase 03 (vertex-ai-enhancement) is now complete. Both plans have SUMMARY.md files:
- `03-01`: Vertex dimension validation logic + Nova 3072d defaults (implementation)
- `03-02`: Test coverage for the above (regression prevention)

Phase 04 (provider abstraction) can proceed with confidence that all three providers (OpenAI, Vertex, Nova) are tested and validated.
