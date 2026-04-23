"""post_render_seo_orchestrator — generate the SEO package after a render completes.

Produces the full content package needed to maximise discoverability when the
final video is published:

- ``title``        : SEO + curiosity + series-continuity title
- ``description``  : hook → promise → open-loop → series next-step CTA
- ``pin_comment``  : first-comment text to pin for extra engagement
- ``hashtags_video``: per-video hashtag list
- ``hashtags_channel``: channel-level evergreen hashtags
- ``thumbnail_brief``: text overlay brief + A/B variant hints
- ``end_screen``   : playlist linking metadata

All fields are generated deterministically from the project/job metadata
(no LLM call required at this stage). When a winner-pattern context is
present, the outputs are shaped by that DNA.

Usage::

    orchestrator = PostRenderSEOOrchestrator()
    package = orchestrator.generate_seo_package(job, project=None)
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / templates
# ---------------------------------------------------------------------------
_TITLE_MAX_CHARS = 100
_DESCRIPTION_MAX_CHARS = 5000
_HASHTAG_VIDEO_COUNT = 8
_HASHTAG_CHANNEL_COUNT = 5

_DEFAULT_CHANNEL_HASHTAGS = [
    "#ai",
    "#shorts",
    "#viral",
    "#trending",
    "#contentcreator",
]

_CURIOSITY_SUFFIXES = [
    "You Won't Believe This",
    "Here's What Happened",
    "This Changes Everything",
    "Watch Until the End",
    "Most People Don't Know This",
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class PostRenderSEOOrchestrator:
    """Generate a complete SEO content package for a completed render job."""

    def generate_seo_package(
        self,
        job: Any,
        project: dict | None = None,
    ) -> dict[str, Any]:
        """Build the full SEO package from available job / project metadata.

        Parameters
        ----------
        job:
            A ``RenderJob`` ORM instance (or any object with the relevant
            attributes: ``id``, ``project_id``, ``final_video_url``, etc.).
        project:
            Optional project dict loaded from ``project_workspace_service``.
            When ``None`` the orchestrator tries to load it from disk.

        Returns
        -------
        dict
            Keys: ``title``, ``description``, ``pin_comment``,
            ``hashtags_video``, ``hashtags_channel``, ``thumbnail_brief``,
            ``end_screen``, ``source_job_id``.
        """
        if project is None:
            project = self._load_project(getattr(job, "project_id", None))

        ctx = self._build_context(job, project)
        package: dict[str, Any] = {
            "source_job_id": getattr(job, "id", None),
            "title": self._generate_title(ctx),
            "description": self._generate_description(ctx),
            "pin_comment": self._generate_pin_comment(ctx),
            "hashtags_video": self._generate_video_hashtags(ctx),
            "hashtags_channel": self._generate_channel_hashtags(ctx),
            "thumbnail_brief": self._generate_thumbnail_brief(ctx),
            "end_screen": self._generate_end_screen_metadata(ctx),
        }

        logger.debug(
            "PostRenderSEOOrchestrator: package generated for job=%s title=%r",
            package["source_job_id"],
            package["title"],
        )
        return package

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def _build_context(self, job: Any, project: dict | None) -> dict[str, Any]:
        p = project or {}
        scenes = p.get("scenes") or []
        first_scene_title = scenes[0].get("title", "") if scenes else ""
        content_goal = p.get("content_goal") or "engagement"
        market_code = p.get("market_code") or "US"
        avatar_id = p.get("avatar_id") or ""
        series_id = p.get("series_id") or ""
        episode_index = int(p.get("episode_index") or 0)
        hook_text = (p.get("hook") or first_scene_title or p.get("title") or "").strip()
        winner_dna = (p.get("winner_dna_summary") or {})
        channel_niche = p.get("niche") or p.get("category") or "general"
        return {
            "job_id": getattr(job, "id", ""),
            "project_id": getattr(job, "project_id", p.get("id", "")),
            "final_video_url": getattr(job, "final_video_url", None) or p.get("final_video_url"),
            "content_goal": content_goal,
            "market_code": market_code,
            "avatar_id": avatar_id,
            "series_id": series_id,
            "episode_index": episode_index,
            "hook_text": hook_text,
            "winner_dna": winner_dna,
            "channel_niche": channel_niche,
            "scene_count": len(scenes),
            "all_scene_titles": [s.get("title", "") for s in scenes],
        }

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------

    def _generate_title(self, ctx: dict) -> str:
        base = ctx["hook_text"] or ctx["content_goal"].replace("_", " ").title()
        winner = ctx["winner_dna"]
        title_pattern = winner.get("title_pattern") or ""

        if title_pattern:
            title = title_pattern.replace("{hook}", base)
        else:
            # Build curiosity title using simple template
            suffix = _CURIOSITY_SUFFIXES[ctx["episode_index"] % len(_CURIOSITY_SUFFIXES)]
            title = f"{base} — {suffix}" if base else suffix

        if ctx["series_id"] and ctx["episode_index"] > 0:
            title = f"Ep {ctx['episode_index'] + 1}: {title}"

        return title[:_TITLE_MAX_CHARS]

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    def _generate_description(self, ctx: dict) -> str:
        hook = ctx["hook_text"] or "Watch this"
        goal = ctx["content_goal"]
        niche = ctx["channel_niche"]
        episode_index = ctx["episode_index"]
        series_id = ctx["series_id"]

        hook_line = f"🔥 {hook}"
        promise_line = f"\nIn this video you'll discover powerful insights about {niche} that most people overlook."
        body_line = "\nWe break it down step by step so you can take action immediately."

        if series_id:
            open_loop = (
                f"\n\n📌 This is part of the '{series_id}' series. "
                "Stay tuned — the next episode drops soon and it gets even better."
            )
        else:
            open_loop = "\n\nStay tuned for the next upload — you won't want to miss it."

        cta_line = "\n\n👉 Like & Subscribe to never miss an update."
        if goal == "conversion":
            cta_line = "\n\n👉 Ready to take the next step? Check the link in bio."

        description = hook_line + promise_line + body_line + open_loop + cta_line
        return description[:_DESCRIPTION_MAX_CHARS]

    # ------------------------------------------------------------------
    # Pin comment
    # ------------------------------------------------------------------

    def _generate_pin_comment(self, ctx: dict) -> str:
        niche = ctx["channel_niche"]
        return (
            f"💬 What's your biggest challenge with {niche}? "
            "Drop it in the comments — I read every single one! 👇"
        )

    # ------------------------------------------------------------------
    # Hashtags
    # ------------------------------------------------------------------

    def _generate_video_hashtags(self, ctx: dict) -> list[str]:
        niche_slug = re.sub(r"[^a-z0-9]", "", ctx["channel_niche"].lower())
        goal_slug = re.sub(r"[^a-z0-9]", "", ctx["content_goal"].lower())
        base = [
            f"#{niche_slug}",
            f"#{goal_slug}",
            "#shorts",
            "#viral",
            "#ai",
            "#contentcreator",
            "#trending",
            "#fyp",
        ]
        return list(dict.fromkeys(base))[:_HASHTAG_VIDEO_COUNT]

    def _generate_channel_hashtags(self, ctx: dict) -> list[str]:
        niche_slug = re.sub(r"[^a-z0-9]", "", ctx["channel_niche"].lower())
        channel_tags = list(_DEFAULT_CHANNEL_HASHTAGS) + [f"#{niche_slug}channel"]
        return list(dict.fromkeys(channel_tags))[:_HASHTAG_CHANNEL_COUNT]

    # ------------------------------------------------------------------
    # Thumbnail brief
    # ------------------------------------------------------------------

    def _generate_thumbnail_brief(self, ctx: dict) -> dict[str, Any]:
        winner = ctx["winner_dna"]
        thumbnail_logic = winner.get("thumbnail_logic") or "face + emotion + bold text"
        return {
            "hero_frame": "first_scene_peak_frame",
            "avatar_safe_frame": "avatar_canonical_face_visible",
            "text_overlay": ctx["hook_text"] or ctx["content_goal"],
            "thumbnail_logic": thumbnail_logic,
            "ab_variants": [
                {"variant": "A", "style": "face_close_up", "text": ctx["hook_text"]},
                {"variant": "B", "style": "scene_reveal", "text": "Watch This →"},
            ],
        }

    # ------------------------------------------------------------------
    # End-screen metadata
    # ------------------------------------------------------------------

    def _generate_end_screen_metadata(self, ctx: dict) -> dict[str, Any]:
        return {
            "subscribe_card": True,
            "next_video_card": True,
            "playlist_link": ctx["series_id"] or None,
            "series_id": ctx["series_id"] or None,
            "episode_next": ctx["episode_index"] + 1 if ctx["series_id"] else None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_project(project_id: str | None) -> dict | None:
        if not project_id:
            return None
        try:
            from app.services.project_workspace_service import load_project
            return load_project(project_id)
        except Exception:
            return None
