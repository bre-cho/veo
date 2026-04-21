"""ProviderFinalStateSyncer — per-platform final state fetching.

Phase 3.1: richer per-platform metadata fields.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Poll interval (seconds) when terminal_status = "pending" and retry_on_pending=True
FINAL_STATE_POLL_INTERVAL_SEC = int(os.environ.get("FINAL_STATE_POLL_INTERVAL_SEC", "300"))


class ProviderFinalStateSyncer:
    """Fetch the terminal publish status from a platform API.

    Returns a dict with at minimum:
    - ``terminal_status``: one of "published", "failed", "pending", "unknown"
    - ``metrics``: dict with views_initial, likes_initial, etc.
    - Platform-specific fields (Phase 3.1)

    Falls back gracefully when the platform API is not configured.
    """

    def fetch_final_state(
        self,
        job_id: str,
        platform: str,
        retry_on_pending: bool = True,
    ) -> dict[str, Any]:
        """Dispatch to the platform-specific syncer."""
        platform_lower = platform.lower()
        if platform_lower in ("youtube", "shorts"):
            result = YouTubeFinalStateSyncer().fetch_final_state(job_id)
        elif platform_lower == "tiktok":
            result = TikTokFinalStateSyncer().fetch_final_state(job_id)
        elif platform_lower in ("meta", "reels", "instagram", "facebook"):
            result = MetaFinalStateSyncer().fetch_final_state(job_id)
        else:
            result = {"terminal_status": "unknown", "metrics": {}, "platform": platform}

        # Phase 3.1: attach poll_interval hint when pending and retry requested
        if retry_on_pending and result.get("terminal_status") == "pending":
            result["retry_after_sec"] = FINAL_STATE_POLL_INTERVAL_SEC

        return result


class YouTubeFinalStateSyncer:
    """Fetch final state from YouTube API.

    Phase 3.1 additions: monetization_status, age_restriction, copyright_claim.
    """

    _API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

    def fetch_final_state(self, job_id: str) -> dict[str, Any]:
        if not self._API_KEY:
            logger.debug("YouTubeFinalStateSyncer: API key not configured")
            return {"terminal_status": "unknown", "metrics": {}, "platform": "youtube"}
        try:
            return self._call_api(job_id)
        except Exception as exc:
            logger.warning("YouTubeFinalStateSyncer error job_id=%s: %s", job_id, exc)
            return {"terminal_status": "unknown", "metrics": {}, "platform": "youtube"}

    def _call_api(self, job_id: str) -> dict[str, Any]:
        import json
        import urllib.request

        url = (
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?part=status,statistics,contentDetails&id={job_id}&key={self._API_KEY}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
        items = data.get("items", [])
        if not items:
            return {"terminal_status": "failed", "metrics": {}, "platform": "youtube"}
        item = items[0]
        status = item.get("status", {})
        upload_status = status.get("uploadStatus", "unknown")
        stats = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        terminal = "published" if upload_status == "processed" else (
            "failed" if upload_status in ("failed", "rejected") else "pending"
        )
        return {
            "terminal_status": terminal,
            "platform": "youtube",
            "metrics": {
                "views_initial": int(stats.get("viewCount", 0)),
                "likes_initial": int(stats.get("likeCount", 0)),
            },
            # Phase 3.1: richer YouTube fields
            "monetization_status": status.get("monetizationStatus", "unknown"),
            "age_restriction": content_details.get("contentRating", {}).get("ytRating"),
            "copyright_claim": status.get("hasCopyrightClaim", False),
        }


class TikTokFinalStateSyncer:
    """Fetch final state from TikTok API.

    Phase 3.1 additions: review_status, rejection_reason, appeal_eligible.
    """

    _ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")

    def fetch_final_state(self, job_id: str) -> dict[str, Any]:
        if not self._ACCESS_TOKEN:
            logger.debug("TikTokFinalStateSyncer: access token not configured")
            return {"terminal_status": "unknown", "metrics": {}, "platform": "tiktok"}
        try:
            return self._call_api(job_id)
        except Exception as exc:
            logger.warning("TikTokFinalStateSyncer error job_id=%s: %s", job_id, exc)
            return {"terminal_status": "unknown", "metrics": {}, "platform": "tiktok"}

    def _call_api(self, job_id: str) -> dict[str, Any]:
        import json
        import urllib.request

        url = "https://open.tiktokapis.com/v2/video/query/"
        payload = json.dumps({"filters": {"video_ids": [job_id]}}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
        videos = data.get("data", {}).get("videos", [])
        if not videos:
            return {"terminal_status": "unknown", "metrics": {}, "platform": "tiktok"}
        v = videos[0]
        status_map = {"published": "published", "failed": "failed"}
        terminal = status_map.get(v.get("status", ""), "pending")
        rejection_reason = v.get("rejection_reason") or v.get("fail_reason")
        return {
            "terminal_status": terminal,
            "platform": "tiktok",
            "metrics": {
                "views_initial": v.get("view_count", 0),
                "likes_initial": v.get("like_count", 0),
            },
            # Phase 3.1: richer TikTok fields
            "review_status": v.get("status", "unknown"),
            "rejection_reason": rejection_reason,
            "appeal_eligible": terminal == "failed" and rejection_reason is not None,
        }


class MetaFinalStateSyncer:
    """Fetch final state from Meta Graph API.

    Phase 3.1 additions: review_status, policy_violation_codes, boost_eligible.
    """

    _ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")

    def fetch_final_state(self, job_id: str) -> dict[str, Any]:
        if not self._ACCESS_TOKEN:
            logger.debug("MetaFinalStateSyncer: access token not configured")
            return {"terminal_status": "unknown", "metrics": {}, "platform": "meta"}
        try:
            return self._call_api(job_id)
        except Exception as exc:
            logger.warning("MetaFinalStateSyncer error job_id=%s: %s", job_id, exc)
            return {"terminal_status": "unknown", "metrics": {}, "platform": "meta"}

    def _call_api(self, job_id: str) -> dict[str, Any]:
        import json
        import urllib.request

        url = (
            f"https://graph.facebook.com/v18.0/{job_id}"
            f"?fields=status,video_insights,content_category,error"
            f"&access_token={self._ACCESS_TOKEN}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
        status = data.get("status", {}).get("video_status", "unknown")
        error = data.get("error", {})
        policy_codes = [error.get("code")] if error.get("code") else []
        terminal = "published" if status in ("ready", "complete") else (
            "failed" if status == "error" else "pending"
        )
        return {
            "terminal_status": terminal,
            "platform": "meta",
            "metrics": {
                "views_initial": 0,
                "likes_initial": 0,
            },
            # Phase 3.1: richer Meta fields
            "review_status": status,
            "policy_violation_codes": policy_codes,
            "boost_eligible": terminal == "published" and not policy_codes,
        }


# ---------------------------------------------------------------------------
# Phase 3.5 (v16): ProviderStatePollOrchestrator — multi-round confirmation
# ---------------------------------------------------------------------------


class ProviderStatePollOrchestrator:
    """Poll provider final state with multi-round confirmation and timeout.

    For platforms where terminal status is eventually consistent (e.g. YouTube
    processing lag), a single fetch may return ``"pending"`` even when the
    video has finished processing.  This orchestrator retries up to
    ``max_rounds`` times with exponential back-off, confirming a
    stable terminal status before returning.

    Confirms ``"published"`` only when the status is stable across
    ``required_stable_rounds`` consecutive polls.

    Usage::

        poller = ProviderStatePollOrchestrator(max_rounds=3, poll_interval_sec=5)
        result = poller.poll_until_stable(job_id="video-abc", platform="youtube")
        # result["confirmed_status"]  → "published" | "failed" | "pending" | "timeout"
        # result["rounds_polled"]     → int
    """

    # Statuses considered terminal (no further polling needed)
    _TERMINAL_STATUSES = frozenset({"published", "failed"})

    def __init__(
        self,
        max_rounds: int = 3,
        poll_interval_sec: float = 2.0,
        required_stable_rounds: int = 2,
        _syncer: ProviderFinalStateSyncer | None = None,
    ) -> None:
        """
        Parameters
        ----------
        max_rounds:
            Maximum number of polling rounds before giving up.
        poll_interval_sec:
            Base sleep interval between rounds (seconds).  In production this
            is an actual sleep; in tests the ``_syncer`` can be mocked so
            no actual sleep occurs.
        required_stable_rounds:
            Number of consecutive rounds with the same terminal status
            required before the status is confirmed.
        """
        self._max_rounds = max(1, max_rounds)
        self._poll_interval_sec = max(0.0, poll_interval_sec)
        self._required_stable = max(1, required_stable_rounds)
        self._syncer = _syncer or ProviderFinalStateSyncer()

    def poll_until_stable(
        self,
        job_id: str,
        platform: str,
        _sleep: bool = False,  # set True only in production; off in tests
    ) -> dict[str, Any]:
        """Poll provider until a stable terminal status is confirmed.

        Args:
            job_id: Platform-side video/post identifier.
            platform: Target platform.
            _sleep: When True, sleep between rounds (use only in async workers).

        Returns:
            Dict with:
            - ``job_id``, ``platform``
            - ``confirmed_status``: "published" | "failed" | "pending" | "timeout"
            - ``rounds_polled``: int
            - ``stable_rounds``: int — consecutive rounds with the same status
            - ``last_result``: last raw syncer result
            - ``confirmed``: bool — True when stable terminal status reached
        """
        import time as _time

        stable_count = 0
        last_status: str | None = None
        last_result: dict[str, Any] = {}

        for round_idx in range(1, self._max_rounds + 1):
            if _sleep and round_idx > 1:
                _time.sleep(self._poll_interval_sec * (2 ** (round_idx - 2)))

            try:
                result = self._syncer.fetch_final_state(
                    job_id=job_id,
                    platform=platform,
                    retry_on_pending=False,
                )
            except Exception as exc:
                logger.warning(
                    "ProviderStatePollOrchestrator: fetch error round=%d job=%s: %s",
                    round_idx, job_id, exc,
                )
                result = {"terminal_status": "unknown", "metrics": {}, "platform": platform}

            current_status = result.get("terminal_status", "unknown")
            last_result = result

            if current_status == last_status and current_status in self._TERMINAL_STATUSES:
                stable_count += 1
            else:
                stable_count = 1 if current_status in self._TERMINAL_STATUSES else 0

            last_status = current_status

            if stable_count >= self._required_stable:
                logger.info(
                    "ProviderStatePollOrchestrator: confirmed status=%s job=%s rounds=%d",
                    current_status, job_id, round_idx,
                )
                return {
                    "job_id": job_id,
                    "platform": platform,
                    "confirmed_status": current_status,
                    "rounds_polled": round_idx,
                    "stable_rounds": stable_count,
                    "last_result": last_result,
                    "confirmed": True,
                }

            if current_status == "pending" and round_idx < self._max_rounds:
                continue

        # Exhausted rounds without stable confirmation
        return {
            "job_id": job_id,
            "platform": platform,
            "confirmed_status": last_status or "timeout",
            "rounds_polled": self._max_rounds,
            "stable_rounds": stable_count,
            "last_result": last_result,
            "confirmed": False,
        }
