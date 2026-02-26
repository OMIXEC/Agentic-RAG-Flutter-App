# Findings

- Flutter app currently calls only `POST /v1/memories/chat`; it does not expose ingest/search/timeline/promote/delete flows from backend.
- Backend already supports provider-explicit routes:
  - `/v1/providers/{provider}/chat`
  - `/v1/providers/{provider}/search`
  - `/v1/providers/{provider}/ingest`
- Provider aliases supported by backend include `openai_clip`, `vertex`, `aws_nova`, and legacy aliases.
- Existing `app/lib/openai.dart` + `app/lib/pinecone.dart` are no longer wired into UI, so backend-first integration must happen in `app/lib/backend_api.dart` + `app/lib/chat.dart`.
- Existing Flutter test coverage is minimal (single widget title assertion), so integration needs service-level tests first.
