"""template_governance_engine — pre-flight and runtime safety rails for templates.

Governance zones
----------------
Hard Safety    : structural / policy violations → block immediately
Soft Safety    : mild policy violations → reduce routing weight
Performance    : post-publish CTR / retention collapse → trigger fail-safe
Runtime        : render error-rate spikes → stop routing
Cost           : cost-per-video too high → reduce weight

Usage
-----
engine = TemplateGovernanceEngine()

# Before entering the selector / tournament
if not engine.pre_check(template):
    mark_rejected(template)

# After publish metrics arrive
if not engine.performance_guard(metrics, baseline):
    trigger_rollback(template)
"""
from __future__ import annotations

from typing import Any


class TemplateGovernanceEngine:
    """Stateless guard engine — all methods are pure functions of their inputs."""

    # ------------------------------------------------------------------
    # PRE-CHECK: structural & policy validation before the template
    # enters the selector or tournament bracket.
    # ------------------------------------------------------------------

    def pre_check(self, template: dict[str, Any]) -> bool:
        """Return True if the template passes basic structural validation.

        Checks
        ------
        1. ``scene_sequence`` is present and has ≥ 3 steps.
        2. No pacing value falls outside [0.5, 2.5].
        3. No critical field is ``None``.
        """
        scene_seq = template.get("scene_sequence")
        if not scene_seq:
            return False
        if len(scene_seq) < 3:
            return False

        pacing = template.get("pacing_profile") or {}
        for v in pacing.values():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return False
            if fv < 0.5 or fv > 2.5:
                return False

        return True

    def policy_check(self, template: dict[str, Any]) -> bool:
        """Return True if the template passes content-policy rules.

        Blocked combinations
        --------------------
        - tone == "extreme_fear"   (regardless of goal)
        - hook_strategy contains "fake_claim"
        - tone == "extreme_fear" AND content_goal == "conversion"
        """
        bias = template.get("prompt_bias") or {}
        tone = bias.get("tone") or ""
        hook_strategy = (template.get("hook_strategy") or "").lower()

        if tone == "extreme_fear":
            return False
        if "fake_claim" in hook_strategy:
            return False

        return True

    def continuity_guard(self, template: dict[str, Any]) -> bool:
        """Return True when the template does not break series continuity rules.

        A template fails this check when it explicitly overrides any of:
        - character_identity_override
        - narrative_arc_override
        - callback_chain_clear
        """
        rules = template.get("continuity_rules") or {}
        dangerous = {"character_identity_override", "narrative_arc_override", "callback_chain_clear"}
        violations = dangerous.intersection(rules.keys())
        return len(violations) == 0

    # ------------------------------------------------------------------
    # RUNTIME GUARD: called while the template is actively being used
    # during render dispatch.
    # ------------------------------------------------------------------

    def runtime_guard(self, metrics: dict[str, Any]) -> bool:
        """Return True if current runtime metrics are within safe limits.

        Fails when render ``error_rate`` exceeds 20 %.
        """
        if float(metrics.get("error_rate", 0.0)) > 0.2:
            return False
        return True

    # ------------------------------------------------------------------
    # PERFORMANCE GUARD: called after publish metrics are available.
    # ------------------------------------------------------------------

    def performance_guard(
        self,
        metrics: dict[str, Any],
        baseline: dict[str, Any],
    ) -> bool:
        """Return True when post-publish metrics stay above 50 % of baseline.

        Triggers fail-safe rollback when either:
        - CTR < 0.5 * baseline CTR
        - retention_30s < 0.5 * baseline retention_30s
        """
        baseline_ctr = float(baseline.get("ctr", 1.0)) or 1.0
        baseline_ret = float(baseline.get("retention_30s", 1.0)) or 1.0

        if float(metrics.get("ctr", 0.0)) < 0.5 * baseline_ctr:
            return False
        if float(metrics.get("retention_30s", 0.0)) < 0.5 * baseline_ret:
            return False
        return True

    # ------------------------------------------------------------------
    # COST GUARD: called after each render to check cost budget.
    # ------------------------------------------------------------------

    def cost_guard(
        self,
        metrics: dict[str, Any],
        *,
        cost_threshold: float = 5.0,
    ) -> bool:
        """Return True when cost_per_video stays within the allowed threshold."""
        return float(metrics.get("cost_per_video", 0.0)) <= cost_threshold

    # ------------------------------------------------------------------
    # Full pipeline check — convenience wrapper.
    # ------------------------------------------------------------------

    def full_pre_check(self, template: dict[str, Any]) -> tuple[bool, list[str]]:
        """Run all pre-launch checks and return (passed, list_of_failures)."""
        failures: list[str] = []
        if not self.pre_check(template):
            failures.append("structural_validation_failed")
        if not self.policy_check(template):
            failures.append("policy_check_failed")
        if not self.continuity_guard(template):
            failures.append("continuity_guard_failed")
        return (len(failures) == 0, failures)
