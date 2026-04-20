from __future__ import annotations

import json
import os
import time
from typing import Any

# ---------------------------------------------------------------------------
# Storage path (configurable via env var so tests can override)
# ---------------------------------------------------------------------------
_DEFAULT_STORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "learning_engine_store.json"
)
_STORE_PATH = os.environ.get("LEARNING_ENGINE_STORE_PATH", _DEFAULT_STORE_PATH)

# ---------------------------------------------------------------------------
# Scoring weights used when updating patterns
# ---------------------------------------------------------------------------
_SCORE_THRESHOLD_HIGH = 0.70
_SCORE_THRESHOLD_LOW = 0.40


class PerformanceLearningEngine:
    """Stores video performance data and updates hook / CTA patterns.

    Storage is a simple JSON file so the service is stateless between
    process restarts and requires no DB.  Production systems can swap
    ``_store_path`` for any durable backend.

    Record schema:
        {
            "video_id": str,
            "hook_pattern": str,
            "cta_pattern": str,
            "template_family": str,
            "conversion_score": float,
            "view_count": int,
            "click_through_rate": float,
            "recorded_at": float  (UNIX timestamp)
        }
    """

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or _STORE_PATH
        self._records: list[dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        video_id: str,
        hook_pattern: str,
        cta_pattern: str,
        template_family: str,
        conversion_score: float,
        view_count: int = 0,
        click_through_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Persist a performance record and return it."""
        record: dict[str, Any] = {
            "video_id": video_id,
            "hook_pattern": hook_pattern,
            "cta_pattern": cta_pattern,
            "template_family": template_family,
            "conversion_score": conversion_score,
            "view_count": view_count,
            "click_through_rate": click_through_rate,
            "recorded_at": time.time(),
        }
        # Upsert by video_id
        self._records = [r for r in self._records if r.get("video_id") != video_id]
        self._records.append(record)
        self._save()
        return record

    def top_hook_patterns(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return top hook patterns by average conversion score."""
        return self._top_patterns("hook_pattern", limit=limit)

    def top_cta_patterns(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return top CTA patterns by average conversion score."""
        return self._top_patterns("cta_pattern", limit=limit)

    def top_template_families(self, *, limit: int = 5) -> list[dict[str, Any]]:
        """Return top template families by average conversion score."""
        return self._top_patterns("template_family", limit=limit)

    def feedback_summary(self) -> dict[str, Any]:
        """Return an aggregated summary for the recommendation engine."""
        if not self._records:
            return {
                "total_records": 0,
                "top_hook_patterns": [],
                "top_cta_patterns": [],
                "top_template_families": [],
                "avg_conversion_score": 0.0,
            }

        avg_score = sum(r["conversion_score"] for r in self._records) / len(self._records)
        return {
            "total_records": len(self._records),
            "top_hook_patterns": self.top_hook_patterns(limit=3),
            "top_cta_patterns": self.top_cta_patterns(limit=3),
            "top_template_families": self.top_template_families(limit=3),
            "avg_conversion_score": round(avg_score, 3),
        }

    def all_records(self) -> list[dict[str, Any]]:
        return list(self._records)

    def clear(self) -> None:
        """Remove all stored records (primarily for testing)."""
        self._records = []
        self._save()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _top_patterns(self, field: str, *, limit: int) -> list[dict[str, Any]]:
        aggregated: dict[str, list[float]] = {}
        for record in self._records:
            key = record.get(field, "")
            if not key:
                continue
            aggregated.setdefault(key, []).append(record["conversion_score"])

        results = [
            {
                "pattern": k,
                "avg_score": round(sum(v) / len(v), 3),
                "sample_count": len(v),
            }
            for k, v in aggregated.items()
        ]
        results.sort(key=lambda x: x["avg_score"], reverse=True)
        return results[:limit]

    def _load(self) -> None:
        try:
            if os.path.exists(self._store_path):
                with open(self._store_path, encoding="utf-8") as fh:
                    self._records = json.load(fh)
        except (OSError, json.JSONDecodeError):
            self._records = []

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "w", encoding="utf-8") as fh:
                json.dump(self._records, fh, indent=2)
        except OSError:
            pass  # Non-fatal — in-memory store still works
