from __future__ import annotations

from typing import Any, Dict, List


class MediaPipeFaceDetector:
    """Detects human faces in a video frame using MediaPipe Face Detection.

    Requires the optional ``mediapipe`` and ``opencv-python`` packages.
    Import is deferred to ``__init__`` so that the surrounding codebase can
    still be imported on environments where these packages are not installed;
    the detector will simply fail to instantiate and the caller falls back to
    no face detection.

    Args:
        min_confidence: Minimum detection confidence in [0, 1].  Boxes with a
            score below this threshold are discarded.
    """

    def __init__(self, min_confidence: float = 0.45) -> None:
        import mediapipe as mp  # noqa: PLC0415

        self.min_confidence = min_confidence
        self._detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # long-range model (>2 m working distance)
            min_detection_confidence=min_confidence,
        )

    def detect(self, frame_path: str) -> List[Dict[str, Any]]:
        """Detect faces in *frame_path* and return bounding-box dicts.

        Args:
            frame_path: Absolute path to a JPEG/PNG frame.

        Returns:
            List of bounding-box dicts, each with integer pixel fields
            ``x``, ``y``, ``w``, ``h``, a ``confidence`` float, and
            ``label: "face"``.  Returns an empty list if the image cannot be
            read or no faces are found.
        """
        import cv2  # noqa: PLC0415

        image = cv2.imread(frame_path)
        if image is None:
            return []

        h, w = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self._detector.process(rgb)

        if not result.detections:
            return []

        boxes: List[Dict[str, Any]] = []
        for detection in result.detections:
            rel = detection.location_data.relative_bounding_box
            boxes.append(
                {
                    "x": int(rel.xmin * w),
                    "y": int(rel.ymin * h),
                    "w": int(rel.width * w),
                    "h": int(rel.height * h),
                    "confidence": float(detection.score[0]),
                    "label": "face",
                }
            )

        return boxes
