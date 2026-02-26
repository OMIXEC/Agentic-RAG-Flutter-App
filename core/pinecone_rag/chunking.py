"""Text chunking strategies for RAG ingestion.

Supports paragraph-based, semantic (sentence-boundary-aware), and
hard-split chunking with configurable overlap.
"""

from __future__ import annotations

import re


def chunk_text(
    text: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """Split text into chunks by paragraph boundaries with optional overlap."""
    chunks: list[str] = []
    pending = ""

    for part in text.split("\n\n"):
        block = part.strip()
        if not block:
            continue

        if len(pending) + len(block) + 2 <= max_chars:
            pending = f"{pending}\n\n{block}".strip()
        else:
            if len(pending) >= min_chars:
                chunks.append(pending)
            pending = block

    if len(pending) >= min_chars:
        chunks.append(pending)

    if overlap_chars > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, overlap_chars)

    return chunks


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex patterns."""
    sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
    sentences = sentence_endings.split(text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_semantic(
    text: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """Chunk text respecting sentence boundaries.

    Groups sentences into chunks that don't exceed max_chars,
    preferring to break at paragraph boundaries when possible.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        sentences = split_sentences(para)

        for sentence in sentences:
            sent_len = len(sentence)

            if current_length + sent_len + 1 <= max_chars:
                current_chunk.append(sentence)
                current_length += sent_len + 1
            else:
                if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
                    chunks.append(" ".join(current_chunk))

                current_chunk = [sentence]
                current_length = sent_len

        if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
            chunk_text_val = " ".join(current_chunk)
            if not chunks or chunks[-1] != chunk_text_val:
                chunks.append(chunk_text_val)
            current_chunk = []
            current_length = 0

    if current_chunk and sum(len(s) for s in current_chunk) >= min_chars:
        chunks.append(" ".join(current_chunk))

    if overlap_chars > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, overlap_chars)

    return chunks


def chunk_text_with_strategy(
    text: str,
    strategy: str,
    max_chars: int = 1200,
    min_chars: int = 80,
    overlap_chars: int = 0,
) -> list[str]:
    """Chunk text using the specified strategy.

    Args:
        text: Input text to chunk
        strategy: Chunking strategy ("paragraph", "semantic", "recursive")
        max_chars: Maximum characters per chunk
        min_chars: Minimum characters for a valid chunk
        overlap_chars: Characters to overlap between adjacent chunks

    Returns:
        List of text chunks
    """
    strategy = (strategy or "paragraph").lower().strip()

    if strategy == "semantic":
        return chunk_semantic(text, max_chars, min_chars, overlap_chars)
    elif strategy == "paragraph":
        return chunk_text(text, max_chars, min_chars, overlap_chars)
    else:
        print(f"Warning: Unknown chunking strategy '{strategy}', using 'paragraph'")
        return chunk_text(text, max_chars, min_chars, overlap_chars)


def hard_split_text(text: str, max_chars: int) -> list[str]:
    """Hard-split text at exact character boundaries."""
    normalized = text.strip()
    if not normalized:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        chunks.append(normalized[cursor : cursor + max_chars])
        cursor += max_chars
    return chunks


def _apply_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    """Apply overlap between adjacent chunks."""
    overlapped: list[str] = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            if i + 1 < len(chunks):
                suffix = chunks[i + 1][:overlap_chars]
                overlapped.append(f"{chunk}\n...{suffix}")
            else:
                overlapped.append(chunk)
        elif i == len(chunks) - 1:
            prefix = chunks[i - 1][-overlap_chars:]
            overlapped.append(f"{prefix}...\n{chunk}")
        else:
            prefix = chunks[i - 1][-overlap_chars:]
            suffix = chunks[i + 1][:overlap_chars]
            overlapped.append(f"{prefix}...\n{chunk}\n...{suffix}")
    return overlapped
