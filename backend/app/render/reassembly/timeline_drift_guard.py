from __future__ import annotations


class TimelineDriftGuard:
    """Detects when a scene's duration has shifted enough to misalign the timeline."""

    def detect_drift(
        self,
        old_duration_sec: float,
        new_duration_sec: float,
        tolerance_sec: float = 0.15,
    ) -> dict:
        """Return a drift report comparing old and new durations.

        Args:
            old_duration_sec: Duration before the rerender.
            new_duration_sec: Duration after the rerender.
            tolerance_sec: Changes smaller than this are treated as noise.

        Returns:
            Dict with keys ``has_drift``, ``drift_sec``, ``old_duration_sec``,
            ``new_duration_sec``, and ``tolerance_sec``.
        """
        drift = round(new_duration_sec - old_duration_sec, 3)

        return {
            "has_drift": abs(drift) > tolerance_sec,
            "drift_sec": drift,
            "old_duration_sec": old_duration_sec,
            "new_duration_sec": new_duration_sec,
            "tolerance_sec": tolerance_sec,
        }

    def compare_manifest_duration(self, old_manifest: dict, new_manifest: dict) -> dict:
        """Convenience wrapper that extracts durations from two manifest dicts.

        Args:
            old_manifest: Manifest snapshot before the rerender.
            new_manifest: Manifest snapshot after the rerender.

        Returns:
            The drift report produced by :meth:`detect_drift`.
        """
        return self.detect_drift(
            old_duration_sec=float(old_manifest.get("duration_sec") or 0),
            new_duration_sec=float(new_manifest.get("duration_sec") or 0),
        )
