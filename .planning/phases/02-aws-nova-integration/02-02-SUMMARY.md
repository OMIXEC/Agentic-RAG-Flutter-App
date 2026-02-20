---
phase: 02-aws-nova-integration
plan: 02
subsystem: testing
tags: [python, unittest, aws-nova, bedrock, multimodal, mock, pathlib, chunking]

# Dependency graph
requires:
  - phase: 02-01
    provides: AwsNovaProvider audio fallback using chunk_text_with_strategy with config params; video size guard in _embed_video returning [] for oversized files

provides:
  - 5 new test methods covering AwsNovaProvider image, video, audio native and fallback embed paths
  - Regression net for Nova multimodal embedding and size guard behavior
  - Test count increased from 17 to 22

affects:
  - 02-03 (future Nova enhancements can use these tests as regression baseline)
  - Any phase modifying AwsNovaProvider multimodal methods

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mock Path.stat at class level (not instance) since PosixPath instances are read-only"
    - "Use transcript length > chunk_min_chars (80) to ensure chunking produces output in fallback tests"
    - "Wrap real function with wraps= to spy on calls while preserving behavior"

key-files:
  created: []
  modified:
    - tests/test_multimodal_pipeline.py

key-decisions:
  - "Mock Path.stat at class level (mock.patch.object(Path, 'stat', ...)) because PosixPath instance attributes are read-only"
  - "Transcript in audio fallback test must exceed chunk_min_chars=80 to produce chunk output; short strings silently return []"
  - "wrap chunk_text_with_strategy with wraps= parameter to verify call args while keeping real chunking behavior"

patterns-established:
  - "Audio fallback test pattern: mock _embed_audio=[], mock _transcribe_fallback=long_string, spy chunk_text_with_strategy, assert call_args match config"
  - "Video size guard test pattern: patch Path.stat at class level, assert build_video_targets returns []"

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 02 Plan 02: Nova Multimodal Test Coverage Summary

**5 test methods added covering AwsNovaProvider image/video/audio native embeds, audio transcript fallback chunking config enforcement, and video 30MB size guard — all 22 tests passing**

## Performance

- **Duration:** 2 min 21 sec
- **Started:** 2026-02-20T04:13:09Z
- **Completed:** 2026-02-20T04:15:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `test_aws_nova_image_embed_returns_1024d_target`: verifies image embed returns 1024d vector with modality=image, media_type=image
- Added `test_aws_nova_video_embed_returns_1024d_target`: verifies video embed returns 1024d vector with modality=video
- Added `test_aws_nova_audio_native_embed_skips_transcript`: verifies `_transcribe_fallback` is NOT called when native audio embed succeeds
- Added `test_aws_nova_audio_fallback_uses_chunk_config`: asserts `chunk_text_with_strategy` receives `cfg.chunk_strategy` and `cfg.chunk_max_chars` (not hardcoded values) — codifies the 02-01 bug fix
- Added `test_aws_nova_video_size_guard_returns_empty_for_large_file`: asserts 30MB file returns `[]` from `build_video_targets` via size guard in `_embed_video`
- All 22 tests pass (17 pre-existing + 5 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Nova image and video native embed tests** - `56e2db6` (test)
2. **Task 2: Add Nova audio native/fallback tests and video size guard** - `198af37` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `tests/test_multimodal_pipeline.py` - Added 5 new `test_aws_nova_*` test methods; 17→22 test count

## Decisions Made
- **Mock Path.stat at class level** — PosixPath instances are read-only; `mock.patch.object(Path, 'stat', ...)` patches all instances within the context, which is safe for isolated tests
- **Long transcript in fallback test** — `chunk_text_with_strategy` silently returns `[]` for strings below `chunk_min_chars=80`; using a 128-char transcript ensures chunks are produced and `_embed_text` is called
- **Wrap real chunk function** — Used `wraps=mm.chunk_text_with_strategy` to spy on call arguments while keeping actual chunking logic, avoiding need to mock return value

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PosixPath instance `stat` attribute is read-only**
- **Found during:** Task 2 (video size guard test)
- **Issue:** `mock.patch.object(vid_path, 'stat', ...)` raised `AttributeError: 'PosixPath' object attribute 'stat' is read-only` because Python's pathlib uses `__slots__`-like protection
- **Fix:** Changed to `mock.patch.object(Path, 'stat', return_value=mock_stat)` — patches at class level, applies to all instances within context
- **Files modified:** tests/test_multimodal_pipeline.py
- **Verification:** Test passes and prints the expected size-guard warning
- **Committed in:** `198af37` (Task 2 commit)

**2. [Rule 1 - Bug] Short transcript produces empty chunks, test assertion fails**
- **Found during:** Task 2 (audio fallback chunk config test)
- **Issue:** `'hello world transcript'` (22 chars) is below `chunk_min_chars=80`, so `chunk_text_with_strategy` returns `[]`, `_embed_text` is never called, `targets` is empty — assertion `len(targets) > 0` fails
- **Fix:** Replaced short string with a 128-char transcript that exceeds the minimum threshold
- **Files modified:** tests/test_multimodal_pipeline.py
- **Verification:** `chunk_text_with_strategy` called once, `targets` has 1 entry with modality=audio
- **Committed in:** `198af37` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bugs)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep — same assertions and behavioral coverage as specified.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 22 tests passing; Nova multimodal paths fully covered with regression tests
- 02-03 can confidently add new Nova features knowing existing behavior is locked in
- No blockers

---
*Phase: 02-aws-nova-integration*
*Completed: 2026-02-20*
