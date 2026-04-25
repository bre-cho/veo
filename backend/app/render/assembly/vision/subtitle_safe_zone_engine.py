from __future__ import annotations

from typing import Any, Dict, List


class SubtitleSafeZoneEngine:
    """Chooses the best subtitle placement position to avoid detected content.

    The engine tests three placement zones (bottom → top → middle-low) in
    order of preference and returns the first zone that is not blocked by
    any detected face, object, or salient region.

    Placement map
    -------------
    - ``bottom`` — ASS alignment 2, margin_v 70  (default, preferred)
    - ``top``    — ASS alignment 8, margin_v 70  (fallback when bottom is blocked)
    - ``middle_low`` — ASS alignment 2, margin_v 180 (last resort)
    """

    # Fraction of video height used to define the "danger zone" boundary
    BOTTOM_DANGER_THRESHOLD = 0.70
    TOP_DANGER_THRESHOLD = 0.25

    _ZONES: Dict[str, Dict[str, Any]] = {
        "bottom": {"alignment": 2, "margin_v": 70},
        "top": {"alignment": 8, "margin_v": 70},
        "middle_low": {"alignment": 2, "margin_v": 180},
    }

    def choose_position(
        self,
        detection: Dict[str, Any],
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> Dict[str, Any]:
        """Return the safest subtitle placement for the given detection result.

        Args:
            detection: Output of
                :meth:`app.render.assembly.vision.visual_detector.VisualDetector.detect`.
            video_width: Frame width (reserved for future horizontal checks).
            video_height: Frame height used for threshold calculations.

        Returns:
            A dict with ``placement`` (str name), ``alignment`` (int), and
            ``margin_v`` (int).
        """
        blocked_bottom = self._is_bottom_blocked(detection, video_height)
        blocked_top = self._is_top_blocked(detection, video_height)

        if not blocked_bottom:
            placement = "bottom"
        elif not blocked_top:
            placement = "top"
        else:
            placement = "middle_low"

        return {"placement": placement, **self._ZONES[placement]}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_bottom_blocked(self, detection: Dict[str, Any], video_height: int) -> bool:
        danger_zone_y = int(video_height * self.BOTTOM_DANGER_THRESHOLD)
        for box in self._all_boxes(detection):
            if box.get("y", 0) + box.get("h", 0) >= danger_zone_y:
                return True
        return False

    def _is_top_blocked(self, detection: Dict[str, Any], video_height: int) -> bool:
        danger_zone_y = int(video_height * self.TOP_DANGER_THRESHOLD)
        for box in self._all_boxes(detection):
            if box.get("y", 0) <= danger_zone_y:
                return True
        return False

    def _all_boxes(self, detection: Dict[str, Any]) -> List[Dict[str, Any]]:
        return (
            detection.get("face_bboxes", [])
            + detection.get("object_bboxes", [])
            + detection.get("saliency_bboxes", [])
        )
