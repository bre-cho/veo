from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # Session imported lazily inside historical_boost to avoid circular deps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Product category → expected conversion signal boosters
# ---------------------------------------------------------------------------
_CATEGORY_SIGNALS: dict[str, float] = {
    "skincare": 0.80,
    "fitness": 0.78,
    "food": 0.72,
    "technology": 0.75,
    "fashion": 0.76,
    "health": 0.80,
    "education": 0.74,
    "finance": 0.72,
}

# Platform-specific weight for conversion intent signals
_PLATFORM_INTENT_SIGNALS: dict[str, float] = {
    "tiktok": 0.82,
    "shorts": 0.80,
    "reels": 0.80,
    "youtube": 0.74,
    "facebook": 0.72,
    "instagram": 0.78,
}

# Funnel stage → copy signal keywords for fit scoring
_FUNNEL_AWARENESS_SIGNALS = ("imagine", "story", "what if", "discover", "?")
_FUNNEL_AWARENESS_PENALTY_SIGNALS = ("buy", "order", "purchase", "claim")
_FUNNEL_CONSIDERATION_SIGNALS = ("review", "compare", "trusted", "proven", "vs", "better")
_FUNNEL_CONVERSION_SIGNALS = ("buy", "tap", "start", "claim", "order", "shop", "now", "today")
_FUNNEL_RETENTION_SIGNALS = ("exclusive", "loyalty", "member", "community", "thank")

# Funnel stage → score multiplier applied to overall composite score
_FUNNEL_STAGE_MULTIPLIERS: dict[str, float] = {
    "awareness": 0.85,   # early stage: penalise hard-sell signals
    "consideration": 1.0,
    "conversion": 1.10,  # bottom-of-funnel: reward CTA / urgency signals
    "retention": 0.95,
}

# Minimum R² to consider calibrated weights "reliable enough"
_MIN_CALIBRATION_R2 = 0.10


