# App (Flutter) - RAG Human Mind v2.1

This Flutter app supports:
- Retrieval chat via backend API (`/v1/memories/chat`)
- Personal memory capture and recall
- Multimodal chat by adding an optional image URL
- Provider fallback for modern model stacks

## Run
```bash
flutter pub get
flutter run
```

## Required `.env` keys
```env
BACKEND_API_BASE_URL=http://localhost:8000
BACKEND_AUTH_TOKEN=
```

`BACKEND_AUTH_TOKEN` must be a valid JWT accepted by backend (`JWT_SECRET`, `JWT_AUDIENCE`, `JWT_ISSUER`).
