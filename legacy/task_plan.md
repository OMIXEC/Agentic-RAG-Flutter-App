# Task Plan

## Goal
Deliver Flutter backend integration for the OpenAI multitext embedding adaptation, focusing on text-only news data routed through `openai_clip` (text index only) while exposing chat/search/timeline/promote/delete flows.

## Phases
- [x] Analyze current repo/app/backend API contracts and identify integration gaps
- [ ] Add failing Flutter tests for new backend service + UI integration behavior
- [ ] Implement backend API client expansion and provider-aware request routing
- [ ] Integrate chat UI controls for provider, retrieval panel, and ingestion actions
- [ ] Run Flutter analyze/tests and update docs/env guidance

## Errors Encountered
| Error | Attempt | Resolution |
|---|---|---|
| `session-catchup.py` produced no visible output | 1 | Continued with manual state recovery from git status + planning files |
