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
**Goal:** Complete GCP ecosystem support
**Status:** Not Started

---

## Phase 4: Provider Abstraction & Fusion
**Goal:** Multi-provider search with result fusion
**Status:** Not Started

---

## Phase 5: Flutter Frontend Integration
**Goal:** Complete mobile experience
**Status:** Not Started
