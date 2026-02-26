# Debugging Bug List (Legacy, OpenAI, Vertex)

Date: 2026-02-19

## Scope
- Unit tests: `tests/test_*.py`
- Loader runtime checks:
  - `python pinecone-legacy-rag.py --load`
  - `python pinecone-openai-load.py --load`
  - `python pinecone-vertexai-load.py --load`

## Current Unit-Test Status
- Result: PASS
- Command: `python -m unittest discover -s tests -p 'test_*.py'`
- Output summary: `Ran 15 tests ... OK`

## 1) Vertex multimodal text length failure (code issue)
- Symptom (from user logs):
  - `Text field must be smaller than 1024 characters.`
- Root cause:
  - Pipeline chunking was using up to 1200 chars globally; Vertex API enforces `<1024` on text field.
- Fix implemented:
  - Added hard text chunking for Vertex provider to max 1000 chars.
  - Applied chunk safety to:
    - load-time text ingestion
    - audio transcript ingestion
    - query embedding input
- Files changed:
  - `pinecone-multimodal-pipeline.py`
  - `tests/test_multimodal_pipeline.py`
- Verification:
  - Added tests:
    - `test_vertex_provider_splits_long_text_for_load`
    - `test_vertex_provider_limits_query_text`
  - Both pass.

## 2) Vertex loader fails in this environment (runtime/network issue)
- Repro command:
  - `python pinecone-vertexai-load.py --load`
- Observed error:
  - `google.auth.exceptions.TransportError`
  - DNS resolution failed for `oauth2.googleapis.com`
- Root cause:
  - Environment/network DNS/connectivity issue; token endpoint unreachable.
- Code-side hardening added:
  - Vertex `_predict` now captures request exceptions and reports concise aggregated request errors.
- Next runtime check needed (outside this restricted network):
  - Re-run loader in a network-enabled shell with valid Google credentials.

## 3) OpenAI loader fails in this environment (runtime/network issue)
- Repro command:
  - `python pinecone-openai-load.py --load`
- Observed error:
  - `openai.APIConnectionError` from `httpx.ConnectError`
  - DNS resolution failure
- Root cause:
  - Environment/network DNS/connectivity issue to OpenAI endpoint.
- Additional code issue fixed:
  - Shared index names across providers could mis-apply expected dimension checks
    (e.g., OpenAI vectors 3072 being compared against Vertex 1408 expectations).
  - Fixed by provider-first dimension routing and explicit validation that OpenAI text
    and Vertex indexes must not share a name when dimensions differ.
- Next runtime check needed (outside this restricted network):
  - Re-run loader in a network-enabled shell with valid OpenAI key.

## 4) Legacy loader fails in this environment (runtime/network issue)
- Repro command:
  - `python pinecone-legacy-rag.py --load`
- Observed error:
  - `google.auth.exceptions.TransportError`
  - DNS resolution failed for `oauth2.googleapis.com`
- Root cause:
  - Environment/network DNS/connectivity issue for Vertex auth/token endpoint.
- Next runtime check needed (outside this restricted network):
  - Re-run legacy loader where outbound HTTPS/DNS is available.

## Fixes Implemented This Cycle
1. Vertex-safe text chunking (`<=1000 chars`) before embedding.
2. Vertex query-length clamp for embedding call.
3. Vertex request error aggregation in `_predict` for better diagnostics.
4. Added regression unit tests for the above behaviors.

## Remaining External Blockers
1. Outbound DNS/network to Google OAuth and OpenAI API from runtime environment.
2. Live integration validation (actual upsert/query) must be executed in network-enabled env.
