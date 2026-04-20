"""ComplianceRiskPolicy — platform-specific content compliance evaluation."""
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
    },
    "youtube": {
        "max_duration_seconds": None,  # no hard limit
        "restricted_keywords": [
            "click bait guaranteed", "get rich overnight",
            "miracle diet", "100% profit",
        ],
        "prohibited_categories": ["adult", "hate_speech", "spam"],
        "risk_multipliers": {"adult": 1.5},
    },
    "reels": {
        "max_duration_seconds": 90,
        "restricted_keywords": [
            "guaranteed profit", "miracle cure",
            "adult only", "violence",
        ],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5, "violence": 1.2},
    },
    "instagram": {
        "max_duration_seconds": 60,
        "restricted_keywords": ["adult only", "violence", "hate speech"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5},
    },
    "meta": {
        "max_duration_seconds": None,
        "restricted_keywords": ["hate speech", "violence", "adult content"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {"adult": 1.5, "violence": 1.2},
    },
    "facebook": {
        "max_duration_seconds": None,
        "restricted_keywords": ["hate speech", "violence", "adult only"],
        "prohibited_categories": ["adult", "violence", "hate_speech"],
        "risk_multipliers": {},
    },
}

_DEFAULT_RULES: dict[str, Any] = {
    "max_duration_seconds": None,
    "restricted_keywords": [],
    "prohibited_categories": ["adult", "violence", "hate_speech"],
    "risk_multipliers": {},
}

# Base risk score increments
_RESTRICTED_KEYWORD_INCREMENT = 0.20
_PROHIBITED_CATEGORY_INCREMENT = 0.40
_DURATION_EXCEEDED_INCREMENT = 0.30


@dataclass
class ComplianceResult:
    """Result of a compliance policy evaluation."""

    compliance_status: str  # "passed" | "review" | "failed"
    risk_score: float  # 0.0 – 1.0
    risk_flags: list[str] = field(default_factory=list)
    platform: str = ""
    tier: str = "standard"


class ComplianceRiskPolicy:
    """Evaluate content against platform-specific compliance rules.

    ``evaluate()`` checks keywords, categories, and duration constraints,
    computing a cumulative risk score.  The result is:
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
        )
