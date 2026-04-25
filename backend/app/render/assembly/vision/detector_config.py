from __future__ import annotations

"""Configuration constants for the visual detection pipeline.

Adjust these values to trade off accuracy vs. speed.  The YOLO model weight
file is downloaded automatically by *ultralytics* on first use.

Tips
----
- CPU-only servers: ``yolov8n.pt`` (nano) is the fastest model.
- If object detection is too slow, set ``enable_object_detection: False``
  to run only the lightweight MediaPipe face detector.
- Increase ``min_confidence`` to reduce false positives in cluttered scenes.
"""

DETECTOR_CONFIG: dict = {
    # Feature flags
    "enable_face_detection": True,
    "enable_object_detection": True,

    # YOLO model weights file (auto-downloaded by ultralytics on first run)
    "yolo_model": "yolov8n.pt",

    # Minimum confidence threshold shared by both detectors
    "min_confidence": 0.45,

    # Only boxes whose label appears in this list influence subtitle placement.
    # "person" and "face" are the highest-priority classes; add domain-specific
    # objects as needed.
    "important_classes": ["person", "face", "car", "phone", "laptop"],
}
