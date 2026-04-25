"""Subtitle burn-in mode configuration.

Change ``SUBTITLE_BURN_IN_MODE`` to switch between:

* ``"global_burn_in"``  — one ``.ass`` file covers the whole episode;
  timeline drift requires rebuilding all chunks from the changed scene onward.
* ``"per_scene_burn_in"`` — each scene has its own ``.ass`` file;
  timeline drift only requires rebuilding the changed scene's chunk.
"""

SUBTITLE_BURN_IN_MODE: str = "per_scene_burn_in"
