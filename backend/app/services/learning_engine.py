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
    """Exponential decay weight based on record age (half-life = 90 days).

    Returns a value in (0, 1].  Future timestamps (``recorded_at > now``) are
    treated as if they were recorded right now, capping the weight at 1.0.
    """
    age_seconds = max(0.0, time.time() - recorded_at)
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

    def data_quality_report(self) -> dict[str, Any]:
        """Return a data quality summary for governance / observability.

        Checks:
        - total record count
        - fraction of records missing platform / market_code
        - fraction of records with out-of-range conversion_score
        - duplicate video_id count (should be 0 with upsert semantics)
        """
        records = self._records
        total = len(records)
        if total == 0:
            return {
                "ok": True,
                "total_records": 0,
                "missing_platform_pct": 0.0,
                "missing_market_code_pct": 0.0,
                "invalid_score_pct": 0.0,
                "duplicate_video_ids": 0,
                "issues": [],
            }

        missing_platform = sum(1 for r in records if not r.get("platform"))
        missing_market = sum(1 for r in records if not r.get("market_code"))
        invalid_score = sum(
            1 for r in records
            if not (0.0 <= float(r.get("conversion_score", -1)) <= 1.0)
        )

        video_ids = [r.get("video_id") for r in records]
        unique_ids = len(set(video_ids))
        duplicates = total - unique_ids

        issues: list[str] = []
        missing_platform_pct = round(missing_platform / total, 3)
        missing_market_pct = round(missing_market / total, 3)
        invalid_score_pct = round(invalid_score / total, 3)

        if missing_platform_pct > 0.5:
            issues.append(f">{missing_platform_pct*100:.0f}% records missing platform field")
        if missing_market_pct > 0.5:
            issues.append(f">{missing_market_pct*100:.0f}% records missing market_code field")
        if invalid_score_pct > 0:
            issues.append(f"{invalid_score_pct*100:.0f}% records have out-of-range conversion_score")
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate video_id(s) found")

        return {
            "ok": len(issues) == 0,
            "total_records": total,
            "missing_platform_pct": missing_platform_pct,
            "missing_market_code_pct": missing_market_pct,
            "invalid_score_pct": invalid_score_pct,
            "duplicate_video_ids": duplicates,
            "issues": issues,
        }

    def score_drift_summary(
        self,
        *,
        window_days: int = 7,
        baseline_days: int = 30,
    ) -> dict[str, Any]:
        """Detect score drift by comparing a recent window to a longer baseline.

        Returns the mean and std of conversion_score for:
        - ``recent``: records from the last ``window_days`` days
        - ``baseline``: all records up to ``baseline_days`` days old

        The ``drift`` field is ``recent_mean - baseline_mean``.  A large
        negative drift suggests performance is degrading; a large positive
        drift suggests improvement (or score inflation).
        """
        now = time.time()
        recent_cutoff = now - window_days * 86400
        baseline_cutoff = now - baseline_days * 86400

        recent_scores = [
            float(r["conversion_score"])
            for r in self._records
            if float(r.get("recorded_at", 0)) >= recent_cutoff
        ]
        baseline_scores = [
            float(r["conversion_score"])
            for r in self._records
            if float(r.get("recorded_at", 0)) >= baseline_cutoff
        ]

        def _stats(scores: list[float]) -> dict[str, Any]:
            if not scores:
                return {"count": 0, "mean": None, "std": None}
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            return {
                "count": len(scores),
                "mean": round(mean, 4),
                "std": round(variance ** 0.5, 4),
            }

        recent_stats = _stats(recent_scores)
        baseline_stats = _stats(baseline_scores)

        drift: float | None = None
        if recent_stats["mean"] is not None and baseline_stats["mean"] is not None:
            drift = round(recent_stats["mean"] - baseline_stats["mean"], 4)

        alert = (
            drift is not None
            and abs(drift) >= 0.15  # ±15 pp drift triggers an alert
            and recent_stats["count"] >= 3  # require at least a few recent records
        )

        return {
            "recent_window_days": window_days,
            "baseline_days": baseline_days,
            "recent": recent_stats,
            "baseline": baseline_stats,
            "drift": drift,
            "alert": alert,
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
        """Upsert a record into the performance_records DB table.

        This method issues its own ``db.commit()`` so the write is durable
        immediately, independent of any outer transaction.  This is intentional:
        the learning-engine write-back is a side-effect that must not be rolled
        back if the caller's transaction is aborted later.
        """
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
