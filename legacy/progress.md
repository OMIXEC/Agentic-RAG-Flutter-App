# Progress

- Added provider-pluggable multimodal core in `pinecone-multimodal-pipeline.py`.
- Fixed OpenAI validation issue: `PINECONE_MEDIA_INDEX` now optional via compatibility mode.
- Fixed Vertex 400 handling with multi-shape payload retries and clearer runtime errors.
- Added legacy entrypoint multimodal routing in `pinecone-db.py` with `LEGACY_TXT_ONLY=true` fallback.
- Added `pinecone-aws-load.py` and unit tests under `tests/`.
- Unit tests pass: `python -m unittest discover -s tests -p 'test_*.py'`.
