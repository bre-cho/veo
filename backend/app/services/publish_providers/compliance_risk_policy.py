"""ComplianceRiskPolicy — platform-specific content compliance evaluation.

Phase 3.2: Added sponsored_content_disclosure, caption_length_limit,
hashtag_limit, and music_license_check rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Platform rule definitions
# ---------------------------------------------------------------------------

PLATFORM_RULES: dict[str, dict[str, Any]] = {
    "tiktok": {
        "max_duration_seconds": 600,
        "restricted_keywords": [
            "guaranteed", "100% results", "get rich quick",
            "miracle cure", "instant weight loss",
        ],
        "prohibited_categories": ["adult", "violence", "hate_speech", "gambling"],
        "risk_multipliers": {"adult": 1.5, "violence": 1.3},
        # Phase 3.2: extra rules
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 2200,
        "hashtag_limit": 30,
        "music_license_check": True,
    },
    "youtube": {
        "max_duration_seconds": None,  # no hard limit
        "restricted_keywords": [
            "click bait guaranteed", "get rich overnight",
            "miracle diet", "100% profit",
        ],
        "prohibited_categories": ["adult", "hate_speech", "spam"],
        "risk_multipliers": {"adult": 1.5},
        # Phase 3.2
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 5000,
        "hashtag_limit": None,  # YouTube: no official hashtag limit (best practice ≤15)
        "music_license_check": True,
    },
    "reels": {
        "max_duration_seconds": 90,
        "restricted_keywords": [
            "guaranteed profit", "miracle cure",
            "adult only", "violence",
        ],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5, "violence": 1.2},
        # Phase 3.2
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 2200,
        "hashtag_limit": 30,
        "music_license_check": True,
    },
    "instagram": {
        "max_duration_seconds": 60,
        "restricted_keywords": ["adult only", "violence", "hate speech"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5},
        # Phase 3.2
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 2200,
        "hashtag_limit": 30,
        "music_license_check": True,
    },
    "meta": {
        "max_duration_seconds": None,
        "restricted_keywords": ["hate speech", "violence", "adult content"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5, "violence": 1.2},
        # Phase 3.2
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 2200,
        "hashtag_limit": 30,
        "music_license_check": True,
    },
    "facebook": {
        "max_duration_seconds": None,
        "restricted_keywords": ["hate speech", "violence", "adult only"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {},
        # Phase 3.2
        "sponsored_content_disclosure_required": True,
        "caption_length_limit": 2200,
        "hashtag_limit": 30,
        "music_license_check": True,
    },
}

_DEFAULT_RULES: dict[str, Any] = {
    "max_duration_seconds": None,
    "restricted_keywords": [],
    "prohibited_categories": ["adult", "violence", "hate_speech"],
    "risk_multipliers": {},
    "sponsored_content_disclosure_required": False,
    "caption_length_limit": None,
    "hashtag_limit": None,
    "music_license_check": False,
}

# Base risk score increments
_RESTRICTED_KEYWORD_INCREMENT = 0.20
_PROHIBITED_CATEGORY_INCREMENT = 0.40
_DURATION_EXCEEDED_INCREMENT = 0.30
_COMPLIANCE_VIOLATION_INCREMENT = 0.25


@dataclass
class ComplianceResult:
    """Result of a compliance policy evaluation."""

    compliance_status: str  # "passed" | "review" | "failed"
    risk_score: float  # 0.0 – 1.0
    risk_flags: list[str] = field(default_factory=list)
    platform: str = ""
    tier: str = "standard"
    # Phase 3.2: severity-tagged preflight errors
    preflight_errors: list[dict[str, str]] = field(default_factory=list)


class ComplianceRiskPolicy:
    """Evaluate content against platform-specific compliance rules.

    ``evaluate()`` checks keywords, categories, duration constraints,
    sponsored disclosure, caption length, hashtag limits, and music license.
    The result is:
    - ``passed``:  risk_score < 0.40
    - ``review``:  0.40 <= risk_score < 0.70
    - ``failed``:  risk_score >= 0.70 or prohibited category present
    """

    def evaluate(
        self,
        content: dict[str, Any],
        platform: str,
        tier: str = "standard",
    ) -> ComplianceResult:
        """Evaluate content against platform compliance rules."""
        rules = PLATFORM_RULES.get(platform.lower(), _DEFAULT_RULES)
        risk_flags: list[str] = []
        preflight_errors: list[dict[str, str]] = []
        risk_score: float = 0.0
        failed = False

        text_fields = " ".join([
            str(content.get("title", "")),
            str(content.get("description", "")),
            str(content.get("caption", "")),
            " ".join(str(t) for t in content.get("tags", [])),
        ]).lower()

        # --- Restricted keywords ---
        for kw in rules.get("restricted_keywords", []):
            if kw.lower() in text_fields:
                risk_flags.append(f"restricted_keyword:{kw}")
                risk_score += _RESTRICTED_KEYWORD_INCREMENT

        # --- Prohibited categories ---
        content_categories: list[str] = content.get("categories", [])
        for cat in content_categories:
            if cat.lower() in rules.get("prohibited_categories", []):
                risk_flags.append(f"prohibited_category:{cat}")
                multiplier = rules.get("risk_multipliers", {}).get(cat.lower(), 1.0)
                risk_score += _PROHIBITED_CATEGORY_INCREMENT * multiplier
                failed = True  # prohibited category always fails

        # --- Duration check ---
        max_dur = rules.get("max_duration_seconds")
        content_duration = content.get("duration_seconds")
        if max_dur is not None and content_duration is not None:
            if float(content_duration) > float(max_dur):
                risk_flags.append(f"duration_exceeded:{content_duration}>{max_dur}")
                risk_score += _DURATION_EXCEEDED_INCREMENT

        # --- Adult content flag ---
        if content.get("adult_content", False):
            risk_flags.append("adult_content_flag")
            risk_score += 0.50
            failed = True

        # --- Phase 3.2: Sponsored content disclosure ---
        if (
            rules.get("sponsored_content_disclosure_required")
            and content.get("is_paid_partnership", False)
        ):
            caption_text = str(content.get("caption", ""))
            has_disclosure = any(
                kw in caption_text.lower()
                for kw in ("#ad", "#sponsored", "#paidpartnership", "paid partnership")
            )
            if not has_disclosure:
                flag = "missing_sponsored_content_disclosure"
                risk_flags.append(flag)
                preflight_errors.append({"code": flag, "severity": "error"})
                risk_score += _COMPLIANCE_VIOLATION_INCREMENT

        # --- Phase 3.2: Caption length limit ---
        caption_limit = rules.get("caption_length_limit")
        if caption_limit is not None:
            caption = str(content.get("caption", ""))
            if len(caption) > caption_limit:
                flag = f"caption_too_long:{len(caption)}>{caption_limit}"
                risk_flags.append(flag)
                preflight_errors.append({"code": "caption_length_exceeded", "severity": "warning"})
                risk_score += _COMPLIANCE_VIOLATION_INCREMENT * 0.5

        # --- Phase 3.2: Hashtag limit ---
        hashtag_limit = rules.get("hashtag_limit")
        if hashtag_limit is not None:
            caption_for_tags = str(content.get("caption", "")) + " " + " ".join(
                str(t) for t in content.get("tags", [])
            )
            hashtags = [w for w in caption_for_tags.split() if w.startswith("#")]
            if len(hashtags) > hashtag_limit:
                flag = f"hashtag_limit_exceeded:{len(hashtags)}>{hashtag_limit}"
                risk_flags.append(flag)
                preflight_errors.append({"code": "hashtag_limit_exceeded", "severity": "warning"})
                risk_score += _COMPLIANCE_VIOLATION_INCREMENT * 0.4

        # --- Phase 3.2: Music license check ---
        if rules.get("music_license_check") and content.get("has_background_music", False):
            if not content.get("music_licensed", False):
                flag = "unlicensed_music"
                risk_flags.append(flag)
                preflight_errors.append({"code": flag, "severity": "error"})
                risk_score += _COMPLIANCE_VIOLATION_INCREMENT
                failed = True

        risk_score = round(min(risk_score, 1.0), 3)

        if failed or risk_score >= 0.70:
            status = "failed"
        elif risk_score >= 0.40:
            status = "review"
        else:
            status = "passed"

        return ComplianceResult(
            compliance_status=status,
            risk_score=risk_score,
            risk_flags=risk_flags,
            platform=platform,
            tier=tier,
            preflight_errors=preflight_errors,
        )

