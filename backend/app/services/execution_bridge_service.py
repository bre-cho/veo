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
        }

    def resolve_project_context(self, db, project: dict[str, Any]) -> dict[str, Any]:
        return self.resolve_context(
            db,
            avatar_id=project.get("avatar_id"),
            market_code=project.get("market_code"),
            content_goal=project.get("content_goal"),
            conversion_mode=project.get("conversion_mode"),
        )

    def apply_to_preview_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        updated = {**payload}
        context = {
            "avatar_id": updated.get("avatar_id"),
            "market_code": updated.get("market_code"),
            "content_goal": updated.get("content_goal"),
            "conversion_mode": updated.get("conversion_mode"),
            "template_family": updated.get("template_family"),
        }
        scenes = updated.get("scenes") or []
        updated["scenes"] = [self.apply_to_project_scene(scene, context) for scene in scenes]
        return updated

    def apply_to_project_scene(self, scene: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        updated = {**scene}
        metadata = dict(updated.get("metadata") or {})
        metadata["execution_context"] = self._compact_context(ctx)
        self._apply_conversion_metadata(metadata, ctx)

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
                parts.append("Goal: conversion content with offer clarity.")
            else:
                parts.append(f"Goal: {content_goal}.")

        conversion_mode = (ctx.get("conversion_mode") or "").strip()
        if conversion_mode:
            parts.append(f"CTA bias: {conversion_mode} with open-loop momentum.")

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
        return {
            "avatar_id": ctx.get("avatar_id"),
            "market_code": ctx.get("market_code"),
            "content_goal": ctx.get("content_goal"),
            "conversion_mode": ctx.get("conversion_mode"),
            "template_family": ctx.get("template_family"),
        }

    def _is_conversion_goal(self, ctx: dict[str, Any]) -> bool:
        return str(ctx.get("content_goal") or "").strip().lower() == "conversion"
