# Phase 3: Vertex AI Enhancement - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Google Vertex AI (`multimodalembedding@001`) as a first-class provider in the multimodal pipeline — separate from AWS Nova and OpenAI. Vertex AI gets its own Pinecone indexes, its own env var configuration, and its own embedding dimension strategy. No cross-provider fusion or shared index space in this phase.

</domain>

<decisions>
## Implementation Decisions

### Provider separation
- Vertex AI and AWS Nova are fully separate providers — separate indexes, separate config, no shared dimension space
- No cross-provider search or result fusion in this phase

### Pinecone index naming
- Format: `multimodal-embedding-vertex-{dim}d`
- Examples: `multimodal-embedding-vertex-1408d`, `multimodal-embedding-vertex-512d`
- Consistent with descriptive naming that makes index contents immediately clear

### Dimension configuration
- Controlled via `VERTEX_EMBEDDING_DIMENSION` env var
- Valid values: 128, 256, 512, 1408
- Default: 1408d (max quality)
- Must be added to `.env_sample` with documentation

### Invalid dimension handling
- If `VERTEX_EMBEDDING_DIMENSION` is set to an invalid value (anything not in 128, 256, 512, 1408):
  - Print a warning identifying the invalid value
  - Fall back to 1408d automatically
  - Do NOT raise — matches existing Nova/CLIP pattern
  - Pinecone preflight does hard enforcement downstream

### Nova dimension correction (in-scope fix)
- AWS Nova docs confirm supported dimensions are: 3072, 1024, 384, 256
- Phase 2 shipped with 1024d as default; 3072d is the model's native maximum and AWS's documented default
- Phase 3 should correct `AWS_NOVA_EMBEDDING_DIMENSION` default to 3072d
- Same fallback pattern: invalid value → warn + fall back to 3072d

### Claude's Discretion
- Modality coverage for Vertex (which file types: text, image, audio, video — follow what `multimodalembedding@001` natively supports)
- GCP auth/credential pattern (follow established patterns for Vertex AI SDK)
- Fallback behavior for unsupported file types (follow Nova's `[]` return pattern)
- Test coverage structure (follow existing 22-test Nova pattern as reference)

</decisions>

<specifics>
## Specific Ideas

- Index name pattern `multimodal-embedding-vertex-1408d` was explicitly preferred — full descriptive name, not short prefix like `vertex_1408d` or `gcp_1408d`
- Nova dimension correction (3072d default) came from reviewing official AWS docs mid-discussion — treat as a documentation/config fix bundled into this phase

</specifics>

<deferred>
## Deferred Ideas

- Cross-provider search / result fusion — Phase 4 (Provider Abstraction & Fusion)
- Vertex AI models beyond `multimodalembedding@001` — future phase if needed

</deferred>

---

*Phase: 03-vertex-ai-enhancement*
*Context gathered: 2026-02-20*
