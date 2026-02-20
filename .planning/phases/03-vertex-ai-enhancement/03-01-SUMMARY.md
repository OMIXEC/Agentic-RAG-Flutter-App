---
phase: "03"
plan: "01"
subsystem: vertex-ai-validation
tags: [vertex, google-cloud, pinecone, validation, env-config, dimension-safety]

dependency-graph:
  requires:
    - "02-03"  # Nova dimension validation pattern (print()-not-raise)
  provides:
    - "VertexProvider dimension validation in validate()"
    - "Corrected Nova defaults to 3072d"
    - "Documented Vertex AI env vars in .env_sample"
  affects:
    - "Any future plan modifying VertexProvider"
    - "Any plan adding new Vertex config vars"
    - "Users migrating from 1024d Nova indexes to 3072d"

tech-stack:
  added: []
  patterns:
    - "print()-not-raise for dimension mismatch warnings (matches CLIP/Nova pattern)"
    - "Module-level allowed-dim set (_VERTEX_ALLOWED_DIMS) for O(1) membership check"
    - "Mutating self.config for fallback reassignment (consistent with existing provider pattern)"

key-files:
  created: []
  modified:
    - "pinecone-multimodal-pipeline.py"
    - ".env_sample"

decisions:
  - "Vertex dimension validation uses print() + fallback not raise ValueError — consistent with CLIP and Nova warning patterns; Pinecone preflight handles hard enforcement"
  - "_VERTEX_ALLOWED_DIMS placed as module-level constant before VertexProvider class — mirrors pattern of other module-level constants"
  - "Nova defaults corrected to 3072 not 1024 — 3072d is the AWS-documented native maximum for amazon.nova-2-multimodal-embeddings-v1; 1024 was a placeholder"
  - "pinecone_index_aws_nova_1024 Python attribute name left unchanged — renaming would break existing tests and configs (CONTEXT.md decision)"
  - "PINECONE_INDEX_VERTEX_1408 default in .env_sample uses locked name 'multimodal-embedding-vertex-1408d' — naming convention established in this phase"

metrics:
  duration: "3 minutes"
  completed: "2026-02-20"
---

# Phase 03 Plan 01: Vertex Dimension Validation + Nova Defaults Summary

**One-liner:** `VertexProvider.validate()` enforces {128, 256, 512, 1408} dimensions with print()-fallback to 1408d; Nova from_env() corrected to 3072d default; .env_sample documents all 8 Vertex AI vars.

## What Was Built

Added dimension validation to `VertexProvider.validate()` following the established CLIP/Nova warning pattern: invalid `GOOGLE_VERTEX_EMBEDDING_DIMENSION` values trigger a `[vertex] WARNING` message and fall back to 1408d (max quality), while the four valid dimensions (128, 256, 512, 1408) pass silently. Pinecone preflight remains the hard enforcement layer.

Also corrected `PipelineConfig.from_env()` to default Nova dimensions to 3072d (the AWS-documented native maximum for `amazon.nova-2-multimodal-embeddings-v1`) instead of the previous placeholder value of 1024d, and updated `AwsNovaProvider.validate()`'s warning message to reference 3072 accordingly.

Finally, updated `.env_sample` with a fully documented Vertex AI section (8 vars with comments) and corrected Nova default values to match the pipeline's new defaults.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Vertex dimension validation to VertexProvider.validate() | d2adc54 | pinecone-multimodal-pipeline.py |
| 2 | Correct Nova defaults to 3072d and update validate() warning | d46e7a1 | pinecone-multimodal-pipeline.py |
| 3 | Update .env_sample with Vertex config and corrected Nova defaults | d4c6f05 | .env_sample |

## Key Changes

### pinecone-multimodal-pipeline.py

**Added before `VertexProvider` class:**
```python
_VERTEX_ALLOWED_DIMS = {128, 256, 512, 1408}
```

**Extended `VertexProvider.validate()` with dimension check:**
```python
dim = self.config.google_vertex_embedding_dimension
if dim not in _VERTEX_ALLOWED_DIMS:
    print(
        f"[vertex] WARNING: GOOGLE_VERTEX_EMBEDDING_DIMENSION={dim} is not a valid "
        f"Vertex multimodalembedding@001 dimension. Valid values: {sorted(_VERTEX_ALLOWED_DIMS)}. "
        "Falling back to 1408d. Pinecone preflight will enforce the expected dim."
    )
    self.config.google_vertex_embedding_dimension = 1408
```

