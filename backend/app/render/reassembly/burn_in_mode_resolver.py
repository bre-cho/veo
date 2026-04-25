from __future__ import annotations

from app.render.assembly.subtitles.subtitle_mode import SUBTITLE_BURN_IN_MODE


class BurnInModeResolver:
    """Interprets the configured subtitle burn-in mode.

    The mode controls two aspects of smart reassembly:

    * Which subtitle service to call when drift is detected.
    * Whether to rebuild only the changed scene's chunk or the changed scene
      *and* every scene that follows it.
    """

    def mode(self) -> str:
        """Return the active burn-in mode string."""
        return SUBTITLE_BURN_IN_MODE

    def requires_affected_range_rebuild(self, has_timeline_drift: bool) -> bool:
        """Return ``True`` when all scenes from the changed scene onward need rebuilding.

        This is only necessary when the episode uses a **single shared** subtitle
        file (``global_burn_in``) *and* the timeline has drifted, because every
        downstream scene's chunk would contain stale subtitle timestamps.

        Args:
            has_timeline_drift: Whether a significant duration change was detected.
        """
        if not has_timeline_drift:
            return False
        return self.mode() == "global_burn_in"

    def requires_only_changed_scene(self, has_timeline_drift: bool) -> bool:
        """Return ``True`` when only the changed scene's chunk needs rebuilding.

        In ``per_scene_burn_in`` mode each scene carries its own subtitle file
        with scene-local timestamps, so downstream scenes are unaffected even
        when duration drifts.

        Args:
            has_timeline_drift: Whether a significant duration change was detected.
        """
        if not has_timeline_drift:
            return True
        return self.mode() == "per_scene_burn_in"
