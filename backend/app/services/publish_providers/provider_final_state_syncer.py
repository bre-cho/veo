"""ProviderFinalStateSyncer — per-platform final state fetching."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ProviderFinalStateSyncer:
    """Fetch the terminal publish status from a platform API.

    Returns a dict with at minimum:
    - ``terminal_status``: one of "published", "failed", "pending", "unknown"
    - ``metrics``: dict with views_initial, likes_initial, etc.

    Falls back gracefully when the platform API is not configured.
    """

    def fetch_final_state(self, job_id: str, platform: str) -> dict[str, Any]:
        """Dispatch to the platform-specific syncer."""
        platform_lower = platform.lower()
        if platform_lower in ("youtube", "shorts"):
            return YouTubeFinalStateSyncer().fetch_final_state(job_id)
        if platform_lower == "tiktok":
            return TikTokFinalStateSyncer().fetch_final_state(job_id)
        if platform_lower in ("meta", "reels", "instagram", "facebook"):
            return MetaFinalStateSyncer().fetch_final_state(job_id)
        return {"terminal_status": "unknown", "metrics": {}, "platform": platform}


class YouTubeFinalStateSyncer:
    """Fetch final state from YouTube API."""

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
            f"?part=status,statistics&id={job_id}&key={self._API_KEY}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
        items = data.get("items", [])
        if not items:
            return {"terminal_status": "failed", "metrics": {}, "platform": "youtube"}
        item = items[0]
        status = item.get("status", {}).get("uploadStatus", "unknown")
        stats = item.get("statistics", {})
        terminal = "published" if status == "processed" else ("failed" if status in ("failed", "rejected") else "pending")
        return {
            "terminal_status": terminal,
            "platform": "youtube",
            "metrics": {
                "views_initial": int(stats.get("viewCount", 0)),
                "likes_initial": int(stats.get("likeCount", 0)),
            },
        }


class TikTokFinalStateSyncer:
    """Fetch final state from TikTok API."""

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
        return {
            "terminal_status": terminal,
            "platform": "tiktok",
            "metrics": {
                "views_initial": v.get("view_count", 0),
                "likes_initial": v.get("like_count", 0),
            },
        }


class MetaFinalStateSyncer:
    """Fetch final state from Meta Graph API."""

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
            f"?fields=status,video_insights&access_token={self._ACCESS_TOKEN}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
        status = data.get("status", {}).get("video_status", "unknown")
        terminal = "published" if status in ("ready", "complete") else ("failed" if status == "error" else "pending")
        return {
            "terminal_status": terminal,
            "platform": "meta",
            "metrics": {
                "views_initial": 0,
                "likes_initial": 0,
            },
        }
