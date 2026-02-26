from collections import defaultdict
from typing import Any


def weighted_rrf(
    per_source_results: dict[str, list[dict[str, Any]]],
    weights: dict[str, float] | None = None,
    k: int = 60,
) -> list[dict[str, Any]]:
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
