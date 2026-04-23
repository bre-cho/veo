"""template_registry — seed catalog of template definitions.

Each entry is a fully-specified TemplateDefinition.  The registry is
intentionally a plain dict so BrainDecisionEngine and TemplateSelector can
iterate over it without a DB round-trip.
"""
from __future__ import annotations

from app.schemas.template_system import TemplateDefinition, TemplatePromptBias, TemplateBestFor


TEMPLATE_REGISTRY: dict[str, TemplateDefinition] = {
    "invisible_system_control": TemplateDefinition(
        template_id="invisible_system_control",
        template_family="documentary_retention",
        narrative_mode="reveal_escalation",
        hook_strategy="invisible_shift",
        scene_sequence=[
            "hook",
            "pattern_reveal",
            "escalation",
            "system_explanation",
            "identity_impact",
            "open_loop_cta",
        ],
        pacing_profile={
            "hook": 1.8,
            "pattern_reveal": 1.4,
            "escalation": 1.5,
            "system_explanation": 1.2,
            "identity_impact": 1.3,
            "open_loop_cta": 1.1,
        },
        shot_profile={
            "hook": "tight_closeup",
            "pattern_reveal": "slow_push",
            "escalation": "tracking_tension",
            "system_explanation": "medium_locked",
            "identity_impact": "close_emotive",
            "open_loop_cta": "linger_exit",
        },
        prompt_bias=TemplatePromptBias(
            tone="dark_systemic",
            contrast="high",
            emotion="unease",
            visual_density="dense",
        ),
        cta_style="series_open_loop",
        best_for=TemplateBestFor(
            content_goal=["retention", "series_binge"],
            market_code=["US"],
            topic_classes=["ai", "control", "attention", "system"],
        ),
    ),
    "shock_reveal_chain": TemplateDefinition(
        template_id="shock_reveal_chain",
        template_family="viral_shock",
        narrative_mode="shock_then_explain",
        hook_strategy="immediate_disruption",
        scene_sequence=[
            "shock_hook",
            "contrast_reveal",
            "proof_block",
            "implication",
            "next_secret_cta",
        ],
        pacing_profile={
            "shock_hook": 2.0,
            "contrast_reveal": 1.5,
            "proof_block": 1.2,
            "implication": 1.3,
            "next_secret_cta": 1.1,
        },
        shot_profile={
            "shock_hook": "hard_cut_close",
            "contrast_reveal": "fast_push",
            "proof_block": "evidence_stack",
            "implication": "slow_drift",
            "next_secret_cta": "exit_linger",
        },
        prompt_bias=TemplatePromptBias(
            tone="urgent",
            contrast="very_high",
            emotion="shock",
            visual_density="medium_dense",
        ),
        cta_style="curiosity_cliffhanger",
        best_for=TemplateBestFor(
            content_goal=["ctr", "retention"],
            market_code=["US"],
            topic_classes=["war", "scandal", "collapse", "ai"],
        ),
    ),
    "story_chain_retention": TemplateDefinition(
        template_id="story_chain_retention",
        template_family="story_series",
        narrative_mode="story_escalation",
        hook_strategy="human_problem_entry",
        scene_sequence=[
            "human_hook",
            "problem",
            "hidden_force",
            "escalation",
            "micro_resolution",
            "next_arc_cta",
        ],
        pacing_profile={
            "human_hook": 1.6,
            "problem": 1.2,
            "hidden_force": 1.4,
            "escalation": 1.4,
            "micro_resolution": 1.0,
            "next_arc_cta": 1.2,
        },
        shot_profile={
            "human_hook": "character_close",
            "problem": "context_medium",
            "hidden_force": "symbolic_push",
            "escalation": "tracking_rise",
            "micro_resolution": "steady_hold",
            "next_arc_cta": "fade_out_tease",
        },
        prompt_bias=TemplatePromptBias(
            tone="cinematic_story",
            contrast="balanced",
            emotion="tension",
            visual_density="balanced",
        ),
        cta_style="episode_chain",
        best_for=TemplateBestFor(
            content_goal=["series_binge", "retention"],
            market_code=["US"],
            topic_classes=["documentary", "biography", "mystery", "system"],
        ),
    ),
}
