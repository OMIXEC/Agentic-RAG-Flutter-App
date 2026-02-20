---
phase: "02"
plan: "03"
subsystem: aws-nova-validation
tags: [aws, nova, bedrock, pinecone, validation, env-config]

dependency-graph:
  requires:
    - "02-01"  # Nova video size guard and audio fallback
    - "02-02"  # Nova multimodal test coverage (22 tests)
  provides:
    - "AwsNovaProvider dimension consistency validation"
    - "Unified .env_sample Nova documentation"
  affects:
    - "Any future plan modifying AwsNovaProvider"
    - "Any plan adding new Nova config vars"

tech-stack:
  added: []
  patterns:
    - "print()-not-raise for dimension mismatch warnings (matches CLIP pattern)"
    - "Variable extraction before comparison for formatter-resistant single-line if"
    - "Comment-driven grep verification pattern"

key-files:
  created: []
  modified:
    - "pinecone-multimodal-pipeline.py"
    - ".env_sample"

decisions:
  - "Nova dimension validation uses print() not raise ValueError — consistent with CLIP dimension warnings; Pinecone preflight handles hard enforcement"
  - "Variables extracted (embed_dim, expected_dim) before comparison to ensure if condition stays on single line despite formatter"
  - "AWS_NOVA_EMBEDDING_DIMENSION added to .env_sample — it was already read by the pipeline (line 542-543) but was never documented for users"

metrics:
  duration: "2 minutes"
  completed: "2026-02-20"
---

# Phase 02 Plan 03: Nova Dimension Consistency Validation Summary

**One-liner:** Nova validate() warns on `aws_nova_embedding_dimension != aws_nova_expected_dim` with print(); .env_sample documents all 5 Nova vars in one cohesive block.

## What Was Built

Added an early-warning validation to `AwsNovaProvider.validate()` that compares the Bedrock request dimension (`AWS_NOVA_EMBEDDING_DIMENSION`) against the Pinecone preflight dimension (`AWS_NOVA_EXPECTED_DIMENSION`). If they diverge, a `[nova] WARNING` is printed — identical pattern to the OpenAI CLIP dimension warnings. The Pinecone preflight layer remains the hard enforcement.

Also consolidated the scattered Nova environment variables in `.env_sample` into a single documented block with a comment explaining the unified 1024d space concept (unlike OpenAI which uses 3072d for text + 512d for CLIP, Nova uses 1024d for all modalities).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add dimension consistency validation to AwsNovaProvider.validate() | 66981cf | pinecone-multimodal-pipeline.py |
| 2 | Document unified 1024d space in .env_sample | 8904a62 | .env_sample |

## Key Changes

### pinecone-multimodal-pipeline.py

**Added above `AwsNovaProvider` class (line 1125):**
```python
# AwsNovaProvider: All modalities (text, image, video, audio) share a single
# 1024-dimensional embedding space. AWS_NOVA_EMBEDDING_DIMENSION controls the
# Bedrock request; AWS_NOVA_EXPECTED_DIMENSION controls the Pinecone preflight.
# These must always match. Unlike OpenAI (text=3072, CLIP=512), Nova is unified.
```

**Added inside `validate()` method:**
```python
embed_dim = self.config.aws_nova_embedding_dimension
expected_dim = self.config.aws_nova_expected_dim
if embed_dim != expected_dim:
    print(
        f"[nova] WARNING: AWS_NOVA_EMBEDDING_DIMENSION={...} != AWS_NOVA_EXPECTED_DIMENSION={...}. "
        "Both values should be 1024 for amazon.nova-2-multimodal-embeddings-v1. "
        "Pinecone preflight will enforce the expected dim and may reject upserts."
    )
```

### .env_sample

Replaced bare Nova vars with a documented block:
```
# AWS Nova Multimodal Embeddings
# Nova uses a UNIFIED embedding space: ALL modalities (text, image, video, audio)
# embed to the same dimension (1024 for amazon.nova-2-multimodal-embeddings-v1).
# Both vars below must match each other AND your Pinecone index dimension.
...
AWS_NOVA_EMBEDDING_DIMENSION="1024"   # (was missing before this plan)
AWS_NOVA_EXPECTED_DIMENSION="1024"
AWS_NOVA_VIDEO_MAX_BYTES="20971520"
```

## Verification Results

```
=== Dimension warning in validate() ===
1147: # Check: aws_nova_embedding_dimension == aws_nova_expected_dim

=== Video size guard (02-01) ===
1219: file_size = file_path.stat().st_size
1220: if file_size > self.config.aws_nova_video_max_bytes:

=== .env_sample Nova block ===
# AWS Nova Multimodal Embeddings
# Nova uses a UNIFIED embedding space...
AWS_NOVA_EMBEDDING_DIMENSION="1024"
AWS_NOVA_EXPECTED_DIMENSION="1024"
AWS_NOVA_VIDEO_MAX_BYTES="20971520"

=== Test suite ===
Ran 22 tests in 0.094s — OK
```

## Decisions Made

1. **print()-not-raise for dimension mismatch** — Matches the CLIP provider pattern. Users may intentionally experiment with dimensions; Pinecone preflight provides hard enforcement when they upsert.

2. **Variable extraction before comparison** — Black/ruff reformatters split `if self.config.A != self.config.B:` across lines when it exceeds 88 chars. Extracting to `embed_dim`/`expected_dim` keeps the `if` on a single line, which also improves readability.

3. **Added `AWS_NOVA_EMBEDDING_DIMENSION` to .env_sample** — The pipeline was already reading this env var (line 542-543 of the pipeline) but it was never documented. Users relying solely on `.env_sample` would have had no hint this var existed.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Phase 02 (aws-nova-integration) is now complete. All three plans executed:
- 02-01: Audio fallback chunking + video size guard
- 02-02: Nova multimodal test coverage (22 tests)
- 02-03: Dimension consistency validation + .env_sample documentation

The Nova provider is production-ready with proper validation, test coverage, and documentation.
