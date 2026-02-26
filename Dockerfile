# ── SynapseMemo Backend ─────────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements-synapsememo.txt .
RUN pip install --no-cache-dir -r requirements-synapsememo.txt

# Copy source
COPY synapsememo/ synapsememo/
COPY providers/ providers/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "synapsememo.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
