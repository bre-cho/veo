from __future__ import annotations

from typing import Any, Dict, List

from app.render.assembly.vision.detector_config import DETECTOR_CONFIG


class YOLOObjectDetector:
    """Detects objects in a video frame using a YOLOv8 model.

    Requires the optional ``ultralytics`` package.  Import is deferred to
    ``__init__`` so that the surrounding codebase can still be imported on
    environments where *ultralytics* is not installed.

    Only bounding boxes whose class label appears in
    ``DETECTOR_CONFIG["important_classes"]`` and whose confidence exceeds
    ``DETECTOR_CONFIG["min_confidence"]`` are returned, keeping the output
    focused on objects that are likely to overlap with subtitles.
    """

    def __init__(self) -> None:
        from ultralytics import YOLO  # noqa: PLC0415

        self._model = YOLO(DETECTOR_CONFIG["yolo_model"])
        self._min_confidence: float = DETECTOR_CONFIG["min_confidence"]
        self._important_classes: frozenset = frozenset(
            DETECTOR_CONFIG["important_classes"]
        )

    def detect(self, frame_path: str) -> List[Dict[str, Any]]:
        """Detect objects in *frame_path* and return bounding-box dicts.

        Args:
            frame_path: Absolute path to a JPEG/PNG frame.

        Returns:
            List of bounding-box dicts with integer pixel fields ``x``, ``y``,
            ``w``, ``h``, a ``confidence`` float, and a ``label`` string.
            Only boxes matching ``important_classes`` above ``min_confidence``
            are included.
        """
        results = self._model(frame_path, verbose=False)
        boxes: List[Dict[str, Any]] = []

        for result in results:
            names = result.names
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < self._min_confidence:
                    continue

                cls_id = int(box.cls[0])
                label = names.get(cls_id, str(cls_id))

                if label not in self._important_classes:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                boxes.append(
                    {
                        "x": int(x1),
                        "y": int(y1),
                        "w": int(x2 - x1),
                        "h": int(y2 - y1),
                        "confidence": conf,
                        "label": label,
                    }
                )

        return boxes
