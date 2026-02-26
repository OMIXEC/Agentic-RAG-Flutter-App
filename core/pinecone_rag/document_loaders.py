"""Document and media file loaders for RAG ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".xml"}
DOC_EXTENSIONS = {".pdf", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def sha256_hash(text: str) -> str:
    """Compute SHA-256 hash of text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_files(folder: Path, extensions: set[str]) -> list[Path]:
    """Recursively collect files matching given extensions."""
    if not folder.exists():
        return []
    files: list[Path] = []
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            files.append(path)
    return sorted(files)


def read_text_file(path: Path) -> str:
    """Read a text file with automatic encoding detection."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def extract_docx_text(path: Path) -> str:
    """Extract text from a DOCX file."""
    import docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def extract_document_text(path: Path) -> str:
    """Extract text from PDF or DOCX files."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf_text(path)
    if ext == ".docx":
        return extract_docx_text(path)
    return ""


def load_media_manifest(folder: Path) -> dict[str, dict[str, str]]:
    """Load media manifest with descriptions and source URLs.

    Manifest format: filename | description | source_url (one per line).
    """
    manifest_path = folder / "media_manifest.txt"
    if not manifest_path.exists():
        return {}

    data: dict[str, dict[str, str]] = {}
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        data[parts[0]] = {
            "description": parts[1],
            "source_url": parts[2] if len(parts) > 2 else "",
        }
    return data
