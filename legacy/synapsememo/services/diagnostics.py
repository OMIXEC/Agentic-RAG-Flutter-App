"""Ingestion diagnostics — tracks success/failure counts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IngestDiagnostic:
    success_count: int = 0
    failed_count: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def add_error(
        self, source_uri: str, stage: str, reason: str, provider: str
    ) -> None:
        self.failed_count += 1
        self.errors.append(
            {
                "source_uri": source_uri,
                "stage": stage,
                "reason": reason,
                "provider": provider,
            }
        )

    def add_success(self, count: int = 1) -> None:
        self.success_count += count
