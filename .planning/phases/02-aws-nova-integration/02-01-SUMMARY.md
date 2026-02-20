---
phase: "02"
plan: "01"
name: "AwsNovaProvider bug fixes: config-aware audio chunking + video size guard"
subsystem: aws-nova-provider
status: complete
tags: [aws-bedrock, nova, chunking, video-guard, pipeline]

one-liner: "Config-aware audio chunking and 20MB video payload guard in AwsNovaProvider"

dependency-graph:
  requires: ["01-03"]
  provides:
    - "AwsNovaProvider audio fallback respects CHUNK_STRATEGY / CHUNK_MAX_CHARS / CHUNK_MIN_CHARS / CHUNK_OVERLAP_CHARS"
    - "AwsNovaProvider._embed_video returns [] with warning for files > AWS_NOVA_VIDEO_MAX_BYTES"
    - "PipelineConfig.aws_nova_video_max_bytes field (20MB default)"
  affects: ["02-02", "02-03"]

tech-stack:
  added: []
  patterns:
    - "chunk_text_with_strategy() for all provider audio fallback paths"
    - "stat().st_size guard before read_bytes() for media payloads"

key-files:
  created: []
  modified:
    - "pinecone-multimodal-pipeline.py"
    - ".env_sample"

decisions:
  - id: D1
    decision: "Video size guard returns [] (not raises) for oversized files"
    rationale: "load_all already handles empty target lists gracefully; raising would crash the whole ingestion run for a single oversized file"
  - id: D2
    decision: "Default AWS_NOVA_VIDEO_MAX_BYTES = 20MB (not 25MB hard limit)"
    rationale: "Base64 encoding adds ~33% overhead; 20MB raw gives ~26.7MB encoded which is near the Bedrock 25MB request body limit — safer to leave margin and warn early"

metrics:
  duration: "1m"
  tasks-completed: 2
  tasks-total: 2
  completed: "2026-02-20"
---

# Phase 02 Plan 01: AwsNovaProvider Bug Fixes Summary

## One-liner

Config-aware audio chunking and 20MB video payload guard in AwsNovaProvider

## What Was Built

Fixed two high-risk production bugs in `AwsNovaProvider`:

1. **Audio transcript chunking** — The fallback path in `build_audio_targets` was calling `_chunk_text(transcript)` with no arguments, silently ignoring `CHUNK_STRATEGY`, `CHUNK_MAX_CHARS`, `CHUNK_MIN_CHARS`, and `CHUNK_OVERLAP_CHARS`. Replaced with `chunk_text_with_strategy(transcript, self.config.chunk_strategy, ...)` to match the pattern used in `load_all` for text/doc files.

2. **Video payload size guard** — `_embed_video` was calling `file_path.read_bytes()` unconditionally. AWS Bedrock Nova has a ~25MB request body limit; large videos would trigger `ClientError` or OOM. Added `stat().st_size` check before payload construction; files exceeding `aws_nova_video_max_bytes` (default 20MB) return `[]` with a descriptive warning instead of crashing.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Fix audio transcript chunking in AwsNovaProvider | `70d635f` | `pinecone-multimodal-pipeline.py` |
| 2 | Add video payload size guard to AwsNovaProvider | `732aceb` | `pinecone-multimodal-pipeline.py`, `.env_sample` |

## Verification Results

- All 17 existing tests pass (`Ran 17 tests in 0.107s OK`)
- `chunk_text_with_strategy` confirmed at line 1321 in `build_audio_targets` fallback
- `aws_nova_video_max_bytes` field confirmed in `PipelineConfig` (line 404) and `from_env()` (line 546)
- `stat().st_size` guard confirmed in `_embed_video` (line 1202–1206)
- `AWS_NOVA_VIDEO_MAX_BYTES` documented in `.env_sample`

## Decisions Made

### D1: Video size guard returns [] instead of raising

Return `[]` on oversized files so `build_video_targets` propagates empty and `load_all` skips the file cleanly. Raising would crash the entire ingestion run for a single large file.

### D2: Default 20MB (not 25MB Bedrock hard limit)

Base64 encoding adds ~33% overhead to file bytes. A 20MB raw file becomes ~26.7MB encoded, which is near Bedrock's 25MB request body limit. Using 20MB as default leaves a meaningful safety margin.

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

Phase 02 plans 02 and 03 can proceed. The `aws_nova_video_max_bytes` config field is available for any future plans that need to reference it. The audio chunking fix ensures consistent behavior across all providers.
