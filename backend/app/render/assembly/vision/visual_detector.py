from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.render.assembly.vision.detector_config import DETECTOR_CONFIG

_logger = logging.getLogger(__name__)


class VisualDetector:
    """Detects faces, persons, and salient objects in a video frame.

    Attempts to load :class:`MediaPipeFaceDetector` and
    :class:`YOLOObjectDetector` at construction time.  Either detector
    gracefully falls back to *disabled* if its optional dependency package
    (``mediapipe`` / ``ultralytics``) is not installed, so the subtitle
    pipeline continues to function without CV packages.

    Bounding box coordinate system
    --------------------------------
    All bounding boxes use pixel coordinates measured from the **top-left
    corner** of the frame:

    - ``x`` — horizontal offset in pixels from the left edge
    - ``y`` — vertical offset in pixels from the top edge
    - ``w`` — box width in pixels
    - ``h`` — box height in pixels

    So the bottom of a box is at ``y + h``.
    """

    def __init__(self) -> None:
        self.face_detector = None
        self.object_detector = None

        if DETECTOR_CONFIG.get("enable_face_detection", True):
            try:
                from app.render.assembly.vision.mediapipe_face_detector import (  # noqa: PLC0415
                    MediaPipeFaceDetector,
                )

                self.face_detector = MediaPipeFaceDetector(
                    min_confidence=DETECTOR_CONFIG["min_confidence"]
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "MediaPipe face detector unavailable (%s: %s); "
                    "face detection disabled.",
                    type(exc).__name__,
                    exc,
                )

        if DETECTOR_CONFIG.get("enable_object_detection", True):
            try:
                from app.render.assembly.vision.yolo_object_detector import (  # noqa: PLC0415
                    YOLOObjectDetector,
                )

                self.object_detector = YOLOObjectDetector()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "YOLO object detector unavailable (%s: %s); "
                    "object detection disabled.",
                    type(exc).__name__,
                    exc,
                )

    def detect(self, frame_path: str) -> Dict[str, Any]:
        """Run available detectors on *frame_path* and merge results.

        Args:
            frame_path: Absolute path to a JPEG frame extracted by
                :class:`app.render.assembly.vision.frame_sampler.FrameSampler`.

        Returns:
            A dict with keys:

            - ``face_bboxes`` — detected human faces (from MediaPipe)
            - ``object_bboxes`` — all important object boxes (from YOLO)
            - ``saliency_bboxes`` — subset of object boxes labelled ``"person"``
            - ``detector_status`` — dict of ``face_detector`` / ``object_detector``
              booleans indicating which detectors were active
        """
        face_bboxes: List[Dict[str, Any]] = []
        object_bboxes: List[Dict[str, Any]] = []

        if self.face_detector:
            face_bboxes = self.face_detector.detect(frame_path)

        if self.object_detector:
            object_bboxes = self.object_detector.detect(frame_path)

        saliency_bboxes = [
            box for box in object_bboxes if box.get("label") == "person"
        ]

        return {
            "face_bboxes": face_bboxes,
            "object_bboxes": object_bboxes,
            "saliency_bboxes": saliency_bboxes,
            "detector_status": {
                "face_detector": self.face_detector is not None,
                "object_detector": self.object_detector is not None,
            },
        }

