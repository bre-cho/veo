"""Publish preflight validator.

Checks platform-specific content rules before a publish job is sent to the
provider.  Each platform has its own ruleset (title length, hashtag count,
description length, etc.).  ``validate()`` returns a list of violation strings;
an empty list means the job passed all checks.
"""
from __future__ import annotations

from typing import Any

from app.models.publish_job import PublishJob

# ---------------------------------------------------------------------------
# Platform rulesets
# ---------------------------------------------------------------------------

_PLATFORM_RULES: dict[str, dict[str, Any]] = {
    "youtube": {
        "max_title_len": 100,
        "max_description_len": 5000,
        "max_tags": 500,          # total chars
        "max_hashtags": 15,
    },
    "shorts": {
        "max_title_len": 100,
        "max_description_len": 5000,
        "max_tags": 500,
        "max_hashtags": 15,
    },
    "tiktok": {
        "max_title_len": 150,
        "max_description_len": 2200,
        "max_hashtags": 30,
    },
    "reels": {
        "max_title_len": 2200,
        "max_description_len": 2200,
        "max_hashtags": 30,
    },
    "instagram": {
        "max_title_len": 2200,
        "max_description_len": 2200,
        "max_hashtags": 30,
    },
    "meta": {
        "max_title_len": 2200,
        "max_description_len": 2200,
        "max_hashtags": 30,
    },
    "facebook": {
        "max_title_len": 2200,
        "max_description_len": 63206,
        "max_hashtags": 30,
    },
}

_DEFAULT_RULES: dict[str, Any] = {
    "max_title_len": 500,
    "max_description_len": 10000,
    "max_hashtags": 50,
}


def _count_hashtags(text: str) -> int:
    return sum(1 for word in text.split() if word.startswith("#"))


class PublishPreflightValidator:
    """Validates a ``PublishJob`` against its platform's content rules.

    Usage::

        validator = PublishPreflightValidator()
        errors = validator.validate(job)
        if errors:
            # fail fast
    """

    def validate(self, job: PublishJob) -> list[str]:
        """Return a list of human-readable violation strings (empty = OK)."""
        platform = (job.platform or "").lower()
        rules = _PLATFORM_RULES.get(platform, _DEFAULT_RULES)
        payload: dict[str, Any] = job.payload or {}
        metadata: dict[str, Any] = payload.get("metadata") or {}

        errors: list[str] = []

        # --- Title length ---
        title = str(payload.get("title_angle") or metadata.get("channel_name") or "")
        max_title = int(rules.get("max_title_len", 500))
        if len(title) > max_title:
            errors.append(
                f"title too long: {len(title)} chars (platform '{platform}' max {max_title})"
            )

        # --- Description / caption length ---
        description = str(payload.get("content_goal") or metadata.get("description") or "")
        max_desc = int(rules.get("max_description_len", 10000))
        if len(description) > max_desc:
            errors.append(
                f"description too long: {len(description)} chars (platform '{platform}' max {max_desc})"
            )

        # --- Hashtag count ---
        all_text = f"{title} {description}"
        hashtag_count = _count_hashtags(all_text)
        max_hashtags = int(rules.get("max_hashtags", 50))
        if hashtag_count > max_hashtags:
            errors.append(
                f"too many hashtags: {hashtag_count} (platform '{platform}' max {max_hashtags})"
            )

        # --- Adult-content flag ---
        if bool(metadata.get("adult_content", False)):
            errors.append("adult_content flag is set; manual review required before publishing")

        # --- Video URL present for platforms that require it ---
        # Only enforce in REAL publish mode (skip for SIMULATED / test runs)
        publish_mode = str(getattr(job, "publish_mode", "") or "").upper()
        if publish_mode != "SIMULATED" and platform in ("tiktok", "reels", "instagram", "meta", "facebook"):
            video_url = str(metadata.get("video_url") or "").strip()
            if not video_url:
                errors.append(
                    f"platform '{platform}' requires metadata.video_url to be set before publishing"
                )

        return errors
