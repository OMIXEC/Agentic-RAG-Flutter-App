# Repository Guidelines

## Project Structure & Module Organization
This repository contains a Python RAG ingestion/query script plus a Flutter client.
- `pinecone-db.py`: loads `.txt` files into Pinecone and runs retrieval queries.
- `txts/`: local text corpus used for indexing.
- `flutter_frontend/lib/`: Flutter app code (`main.dart`, chat UI, OpenAI/Pinecone clients).
- `flutter_frontend/test/`: Flutter widget tests.
- `flutter_frontend/web/`: web entrypoint and icons.
- `.env_sample`: required environment variable template.

## Build, Test, and Development Commands
From repo root:
- `python -m venv env && source env/bin/activate`: create/activate Python env.
- `pip install -r requirements.txt`: install backend dependencies.
- `cp .env_sample .env`: create local config.
- `python pinecone-db.py -L`: load data from `DATA_FOLDER` into Pinecone.
- `python pinecone-db.py -Q "What is AI?"`: query indexed context.

From `flutter_frontend/`:
- `flutter pub get`: install Flutter dependencies.
- `flutter run`: run app locally.
- `flutter analyze`: run static analysis with `flutter_lints`.
- `flutter test`: run widget tests.

## Coding Style & Naming Conventions
- Dart: follow `flutter_lints` (`flutter_frontend/analysis_options.yaml`), 2-space indentation, `PascalCase` for classes/widgets, `lowerCamelCase` for members.
- Python: use 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes.
- Keep files focused by feature (chat UI in `chat.dart`, API wrappers in `openai.dart`/`pinecone.dart`).

## Testing Guidelines
- Flutter uses `flutter_test`; place tests in `flutter_frontend/test/` with `*_test.dart` naming.
- Prefer widget tests for UI behavior and mock network calls where possible.
- Run `flutter analyze && flutter test` before opening a PR.

## Commit & Pull Request Guidelines
Git history is not available in this workspace snapshot, so use Conventional Commits moving forward:
- Examples: `feat(chat): add streaming response`, `fix(pinecone): handle empty matches`.

PRs should include:
- Clear summary of behavior changes.
- Linked issue/task (if available).
- Screenshots or short video for UI changes.
- Notes about `.env` changes; never commit secrets.