**Corrected `PipelineConfig.from_env()` Nova defaults:**
```python
# Before:
aws_nova_embedding_dimension=int(_env("AWS_NOVA_EMBEDDING_DIMENSION", "1024")),
aws_nova_expected_dim=int(_env("AWS_NOVA_EXPECTED_DIMENSION", "1024")),

# After:
aws_nova_embedding_dimension=int(_env("AWS_NOVA_EMBEDDING_DIMENSION", "3072")),
aws_nova_expected_dim=int(_env("AWS_NOVA_EXPECTED_DIMENSION", "3072")),
```

**Updated `AwsNovaProvider.validate()` warning string:**
```
"Both values should be 3072 for amazon.nova-2-multimodal-embeddings-v1 (native max). "
```

### .env_sample

- `PINECONE_INDEX_VERTEX_1408` updated to `"multimodal-embedding-vertex-1408d"` (locked naming convention)
- Added full Vertex AI block replacing bare 2-line stub:
  ```
  # Google Vertex AI Multimodal Embeddings
  # Uses multimodalembedding@001 — supports text, image, and video natively.
  # Auth: set GOOGLE_VERTEX_ACCESS_TOKEN for short-lived tokens, or
  #       GOOGLE_APPLICATION_CREDENTIALS for service-account key file (recommended for production).
  # GOOGLE_VERTEX_EMBEDDING_DIMENSION: requested output dimension
  #   Valid values: 128, 256, 512, 1408 (default: 1408 = max quality)
  #   Invalid values trigger a warning and fall back to 1408d automatically.
  ...
  GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
  GOOGLE_CLOUD_LOCATION="us-central1"
  GOOGLE_VERTEX_MODEL="multimodalembedding@001"
  GOOGLE_VERTEX_EMBEDDING_DIMENSION="1408"
  GOOGLE_VERTEX_EXPECTED_DIMENSION="1408"
  GOOGLE_VERTEX_ACCESS_TOKEN=""
  GOOGLE_APPLICATION_CREDENTIALS=""
  VERTEX_VIDEO_GCS_BUCKET=""
  ```
- `AWS_NOVA_EMBEDDING_DIMENSION` and `AWS_NOVA_EXPECTED_DIMENSION` corrected to `"3072"`
- Nova comment block updated to document 3072 as native max with valid value list

## Verification Results

```
=== Task 1: VertexProvider.validate() with invalid dim ===
PASS: invalid dim warns and falls back to 1408

=== Task 1: Valid dimensions produce no warning ===
PASS: dim=128 is valid, no warning
PASS: dim=256 is valid, no warning
PASS: dim=512 is valid, no warning
PASS: dim=1408 is valid, no warning

=== Task 2: Nova defaults to 3072d ===
PASS: Nova defaults to 3072d

=== Task 3: .env_sample keys verified ===
PINECONE_INDEX_VERTEX_1408="multimodal-embedding-vertex-1408d" ✓
GOOGLE_CLOUD_LOCATION="us-central1" ✓
GOOGLE_VERTEX_MODEL="multimodalembedding@001" ✓
GOOGLE_VERTEX_EMBEDDING_DIMENSION="1408" ✓
GOOGLE_APPLICATION_CREDENTIALS="" ✓
VERTEX_VIDEO_GCS_BUCKET="" ✓
AWS_NOVA_EMBEDDING_DIMENSION="3072" ✓

=== Full test suite ===
22 passed in 0.59s ✓
```

## Decisions Made

1. **Vertex dimension validation uses print() + fallback** — Consistent with CLIP (`_resolve_clip_expected_dim`) and Nova warning patterns. Users who intentionally test with non-standard dimensions get a clear warning; Pinecone preflight hard-enforces on upsert.

2. **Fallback to 1408d (not raise)** — 1408d is the maximum quality dimension and safe default for `multimodalembedding@001`. Auto-correcting to it prevents silent failures while keeping the pipeline functional.

3. **Nova corrected to 3072d** — AWS documentation for `amazon.nova-2-multimodal-embeddings-v1` specifies 3072d as the native maximum. The prior 1024d was a placeholder that didn't match AWS docs. Users with existing 1024d Pinecone indexes can override via env var.

4. **`pinecone_index_aws_nova_1024` attribute name preserved** — Renaming the Python attribute to reflect 3072 would require coordinated test and config changes; the CONTEXT.md decision was to leave field names as-is.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Plan 03-01 is complete. Phase 03 (vertex-ai-enhancement) continues with plan 03-02 which builds on the validated Vertex dimension infrastructure established here.