class ConversionScoringEngine:
    def score_variant(
        self,
        variant: dict[str, Any],
        market_code: str | None = None,
        persona: str | None = None,
        product_category: str | None = None,
        platform: str | None = None,
        funnel_stage: str | None = None,
        campaign_id: str | None = None,
        calibration_store: "Any | None" = None,
    ) -> dict[str, Any]:
        text = " ".join(
            [
                str(variant.get("hook") or ""),
                str(variant.get("body") or ""),
                str(variant.get("cta") or ""),
            ]
        ).lower()

        hook_strength = 0.8 if any(x in text for x in ("?", "did you know", "secret", "stop")) else 0.55
        clarity = 0.75 if len(text.split()) < 120 else 0.55
        trust = 0.8 if any(x in text for x in ("customer", "review", "trusted", "proven")) else 0.6
        cta_quality = 0.85 if any(x in text for x in ("buy", "tap", "start", "claim", "order", "shop")) else 0.5
        market_fit = 0.75 if market_code else 0.65

        # New dimension: persona_fit
        persona_fit = self._score_persona_fit(text, persona)

        # New dimension: product_category_fit
        product_category_fit = self._score_category_fit(product_category)

        # New dimension: platform_fit
        platform_fit = self._score_platform_fit(text, platform)

        # New dimension: funnel_stage_fit
        funnel_stage_fit = self._score_funnel_stage_fit(text, funnel_stage)

        dimensions = {
            "hook_strength": hook_strength,
            "clarity": clarity,
            "trust": trust,
            "cta_quality": cta_quality,
            "market_fit": market_fit,
            "persona_fit": persona_fit,
            "product_category_fit": product_category_fit,
            "platform_fit": platform_fit,
            "funnel_stage_fit": funnel_stage_fit,
        }

        # Campaign-fit: reward when variant explicitly references campaign context
        campaign_fit: float | None = None
        if campaign_id:
            cid_lower = str(campaign_id).lower()
            campaign_fit = 0.85 if cid_lower in text or "campaign" in text else 0.65
            dimensions["campaign_fit"] = campaign_fit

        # Load calibration weights.  When calibration is available, enforce its
        # use.  When absent, log a warning and fall back to equal weights.
        calibrated_weights: dict[str, float] | None = None
        calibration_r2: float | None = None
        if calibration_store is not None:
            try:
                calibrated_weights = calibration_store.get_dimension_weights(
                    platform=platform, product_category=product_category
                )
                calibration_r2 = getattr(calibration_store, "last_r2", None)
            except Exception as exc:
                logger.warning(
                    "ConversionScoringEngine: calibration load failed (%s) — "
                    "using equal-weight fallback",
                    exc,
                )
                calibrated_weights = None

        if calibrated_weights:
            # Confidence weight: scale by how reliable calibration is (R²-based)
            r2 = calibration_r2 if calibration_r2 is not None else 0.5
            confidence = max(0.0, min(1.0, r2))
            # Blend calibrated weights with equal-weight fallback proportionally to R²
            n = len(dimensions)
            equal_w = 1.0 / n
            blended_weights = {
                k: round(confidence * calibrated_weights.get(k, equal_w) + (1 - confidence) * equal_w, 4)
                for k in dimensions
            }
            score = round(
                sum(blended_weights.get(k, equal_w) * v for k, v in dimensions.items()),
                3,
            )
        else:
            # No calibration available — emit warning and use equal weights
            if calibration_store is not None:
                logger.warning(
                    "ConversionScoringEngine: no persisted calibration found for "
                    "platform=%s category=%s; using equal-weight scoring",
                    platform,
                    product_category,
                )
            n = len(dimensions)
            score = round(sum(dimensions.values()) / n, 3)
            confidence = 0.0

        # Apply funnel-stage multiplier AFTER base score is computed
        funnel_multiplier = _FUNNEL_STAGE_MULTIPLIERS.get(
            (funnel_stage or "").lower(), 1.0
        )
        score = round(min(1.0, score * funnel_multiplier), 3)

        return {
            "score": score,
            "details": {k: round(v, 3) for k, v in dimensions.items()},
            "calibrated": calibrated_weights is not None,
            "calibration_confidence": round(confidence, 3),
            "funnel_stage": funnel_stage,
            "funnel_multiplier": funnel_multiplier,
            "campaign_id": campaign_id,
            "campaign_fit": campaign_fit,
        }

    # ------------------------------------------------------------------
    # New scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_funnel_stage_fit(text: str, funnel_stage: str | None) -> float:
        """Score how well the variant copy fits the target funnel stage."""
        if not funnel_stage:
            return 0.68
        stage = funnel_stage.lower()
        if stage == "awareness":
            # Awareness: storytelling, problem framing — penalise hard sell
            has_story = any(w in text for w in _FUNNEL_AWARENESS_SIGNALS)
            has_hard_sell = any(w in text for w in _FUNNEL_AWARENESS_PENALTY_SIGNALS)
            score = 0.80 if has_story else 0.65
            if has_hard_sell:
                score = max(score - 0.10, 0.50)
            return score
        if stage == "consideration":
            # Consideration: features, comparison, social proof
            has_proof = any(w in text for w in _FUNNEL_CONSIDERATION_SIGNALS)
            return 0.82 if has_proof else 0.68
        if stage == "conversion":
            # Conversion: CTA urgency, offer
            has_cta = any(w in text for w in _FUNNEL_CONVERSION_SIGNALS)
            return 0.88 if has_cta else 0.60
        if stage == "retention":
            # Retention: loyalty, community, value
            has_retention = any(w in text for w in _FUNNEL_RETENTION_SIGNALS)
            return 0.80 if has_retention else 0.65
        return 0.68

    @staticmethod
    def _score_persona_fit(text: str, persona: str | None) -> float:
        """Score how well the variant copy targets the intended persona."""
        if not persona:
            return 0.65  # neutral when unknown
        persona_lower = persona.lower()
        # Direct mention of persona label in copy
        if persona_lower in text:
            return 0.90
        # General persona category signals
        persona_signals = {
            "professional": ("professional", "business", "work", "team", "company"),
            "student": ("student", "learn", "study", "skill"),
            "parent": ("parent", "family", "mom", "dad", "child"),
            "entrepreneur": ("entrepreneur", "grow", "scale", "startup", "revenue"),
            "athlete": ("athlete", "fitness", "performance", "training", "results"),
        }
        for key, signals in persona_signals.items():
            if key in persona_lower:
                if any(s in text for s in signals):
                    return 0.80
        return 0.65

    @staticmethod
    def _score_category_fit(product_category: str | None) -> float:
        """Return base conversion expectation for this product category."""
        if not product_category:
            return 0.68
        return _CATEGORY_SIGNALS.get(product_category.lower(), 0.68)

    @staticmethod
    def _score_platform_fit(text: str, platform: str | None) -> float:
        """Score how well the variant's language fits the target platform."""
        if not platform:
            return 0.68
        platform_lower = platform.lower()
        base = _PLATFORM_INTENT_SIGNALS.get(platform_lower, 0.70)
        # Short-form platforms reward short punchy copy
        if platform_lower in ("tiktok", "shorts", "reels"):
            word_count = len(text.split())
            if word_count < 80:
                base = min(base + 0.05, 1.0)
            elif word_count > 150:
                base = max(base - 0.05, 0.0)
        # Long-form platforms (YouTube) reward more detailed copy
        elif platform_lower == "youtube":
            word_count = len(text.split())
            if word_count > 100:
                base = min(base + 0.04, 1.0)
        return base

    @staticmethod
    def historical_boost(
        variant_type: str,
        product_category: str | None = None,
        platform: str | None = None,
        persona_id: str | None = None,
        campaign_id: str | None = None,
        funnel_stage: str | None = None,
        db: "Any | None" = None,
    ) -> float:
        """Compute an EWMA-based score adjustment from historical outcomes.

        Queries ``VariantRunRecord`` rows that have an ``actual_conversion_score``
        recorded and computes an exponentially-weighted moving average for the
        given ``variant_type`` + optional filters.

        Returns a value in [-0.1, +0.1]:
        - positive when history shows above-average conversion
        - negative when history shows below-average conversion
        - 0.0 when insufficient data or no DB session
        """
        if db is None:
            return 0.0
        try:
            from app.models.variant_run_record import VariantRunRecord
            from datetime import datetime, timedelta, timezone

            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=60)
            query = (
                db.query(VariantRunRecord)
                .filter(
                    VariantRunRecord.actual_conversion_score.isnot(None),
                    VariantRunRecord.recorded_at >= cutoff,
                )
            )
            if product_category:
                query = query.filter(VariantRunRecord.product_category == product_category)
            if platform:
                query = query.filter(VariantRunRecord.platform == platform)
            rows = query.all()

            # Filter to rows whose winning variant matches the requested type,
            # and apply persona_id / campaign_id / funnel_stage context filters
            relevant_scores: list[float] = []
            for row in rows:
                ctx = dict(row.context or {})
                # persona_id filter via context
                if persona_id and ctx.get("persona_id") not in (None, persona_id):
                    continue
                # campaign_id filter via context
                if campaign_id and ctx.get("campaign_id") not in (None, str(campaign_id)):
                    continue
                # funnel_stage filter via context
                if funnel_stage and ctx.get("funnel_stage") not in (None, funnel_stage):
                    continue
                winner_idx = row.winner_variant_index
                variants = row.variants or []
                winning_v = next(
                    (v for v in variants if v.get("variant_index") == winner_idx), None
                )
                if winning_v and winning_v.get("variant_type") == variant_type:
                    if row.actual_conversion_score is not None:
                        relevant_scores.append(float(row.actual_conversion_score))

            if not relevant_scores:
                return 0.0

            # EWMA: more recent scores get higher weight
            import math
            ewma = 0.0
            weight_sum = 0.0
            for i, score in enumerate(relevant_scores):
                w = math.exp(-0.1 * (len(relevant_scores) - 1 - i))
                ewma += score * w
                weight_sum += w
            if weight_sum > 0:
                ewma /= weight_sum

            # Map EWMA to [-0.1, +0.1] centred on 0.65 (neutral)
            raw = (ewma - 0.65) * (0.1 / 0.35)
            return round(max(-0.1, min(0.1, raw)), 4)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Weight calibration
    # ------------------------------------------------------------------

    _CALIBRATION_MIN_RECORDS = 30
    _DIMENSION_NAMES = (
        "hook_strength", "clarity", "trust", "cta_quality",
        "market_fit", "persona_fit", "product_category_fit", "platform_fit",
        "funnel_stage_fit",
    )

    @classmethod
    def calibrate_weights(
        cls,
        db: "Any",
        platform: str | None = None,
        product_category: str | None = None,
        funnel_stage: str | None = None,
    ) -> dict[str, Any]:
        """Compute optimal scoring weights from historical conversion data.

        Uses least-squares linear regression over ``VariantRunRecord`` rows
        that have ``actual_conversion_score`` recorded.  When ≥30 records are
        available the computed weights are persisted to ``ScoringCalibration``
        and returned.

        Performs segment-level calibration keyed by
        ``(platform, product_category, funnel_stage)`` in addition to the
        combined calibration.

        Returns a dict with:
        - ``weights``: calibrated weight dict
        - ``segment_key``: str identifying the calibration segment
        - ``n_records``: int — records used
        - ``fit_quality``: float — R² of the fit
        """
        defaults = {d: round(1.0 / len(cls._DIMENSION_NAMES), 4) for d in cls._DIMENSION_NAMES}
        segment_key = f"{platform or 'all'}|{product_category or 'all'}|{funnel_stage or 'all'}"
        try:
            from app.models.variant_run_record import VariantRunRecord
            from app.models.scoring_calibration import ScoringCalibration
            from datetime import datetime, timezone

            query = db.query(VariantRunRecord).filter(
                VariantRunRecord.actual_conversion_score.isnot(None)
            )
            if platform:
                query = query.filter(VariantRunRecord.platform == platform)
            if product_category:
                query = query.filter(VariantRunRecord.product_category == product_category)
            rows = query.all()

            # Segment-level filter by funnel_stage (stored in context JSON)
            if funnel_stage:
                rows = [
                    r for r in rows
                    if (dict(r.context or {})).get("funnel_stage") == funnel_stage
                ]

            if len(rows) < cls._CALIBRATION_MIN_RECORDS:
                return {"weights": defaults, "segment_key": segment_key, "n_records": len(rows), "fit_quality": 0.0}

            # Build X (feature matrix) and y (target) from winner variants
            X: list[list[float]] = []
            y: list[float] = []
            for row in rows:
                winner_idx = row.winner_variant_index
                variants = row.variants or []
                winning_v = next(
                    (v for v in variants if v.get("variant_index") == winner_idx), None
                )
                if winning_v is None:
                    continue
                breakdown: dict = winning_v.get("score_breakdown") or {}
                features = [float(breakdown.get(d, 0.5)) for d in cls._DIMENSION_NAMES]
                X.append(features)
                y.append(float(row.actual_conversion_score))

            if len(X) < cls._CALIBRATION_MIN_RECORDS:
                return {"weights": defaults, "segment_key": segment_key, "n_records": len(X), "fit_quality": 0.0}

            # Ordinary least squares: w = (X^T X)^{-1} X^T y
            n = len(cls._DIMENSION_NAMES)
            XtX = [[0.0] * n for _ in range(n)]
            Xty = [0.0] * n
            for xi, yi in zip(X, y):
                for i in range(n):
                    Xty[i] += xi[i] * yi
                    for j in range(n):
                        XtX[i][j] += xi[i] * xi[j]

            w = _solve_lstsq(XtX, Xty, n)
            if w is None:
                return {"weights": defaults, "segment_key": segment_key, "n_records": len(X), "fit_quality": 0.0}

            # Normalise weights to [0.05, 0.4] range and sum to 1
            total_w = sum(abs(wi) for wi in w) or 1.0
            calibrated = {
                d: max(0.05, min(0.40, round(abs(w[i]) / total_w, 4)))
                for i, d in enumerate(cls._DIMENSION_NAMES)
            }
            cw_sum = sum(calibrated.values())
            calibrated = {k: round(v / cw_sum, 4) for k, v in calibrated.items()}

            # Compute R²
            y_mean = sum(y) / len(y)
            ss_tot = sum((yi - y_mean) ** 2 for yi in y)
            y_hat = [sum(calibrated[d] * xi[i] for i, d in enumerate(cls._DIMENSION_NAMES)) for xi in X]
            ss_res = sum((yi - yh) ** 2 for yi, yh in zip(y, y_hat))
            r_sq = round(1.0 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0

            # Persist calibration (keyed by platform + product_category + funnel_stage)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            existing = (
                db.query(ScoringCalibration)
                .filter(
                    ScoringCalibration.platform == platform,
                    ScoringCalibration.product_category == product_category,
                )
                .first()
            )
            if existing is not None:
                existing.weights = calibrated
                existing.sample_count = len(X)
                existing.r_squared = r_sq
                existing.calibrated_at = now
                db.add(existing)
            else:
                db.add(ScoringCalibration(
                    platform=platform,
                    product_category=product_category,
                    weights=calibrated,
                    sample_count=len(X),
                    r_squared=r_sq,
                    calibrated_at=now,
                ))
            db.commit()
            return {
                "weights": calibrated,
                "segment_key": segment_key,
                "n_records": len(X),
                "fit_quality": r_sq,
            }
        except Exception:
            return {"weights": defaults, "segment_key": segment_key, "n_records": 0, "fit_quality": 0.0}

    @classmethod
    def load_calibrated_weights(
        cls,
        db: "Any | None",
        platform: str | None = None,
        product_category: str | None = None,
    ) -> dict[str, float] | None:
        """Load persisted calibrated weights from DB, or None if unavailable."""
        if db is None:
            return None
        try:
            from app.models.scoring_calibration import ScoringCalibration
            from datetime import datetime, timedelta, timezone

            row = (
                db.query(ScoringCalibration)
                .filter(
                    ScoringCalibration.platform == platform,
                    ScoringCalibration.product_category == product_category,
                )
                .order_by(ScoringCalibration.calibrated_at.desc())
                .first()
            )
            if row is None:
                return None
            # Staleness check: warn if calibration is >7 days old (but still use it)
            age_days = (
                datetime.now(timezone.utc).replace(tzinfo=None) - row.calibrated_at
            ).days
            if age_days > 7:
                import logging
                logging.getLogger(__name__).warning(
                    "ScoringCalibration for platform=%s category=%s is %d days old",
                    platform, product_category, age_days,
                )
            return row.weights
        except Exception:
            return None


def _solve_lstsq(A: list[list[float]], b: list[float], n: int) -> list[float] | None:
    """Gaussian elimination to solve A*w = b.  Returns w or None on failure."""
    # Augmented matrix
    M = [A[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if abs(M[row][col]) > 1e-12:
                pivot = row
                break
        if pivot is None:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        scale = M[col][col]
        M[col] = [v / scale for v in M[col]]
        for row in range(n):
            if row != col:
                factor = M[row][col]
                M[row] = [M[row][j] - factor * M[col][j] for j in range(n + 1)]
    return [M[i][n] for i in range(n)]
