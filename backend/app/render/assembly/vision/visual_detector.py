from __future__ import annotations

from typing import Any, Dict, List


class VisualDetector:
    """Detects faces, persons, and salient objects in a video frame.

    The production implementation should delegate to a real CV pipeline
    (YOLO, MediaPipe, OpenCV DNN, or a cloud vision API).  This stub always
    returns empty detection lists so that the subtitle placement pipeline
    remains functional without a CV dependency installed.

    Replace :meth:`detect` with a concrete implementation to enable
    face/object-aware subtitle placement.
    """

    def detect(self, frame_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Run detection on the given frame and return bounding boxes.

        Args:
            frame_path: Absolute path to a JPEG frame extracted by
                :class:`app.render.assembly.vision.frame_sampler.FrameSampler`.

        Returns:
            A dict with three keys:

            - ``face_bboxes`` — detected human faces
            - ``object_bboxes`` — detected important objects / props
            - ``saliency_bboxes`` — visually salient regions

            Each bounding box is a dict ``{"x": int, "y": int, "w": int, "h": int}``.
        """
        return {
            "face_bboxes": [],
            "object_bboxes": [],
            "saliency_bboxes": [],
        }
