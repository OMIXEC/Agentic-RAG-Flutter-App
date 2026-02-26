"""Weighted Reciprocal Rank Fusion for multi-source search results.

Migrated from backend/fusion.py — unchanged algorithm, typed more strictly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def weighted_rrf(
    per_source_results: dict[str, list[dict[str, Any]]],
    weights: dict[str, float] | None = None,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Fuse ranked results from multiple sources using weighted RRF.

    Args:
        per_source_results: ``{"text_index": [...], "media_index": [...]}``.
        weights: Per-source weight multiplier (default 1.0).
        k: RRF constant (higher → flatter ranking).

    Returns:
        Unified list sorted by fused score descending.
    """
    weights = weights or {}
    scores: dict[str, float] = defaultdict(float)
    chosen: dict[str, dict[str, Any]] = {}

    for source, results in per_source_results.items():
        w = weights.get(source, 1.0)
        for rank, item in enumerate(results, start=1):
            memory_id = item.get("memory_id")
            if not memory_id:
                continue
            scores[memory_id] += w * (1.0 / (k + rank))
            if memory_id not in chosen:
                chosen[memory_id] = item

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    output: list[dict[str, Any]] = []
    for memory_id, score in ordered:
        row = dict(chosen[memory_id])
        row["fused_score"] = score
        output.append(row)
    return output
