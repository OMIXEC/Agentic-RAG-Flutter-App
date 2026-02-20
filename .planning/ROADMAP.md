# Project Roadmap

## Phase 1: OpenAI Embedding Enhancement
**Goal:** Improve OpenAI embedding quality with better chunking and CLIP models
**Status:** Complete ✓
**Completed:** 2026-02-20
**Plans:** 3 plans in 3 waves

### Scope
- Enhanced text chunking (semantic, recursive, overlap)
- CLIP model upgrades (ViT-L-14, ViT-H-14)
- Environment-based configuration

### Success Criteria
- [x] Chunking preserves semantic context across boundaries
- [x] CLIP model configurable via env var
- [x] All existing tests pass
- [x] No regression in ingestion/query

Plans:
- [x] 01-01-PLAN.md — Configuration foundation
- [x] 01-02-PLAN.md — Enhanced chunking implementation
- [x] 01-03-PLAN.md — CLIP model upgrade

---

## Phase 2: AWS Nova Multimodal Deep Integration
**Goal:** Full Nova multimodal support with native audio/video embeddings, production safety guards, and comprehensive test coverage
**Status:** Complete ✓
**Completed:** 2026-02-20
**Plans:** 3 plans in 2 waves

### Scope
- Native audio embeddings with config-aware chunking fallback
- Video payload size guard (25MB Bedrock limit)
- Unified 1024d embedding space validation
- Comprehensive Nova test coverage (17 → 22 tests)

### Success Criteria
- [x] Nova audio fallback uses `chunk_text_with_strategy` with config params
- [x] Nova video guarded against files > `AWS_NOVA_VIDEO_MAX_BYTES`
- [x] All modality paths covered by tests
- [x] `validate()` warns on dimension mismatch
- [x] All 22 tests pass

Plans:
- [x] 02-01-PLAN.md — Audio chunking fix + video size guard
- [x] 02-02-PLAN.md — Comprehensive Nova test coverage
- [x] 02-03-PLAN.md — Unified 1024d validation + env documentation

---

## Phase 3: Vertex AI Enhancement
**Goal:** Add Vertex AI dimension validation, correct Nova defaults to 3072d, and fully document Vertex env vars — completing first-class GCP provider support
**Status:** Complete ✓
**Completed:** 2026-02-20
**Plans:** 2 plans in 2 waves

### Scope
- Vertex dimension validation in `VertexProvider.validate()` — warn + fallback to 1408d for invalid dims
- Nova default dimension corrected from 1024d → 3072d (AWS documented native maximum)
- `.env_sample` Vertex section fully documented with all 8 env vars and comments
- 4 new tests covering Vertex validation and Nova correction (22 → 26 tests)

### Success Criteria
- [x] `VertexProvider.validate()` warns and falls back for dims not in {128, 256, 512, 1408}
- [x] `PipelineConfig.from_env()` Nova defaults are 3072d
- [x] `.env_sample` has all Vertex env vars with inline comments
- [x] All 26 tests pass

Plans:
- [x] 03-01-PLAN.md — Vertex validate() + Nova defaults + .env_sample documentation
- [x] 03-02-PLAN.md — Test coverage for Vertex validation and Nova 3072d correction

---

## Phase 4: Provider Abstraction & Fusion
**Goal:** Multi-provider search with result fusion
**Status:** Not Started

---

## Phase 5: Flutter Frontend Integration
**Goal:** Complete mobile experience
**Status:** Not Started
