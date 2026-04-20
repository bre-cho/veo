from __future__ import annotations

import json
import math
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Storage path (configurable via env var so tests can override)
# ---------------------------------------------------------------------------
_DEFAULT_STORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "learning_engine_store.json"
)
_STORE_PATH = os.environ.get("LEARNING_ENGINE_STORE_PATH", _DEFAULT_STORE_PATH)

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------
_SCORE_THRESHOLD_HIGH = 0.70
_SCORE_THRESHOLD_LOW = 0.40

# ---------------------------------------------------------------------------
# Time-decay configuration
# Half-life of 90 days: records from 90 days ago carry half the weight of
# today's records; records from 180 days ago carry a quarter, and so on.
# ---------------------------------------------------------------------------
_HALF_LIFE_DAYS = 90.0


def _time_weight(recorded_at: float) -> float:
    """Exponential decay weight based on record age (half-life = 90 days)."""
    age_seconds = time.time() - recorded_at
    age_days = age_seconds / 86400.0
    return math.pow(0.5, age_days / _HALF_LIFE_DAYS)


class PerformanceLearningEngine:
    """Stores video performance data and updates hook / CTA patterns.

    Storage is a JSON file (stateless between restarts, zero-dependency).
    When a SQLAlchemy ``Session`` is supplied at construction time the engine
    **dual-writes** every record to the ``performance_records`` table so ops
    tooling and analytics queries can operate on a real database.

    Record schema (JSON store):
        {
            "video_id": str,
            "hook_pattern": str,
            "cta_pattern": str,
            "template_family": str,
            "conversion_score": float,
            "view_count": int,
            "click_through_rate": float,
            "platform": str | null,
            "market_code": str | null,
            "recorded_at": float  (UNIX timestamp)
        }
    """

    def __init__(
        self,
        store_path: str | None = None,
        db: "Session | None" = None,
    ) -> None:
        self._store_path = store_path or _STORE_PATH
        self._db = db
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
        platform: str | None = None,
        market_code: str | None = None,
    ) -> dict[str, Any]:
        """Persist a performance record and return it.

        When the engine was constructed with a DB session the record is also
        upserted into the ``performance_records`` table.
        """
        rec: dict[str, Any] = {
            "video_id": video_id,
            "hook_pattern": hook_pattern,
            "cta_pattern": cta_pattern,
            "template_family": template_family,
            "conversion_score": conversion_score,
            "view_count": view_count,
            "click_through_rate": click_through_rate,
            "platform": platform,
            "market_code": market_code,
            "recorded_at": time.time(),
        }
        # Upsert by video_id in the JSON store
        self._records = [r for r in self._records if r.get("video_id") != video_id]
        self._records.append(rec)
        self._save()

        # Dual-write to DB when session is available
        if self._db is not None:
            self._db_upsert(rec)

        return rec

    def top_hook_patterns(
        self,
        *,
        limit: int = 5,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top hook patterns by time-weighted conversion score."""
        return self._top_patterns(
            "hook_pattern", limit=limit, platform=platform, market_code=market_code
        )

    def top_cta_patterns(
        self,
        *,
        limit: int = 5,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top CTA patterns by time-weighted conversion score."""
        return self._top_patterns(
            "cta_pattern", limit=limit, platform=platform, market_code=market_code
        )

    def top_template_families(
        self,
        *,
        limit: int = 5,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top template families by time-weighted conversion score."""
        return self._top_patterns(
            "template_family", limit=limit, platform=platform, market_code=market_code
        )

    def feedback_summary(
        self,
        *,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> dict[str, Any]:
        """Return an aggregated summary for the recommendation engine."""
        filtered = self._filter_records(platform=platform, market_code=market_code)
        if not filtered:
            return {
                "total_records": 0,
                "top_hook_patterns": [],
                "top_cta_patterns": [],
                "top_template_families": [],
                "avg_conversion_score": 0.0,
            }

        avg_score = sum(r["conversion_score"] for r in filtered) / len(filtered)
        return {
            "total_records": len(filtered),
            "top_hook_patterns": self.top_hook_patterns(
                limit=3, platform=platform, market_code=market_code
            ),
            "top_cta_patterns": self.top_cta_patterns(
                limit=3, platform=platform, market_code=market_code
            ),
            "top_template_families": self.top_template_families(
                limit=3, platform=platform, market_code=market_code
            ),
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

    def _filter_records(
        self,
        *,
        platform: str | None,
        market_code: str | None,
    ) -> list[dict[str, Any]]:
        """Return records matching the optional platform/market_code filters."""
        records = self._records
        if platform:
            records = [r for r in records if r.get("platform") == platform]
        if market_code:
            records = [r for r in records if r.get("market_code") == market_code]
        return records

    def _top_patterns(
        self,
        field: str,
        *,
        limit: int,
        platform: str | None = None,
        market_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate patterns using time-weighted conversion scores.

        Each record's contribution is weighted by exponential decay so recent
        records have more influence than older ones (half-life = 90 days).
        """
        records = self._filter_records(platform=platform, market_code=market_code)
        # aggregated: pattern -> list of (score, weight) tuples
        aggregated: dict[str, list[tuple[float, float]]] = {}
        for rec in records:
            key = rec.get(field, "")
            if not key:
                continue
            w = _time_weight(float(rec.get("recorded_at") or time.time()))
            aggregated.setdefault(key, []).append((float(rec["conversion_score"]), w))

        results: list[dict[str, Any]] = []
        for pattern, pairs in aggregated.items():
            total_weight = sum(w for _, w in pairs)
            if total_weight < 1e-9:
                continue
            weighted_avg = sum(s * w for s, w in pairs) / total_weight
            results.append(
                {
                    "pattern": pattern,
                    "avg_score": round(weighted_avg, 3),
                    "sample_count": len(pairs),
                }
            )
        results.sort(key=lambda x: x["avg_score"], reverse=True)
        return results[:limit]

    def _db_upsert(self, rec: dict[str, Any]) -> None:
        """Upsert a record into the performance_records DB table."""
        try:
            from datetime import datetime, timezone

            from app.models.performance_record import PerformanceRecord

            db = self._db
            existing = (
                db.query(PerformanceRecord)
                .filter(PerformanceRecord.video_id == rec["video_id"])
                .first()
            )
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if existing is not None:
                existing.hook_pattern = rec["hook_pattern"]
                existing.cta_pattern = rec["cta_pattern"]
                existing.template_family = rec["template_family"]
                existing.conversion_score = rec["conversion_score"]
                existing.view_count = rec.get("view_count", 0)
                existing.click_through_rate = rec.get("click_through_rate", 0.0)
                existing.platform = rec.get("platform")
                existing.market_code = rec.get("market_code")
                existing.recorded_at = now
                existing.updated_at = now
                db.add(existing)
            else:
                row = PerformanceRecord(
                    video_id=rec["video_id"],
                    hook_pattern=rec["hook_pattern"],
                    cta_pattern=rec["cta_pattern"],
                    template_family=rec["template_family"],
                    conversion_score=rec["conversion_score"],
                    view_count=rec.get("view_count", 0),
                    click_through_rate=rec.get("click_through_rate", 0.0),
                    platform=rec.get("platform"),
                    market_code=rec.get("market_code"),
                    recorded_at=now,
                )
                db.add(row)
            db.commit()
        except Exception:
            pass  # Non-fatal – DB write-back must never corrupt the JSON store

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
