from __future__ import annotations

from typing import Any

from app.models.autovis import TemplateFamily
from app.repositories.avatar_repo import AvatarRepo
from app.repositories.localization_repo import LocalizationRepo


class ExecutionBridgeService:
    PROJECT_SCENE_CONVERSION_MAX_DURATION_SEC = 25.0
    PROJECT_SCENE_CONVERSION_BONUS_SEC = 0.5
    RENDER_SCENE_CONVERSION_MIN_DURATION_SEC = 3
    RENDER_SCENE_CONVERSION_MAX_DURATION_SEC = 60
    RENDER_SCENE_CONVERSION_BONUS_SEC = 1
    CONVERSION_GOAL_PROMPT = "Goal: conversion content with offer clarity."

    def __init__(self) -> None:
        self._avatar_repo = AvatarRepo()
        self._localization_repo = LocalizationRepo()

    def resolve_context(
        self,
        db,
        *,
        avatar_id: str | None = None,
        market_code: str | None = None,
        content_goal: str | None = None,
        conversion_mode: str | None = None,
        storyboard: dict[str, Any] | None = None,
        optimization_response: dict[str, Any] | None = None,
        winner_patterns: list[dict[str, Any]] | None = None,
        # Brain Layer fields
        series_id: str | None = None,
        episode_index: int | None = None,
        continuity_context: dict[str, Any] | None = None,
        winner_dna_summary: dict[str, Any] | None = None,
        brain_plan: dict[str, Any] | None = None,
        # Template System fields
        template_prompt_bias: dict[str, Any] | None = None,
        # Avatar System fields
        avatar_identity: dict[str, Any] | None = None,
        avatar_voice: dict[str, Any] | None = None,
        avatar_continuity: dict[str, Any] | None = None,
        # Avatar Tournament fields
        avatar_selection_debug: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        avatar: dict[str, Any] | None = None
        market: dict[str, Any] | None = None

        if db is not None and avatar_id:
            avatar_row = self._avatar_repo.get_avatar(db, avatar_id)
            if avatar_row is not None:
                avatar = {
                    "id": avatar_row.id,
                    "name": avatar_row.name,
                    "role_id": avatar_row.role_id,
                    "niche_code": avatar_row.niche_code,
                    "market_code": avatar_row.market_code,
                }
                market_code = market_code or avatar_row.market_code

        if db is not None and market_code:
            market_row = self._localization_repo.get_profile(db, market_code)
            if market_row is not None:
                market = {
                    "market_code": market_row.market_code,
                    "country_name": market_row.country_name,
                    "language_code": market_row.language_code,
                    "currency_code": market_row.currency_code,
                    "timezone": market_row.timezone,
                    "rtl": market_row.rtl,
                }

        template_family = self._resolve_template_family(
            db,
            content_goal=content_goal,
            market_code=market_code,
        )

        return {
            "avatar_id": avatar_id,
            "market_code": market_code,
            "content_goal": content_goal,
            "conversion_mode": conversion_mode,
            "avatar": avatar,
            "market": market,
            "template_family": template_family,
            "storyboard": storyboard,
            "optimization_response": optimization_response,
            "winner_patterns": winner_patterns or [],
            # Brain Layer fields
            "series_id": series_id,
            "episode_index": episode_index,
            "continuity_context": continuity_context,
            "winner_dna_summary": winner_dna_summary,
            "brain_plan": brain_plan,
            # Template System fields
            "template_prompt_bias": template_prompt_bias or {},
            # Avatar System fields
            "avatar_identity": avatar_identity or {},
            "avatar_voice": avatar_voice or {},
            "avatar_continuity": avatar_continuity or {},
            # Avatar Tournament fields
            "avatar_selection_debug": avatar_selection_debug or {},
        }

    def resolve_project_context(self, db, project: dict[str, Any]) -> dict[str, Any]:
        return self.resolve_context(
            db,
            avatar_id=project.get("avatar_id"),
            market_code=project.get("market_code"),
            content_goal=project.get("content_goal"),
            conversion_mode=project.get("conversion_mode"),
            storyboard=project.get("storyboard"),
            optimization_response=project.get("optimization_response"),
            winner_patterns=project.get("winner_patterns"),
            series_id=project.get("series_id"),
            episode_index=project.get("episode_index"),
            continuity_context=project.get("continuity_context"),
            winner_dna_summary=project.get("winner_dna_summary"),
            brain_plan=project.get("brain_plan"),
            avatar_identity=project.get("avatar_identity"),
            avatar_voice=project.get("avatar_voice"),
            avatar_continuity=project.get("avatar_continuity"),
            avatar_selection_debug=project.get("avatar_selection_debug"),
        )

    def apply_to_preview_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        updated = {**payload}
        context = {
            "avatar_id": updated.get("avatar_id"),
            "market_code": updated.get("market_code"),
            "content_goal": updated.get("content_goal"),
            "conversion_mode": updated.get("conversion_mode"),
            "template_family": updated.get("template_family"),
            "storyboard": updated.get("storyboard"),
            "optimization_response": updated.get("optimization_response"),
            "winner_patterns": updated.get("winner_patterns") or [],
            # Brain Layer fields
            "series_id": updated.get("series_id"),
            "episode_index": updated.get("episode_index"),
            "continuity_context": updated.get("continuity_context") or {},
            "winner_dna_summary": updated.get("winner_dna_summary") or {},
            "brain_plan": updated.get("brain_plan") or {},
        }
        scenes = updated.get("scenes") or []
        updated["scenes"] = [self.apply_to_project_scene(scene, context) for scene in scenes]
        return updated

    def apply_to_project_scene(self, scene: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        updated = {**scene}
        metadata = dict(updated.get("metadata") or {})
        metadata["execution_context"] = self._compact_context(ctx)
        self._apply_conversion_metadata(metadata, ctx)
        self._apply_storyboard_and_optimization(updated, metadata, ctx)

        base_visual_prompt = (
            updated.get("visual_prompt")
            or updated.get("prompt_text")
            or updated.get("script_text")
            or updated.get("title")
            or ""
        )
        updated["visual_prompt"] = self._prepend_context_prompt(base_visual_prompt, ctx)

        if "prompt_text" in updated and updated.get("prompt_text"):
            updated["prompt_text"] = self._prepend_context_prompt(str(updated["prompt_text"]), ctx)

        if self._is_conversion_goal(ctx):
            title = str(updated.get("title") or "").strip()
            if title and "offer" not in title.lower():
                updated["title"] = f"{title} — Offer clarity"
            try:
                duration = float(updated.get("target_duration_sec"))
                updated["target_duration_sec"] = min(
                    self.PROJECT_SCENE_CONVERSION_MAX_DURATION_SEC,
                    round(duration + self.PROJECT_SCENE_CONVERSION_BONUS_SEC, 1),
                )
            except (TypeError, ValueError):
                pass

        updated["metadata"] = metadata
        return updated

    def transform_scene_payload(self, scene_payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        updated = {**scene_payload}
        metadata = dict(updated.get("metadata") or {})
        metadata["execution_context"] = self._compact_context(ctx)
        self._apply_conversion_metadata(metadata, ctx)
        self._apply_storyboard_and_optimization(updated, metadata, ctx)

        base_prompt = (
            updated.get("resolved_prompt_text")
            or updated.get("prompt_text")
            or updated.get("prompt")
            or updated.get("script_text")
            or updated.get("title")
            or ""
        )
        updated["resolved_prompt_text"] = self._prepend_context_prompt(base_prompt, ctx)

        if updated.get("prompt_text"):
            updated["prompt_text"] = self._prepend_context_prompt(str(updated["prompt_text"]), ctx)

        if self._is_conversion_goal(ctx):
            for duration_key in ("resolved_duration_seconds", "provider_target_duration_sec", "duration_seconds"):
                value = updated.get(duration_key)
                if value is None:
                    continue
                try:
                    updated[duration_key] = min(
                        self.RENDER_SCENE_CONVERSION_MAX_DURATION_SEC,
                        max(
                            self.RENDER_SCENE_CONVERSION_MIN_DURATION_SEC,
                            int(value) + self.RENDER_SCENE_CONVERSION_BONUS_SEC,
                        ),
                    )
                except (TypeError, ValueError):
                    continue

        updated["metadata"] = metadata
        return updated

    def _resolve_template_family(
        self,
        db,
        *,
        content_goal: str | None,
        market_code: str | None,
    ) -> str | None:
        if db is None or not content_goal:
            return None

        rows = (
            db.query(TemplateFamily)
            .filter(
                TemplateFamily.is_active.is_(True),
                TemplateFamily.content_goal == content_goal,
            )
            .order_by(TemplateFamily.created_at.desc())
            .all()
        )
        if not rows:
            return None

        if market_code:
            for row in rows:
                market_codes = row.market_codes or []
                if isinstance(market_codes, list) and market_code in market_codes:
                    return row.name

        return rows[0].name

    def _prepend_context_prompt(self, prompt: str, ctx: dict[str, Any]) -> str:
        prompt = (prompt or "").strip()
        parts: list[str] = []

        avatar_name: str | None = None
        avatar = ctx.get("avatar")
        if isinstance(avatar, dict):
            avatar_name = avatar.get("name")
        avatar_name = avatar_name or ctx.get("avatar_id")
        if avatar_name:
            parts.append(f"Avatar framing: {avatar_name}.")

        market = ctx.get("market") if isinstance(ctx.get("market"), dict) else None
        if market:
            country = market.get("country_name") or market.get("market_code")
            lang = market.get("language_code")
            tone = f"Market tone: {country}"
            if lang:
                tone += f", language {lang}"
            parts.append(f"{tone}.")
        elif ctx.get("market_code"):
            parts.append(f"Market tone: {ctx.get('market_code')}.")

        content_goal = (ctx.get("content_goal") or "").strip()
        if content_goal:
            if content_goal.lower() == "conversion":
                parts.append(self.CONVERSION_GOAL_PROMPT)
            else:
                parts.append(f"Goal: {content_goal}.")

        conversion_mode = (ctx.get("conversion_mode") or "").strip()
        if conversion_mode:
            parts.append(f"CTA bias: {conversion_mode} with open-loop momentum.")

        # Brain Layer context hints (brief, non-redundant)
        series_id = (ctx.get("series_id") or "").strip()
        if series_id:
            continuity = ctx.get("continuity_context") or {}
            unresolved = continuity.get("unresolved_loops") or []
            episode_role = continuity.get("episode_role")
            if not episode_role:
                brain_plan = ctx.get("brain_plan") or {}
                if isinstance(brain_plan, dict):
                    episode_role = brain_plan.get("episode_role")
            if episode_role:
                parts.append(f"Episode role: {episode_role}.")
            if unresolved:
                parts.append(f"Series continuity: preserve unresolved loop about {unresolved[0]}.")

        winner_dna = ctx.get("winner_dna_summary") or {}
        if isinstance(winner_dna, dict) and winner_dna.get("hook_core"):
            parts.append(f"Winner DNA: {winner_dna['hook_core']}.")

        # Template System: inject template identity and visual bias from brain plan
        brain_notes = (ctx.get("brain_plan") or {}).get("notes") or {}
        template_id = brain_notes.get("selected_template_id")
        template_family = brain_notes.get("selected_template_family")
        template_prompt_bias = brain_notes.get("template_prompt_bias") or {}

        if template_id:
            parts.append(f"Template: {template_id}.")
        if template_family:
            parts.append(f"Template family: {template_family}.")

        prompt_bias = template_prompt_bias.get("prompt_bias") or {}
        if isinstance(prompt_bias, dict):
            if prompt_bias.get("tone"):
                parts.append(f"Tone bias: {prompt_bias['tone']}.")
            if prompt_bias.get("emotion"):
                parts.append(f"Emotion bias: {prompt_bias['emotion']}.")
            if prompt_bias.get("contrast"):
                parts.append(f"Contrast bias: {prompt_bias['contrast']}.")
        cta_style = template_prompt_bias.get("cta_style")
        if cta_style:
            parts.append(f"CTA style: {cta_style}.")

        # Avatar System: inject avatar identity context into prompt
        avatar_identity = ctx.get("avatar_identity") or {}
        avatar_voice = ctx.get("avatar_voice") or {}
        avatar_continuity = ctx.get("avatar_continuity") or {}

        if avatar_identity.get("display_name"):
            parts.append(f"Avatar: {avatar_identity['display_name']}.")
        if avatar_identity.get("persona"):
            parts.append(f"Avatar persona: {avatar_identity['persona']}.")
        if avatar_identity.get("tone"):
            parts.append(f"Avatar tone: {avatar_identity['tone']}.")
        if avatar_voice.get("delivery_style"):
            parts.append(f"Voice delivery: {avatar_voice['delivery_style']}.")
        if avatar_continuity.get("emotion_curve"):
            parts.append(f"Emotion curve: {avatar_continuity['emotion_curve']}.")

        if not parts:
            return prompt

        prefix = " ".join(parts).strip()
        if not prompt:
            return prefix
        return f"{prefix} {prompt}".strip()

    def _apply_conversion_metadata(self, metadata: dict[str, Any], ctx: dict[str, Any]) -> None:
        conversion_mode = ctx.get("conversion_mode")
        if conversion_mode:
            metadata["cta_bias"] = conversion_mode
            metadata["open_loop_bias"] = True

    def _compact_context(self, ctx: dict[str, Any]) -> dict[str, Any]:
        brain_notes = (ctx.get("brain_plan") or {}).get("notes") or {}
        avatar_selection = brain_notes.get("avatar_selection") or {}
        return {
            "avatar_id": ctx.get("avatar_id"),
            "market_code": ctx.get("market_code"),
            "content_goal": ctx.get("content_goal"),
            "conversion_mode": ctx.get("conversion_mode"),
            "template_family": ctx.get("template_family"),
            "has_storyboard": bool(ctx.get("storyboard")),
            "has_optimization_response": bool(ctx.get("optimization_response")),
            # Brain Layer fields
            "series_id": ctx.get("series_id"),
            "episode_index": ctx.get("episode_index"),
            "continuity_context": ctx.get("continuity_context"),
            "winner_dna_summary": ctx.get("winner_dna_summary"),
            "brain_plan": ctx.get("brain_plan"),
            # Template System fields (sourced from brain_plan.notes for consistency)
            "selected_template_id": brain_notes.get("selected_template_id"),
            "selected_template_family": brain_notes.get("selected_template_family"),
            "template_prompt_bias": brain_notes.get("template_prompt_bias") or {},
            # Avatar System fields
            "avatar_identity": ctx.get("avatar_identity") or {},
            "avatar_voice": ctx.get("avatar_voice") or {},
            "avatar_continuity": ctx.get("avatar_continuity") or {},
            # Avatar Tournament fields
            "avatar_selection_debug": ctx.get("avatar_selection_debug") or {},
            "avatar_tournament_run_id": avatar_selection.get("tournament_run_id"),
            "avatar_selection_mode": avatar_selection.get("selection_mode"),
        }

    def _is_conversion_goal(self, ctx: dict[str, Any]) -> bool:
        return str(ctx.get("content_goal") or "").strip().lower() == "conversion"

    def _apply_storyboard_and_optimization(
        self,
        updated: dict[str, Any],
        metadata: dict[str, Any],
        ctx: dict[str, Any],
    ) -> None:
        try:
            scene_index = int(updated.get("scene_index") or 0)
        except (TypeError, ValueError):
            scene_index = 0
        storyboard = ctx.get("storyboard") or {}
        storyboard_scenes = storyboard.get("scenes") if isinstance(storyboard, dict) else None
        if isinstance(storyboard_scenes, list) and scene_index > 0:
            matched = next(
                (
                    s
                    for s in storyboard_scenes
                    if int(s.get("scene_index", 0)) == scene_index
                ),
                None,
            )
            if matched:
                if matched.get("scene_goal"):
                    metadata["scene_goal"] = matched.get("scene_goal")
                if matched.get("shot_hint"):
                    metadata["shot_hint"] = matched.get("shot_hint")
                    updated.setdefault("shot_hint", matched.get("shot_hint"))
                if matched.get("pacing_weight") is not None:
                    metadata["pacing_weight"] = matched.get("pacing_weight")
                if matched.get("cta_flag"):
                    metadata["cta_bias"] = ctx.get("conversion_mode") or "default"

        optimization = ctx.get("optimization_response") or {}
        rewrites = optimization.get("rewrite_suggestions") if isinstance(optimization, dict) else None
        if isinstance(rewrites, list) and scene_index > 0:
            matched_rewrite = next(
                (
                    r
                    for r in rewrites
                    if int(r.get("target_scene_index", 0)) == scene_index
                ),
                None,
            )
            if matched_rewrite:
                metadata["optimization_type"] = matched_rewrite.get("type")
                replacement = matched_rewrite.get("replacement_text")
                if replacement:
                    updated["script_text"] = replacement

        winner_patterns = ctx.get("winner_patterns") or []
        if winner_patterns:
            top_pattern = winner_patterns[0]
            if isinstance(top_pattern, dict):
                metadata["trust_bias"] = top_pattern.get("score")

        # Brain Layer: inject continuity and winner DNA into scene metadata
        continuity = ctx.get("continuity_context") or {}
        if continuity:
            metadata["series_id"] = continuity.get("series_id")
            metadata["episode_index"] = continuity.get("episode_index")
            metadata["episode_role"] = continuity.get("episode_role")
            metadata["callback_targets"] = continuity.get("callback_targets") or []
            metadata["continuity_constraints"] = continuity.get("continuity_constraints") or {}

        winner_dna = ctx.get("winner_dna_summary") or {}
        if winner_dna:
            metadata["winner_dna_summary"] = winner_dna

        # Template System: inject selected template metadata into scene metadata
        brain_notes = (ctx.get("brain_plan") or {}).get("notes") or {}
        if brain_notes.get("selected_template_id"):
            metadata["selected_template_id"] = brain_notes.get("selected_template_id")
        if brain_notes.get("selected_template_family"):
            metadata["selected_template_family"] = brain_notes.get("selected_template_family")
        if brain_notes.get("template_prompt_bias"):
            metadata["template_prompt_bias"] = brain_notes.get("template_prompt_bias")

        # Avatar System: inject avatar context into scene metadata
        avatar_identity = ctx.get("avatar_identity") or {}
        if avatar_identity:
            metadata["avatar_id"] = avatar_identity.get("avatar_id")
            metadata["avatar_persona"] = avatar_identity.get("persona")
            metadata["avatar_tone"] = avatar_identity.get("tone")
            metadata["avatar_visual_style"] = avatar_identity.get("visual_style")

        avatar_voice = ctx.get("avatar_voice") or {}
        if avatar_voice:
            metadata["avatar_voice"] = avatar_voice

        avatar_continuity = ctx.get("avatar_continuity") or {}
        if avatar_continuity:
            metadata["avatar_continuity"] = avatar_continuity

        # Direct avatar_id fallback: if avatar_identity didn't carry avatar_id, use ctx-level one
        if not metadata.get("avatar_id") and ctx.get("avatar_id"):
            metadata["avatar_id"] = ctx.get("avatar_id")

        # Avatar Tournament fields
        avatar_selection_debug = ctx.get("avatar_selection_debug") or {}
        brain_notes = (ctx.get("brain_plan") or {}).get("notes") or {}
        avatar_selection = brain_notes.get("avatar_selection") or {}

        if avatar_selection_debug or avatar_selection:
            # Use tournament explanation if available, fall back to legacy debug payload
            explanation = avatar_selection.get("explanation") or {}
            ranking_summary = explanation.get("ranking_summary") or avatar_selection_debug.get("ranking_summary") or []
            metadata["avatar_selection_reason"] = ranking_summary[:1]
            metadata["avatar_selection_mode"] = (
                avatar_selection.get("selection_mode")
                or avatar_selection_debug.get("selection_mode")
            )
            tournament_run_id = (
                avatar_selection.get("tournament_run_id")
                or avatar_selection_debug.get("tournament_run_id")
            )
            if tournament_run_id:
                metadata["avatar_tournament_run_id"] = tournament_run_id
            if avatar_selection.get("selection_mode"):
                metadata["avatar_policy_state"] = avatar_selection["selection_mode"]
