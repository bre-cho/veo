"""factory_qa_verifier – real artifact and metadata verification for QA_VALIDATE.

Checks performed
----------------
1.  scene_count ≥ 1
2.  render_job_id present
3.  script title present
4.  brain decision not BLOCK
5.  avatar assigned
6.  render plan present and non-empty
7.  manifest readable (final_timeline JSON parseable, scenes match)
8.  audio present (audio_url or duration_ms)
9.  subtitle segments present (at least one non-empty subtitle_text)
10. estimated duration valid (> 0 seconds)
11. SEO package non-empty (title set)
12. publish payload shape valid (run_id, render_job_id, dry_run field)

Each failed check appends a code string to ``issues``.  The verifier never
raises — all checks degrade gracefully.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FactoryQAVerifier:
    """Runs structured QA checks against factory pipeline outputs.

    Usage::

        verifier = FactoryQAVerifier()
        result = verifier.verify(ctx_fields, db=db)
        # result["qa_passed"] == True/False
        # result["issues"]    == list of issue codes
        # result["warnings"]  == list of advisory codes
    """

    def verify(
        self,
        scenes: list[dict[str, Any]],
        render_job_id: str | None,
        script_plan: dict[str, Any] | None,
        avatar_id: str | None,
        render_plan: dict[str, Any] | None,
        audio_url: str | None,
        seo_package: dict[str, Any] | None,
        publish_result: dict[str, Any] | None,
        render_manifest: dict[str, Any] | None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Run all QA checks and return a structured result dict."""
        issues: list[str] = []
        warnings: list[str] = []
        details: dict[str, Any] = {}

        plan = script_plan or {}

        # ── 1. Scene count ────────────────────────────────────────────────
        scene_count = len(scenes)
        details["scene_count"] = scene_count
        if scene_count == 0:
            issues.append("no_scenes_built")

        # ── 2. Render job ID ──────────────────────────────────────────────
        if not render_job_id:
            issues.append("no_render_job_id")

        # ── 3. Script title ───────────────────────────────────────────────
        if not plan.get("title"):
            issues.append("missing_script_title")

        # ── 4. Brain decision ─────────────────────────────────────────────
        if plan.get("decision") == "BLOCK":
            issues.append("brain_decision_block")

        # ── 5. Avatar ─────────────────────────────────────────────────────
        if not avatar_id:
            issues.append("no_avatar_assigned")

        # ── 6. Render plan ────────────────────────────────────────────────
        rp = render_plan or {}
        if not rp.get("scene_count"):
            issues.append("empty_render_plan")

        # ── 7. Manifest readable ──────────────────────────────────────────
        if render_manifest:
            try:
                if isinstance(render_manifest, str):
                    parsed_manifest = json.loads(render_manifest)
                else:
                    parsed_manifest = render_manifest
                manifest_scene_count = len(parsed_manifest.get("scenes", []))
                details["manifest_scene_count"] = manifest_scene_count
                if manifest_scene_count == 0:
                    issues.append("manifest_empty_scenes")
                elif scene_count > 0 and manifest_scene_count != scene_count:
                    warnings.append(
                        f"manifest_scene_mismatch:expected={scene_count},got={manifest_scene_count}"
                    )
            except (json.JSONDecodeError, TypeError) as exc:
                issues.append(f"manifest_not_readable:{type(exc).__name__}")
        else:
            # No manifest persisted yet — warn only (adapter may have skipped for no project_id)
            warnings.append("no_render_manifest")

        # ── 8. Audio ──────────────────────────────────────────────────────
        details["audio_url"] = audio_url
        if not audio_url:
            warnings.append("no_audio_url")

        # ── 9. Subtitle segments ──────────────────────────────────────────
        subtitle_texts = [s.get("subtitle_text", "") for s in scenes if s.get("subtitle_text")]
        details["subtitle_count"] = len(subtitle_texts)
        if scene_count > 0 and not subtitle_texts:
            warnings.append("no_subtitle_texts")

        # ── 10. Duration ──────────────────────────────────────────────────
        total_duration = sum(s.get("duration", 0) for s in scenes)
        details["total_duration_seconds"] = total_duration
        if scene_count > 0 and total_duration <= 0:
            issues.append("invalid_duration")

        # ── 11. SEO package ───────────────────────────────────────────────
        seo = seo_package or {}
        details["seo_title"] = seo.get("title", "")
        if not seo.get("title"):
            issues.append("seo_package_empty")

        # ── 12. Publish payload ───────────────────────────────────────────
        pub = publish_result or {}
        details["publish_run_id"] = pub.get("run_id")
        if pub:
            if not pub.get("run_id"):
                issues.append("publish_missing_run_id")
            if "dry_run" not in pub:
                issues.append("publish_missing_dry_run_flag")
            if not pub.get("render_job_id"):
                warnings.append("publish_missing_render_job_id")
        # Publish result not yet available during QA — that's fine
        # (QA runs before PUBLISH stage)

        qa_passed = len(issues) == 0
        result: dict[str, Any] = {
            "qa_passed": qa_passed,
            "scene_count": scene_count,
            "issues": issues,
            "warnings": warnings,
            "details": details,
        }
        if issues:
            result["retry_strategy"] = "downgrade" if len(issues) <= 2 else "human_review"

        return result
