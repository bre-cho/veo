"""avatar_tournament_engine — runs avatar selection tournaments.

Flow
----
1. Collect candidate avatar IDs (from request or AVATAR_REGISTRY)
2. Score each candidate via scorecard + pair optimizer + weight engine
3. Apply governance state (exclude blocked/cooldown from exploitation)
4. Rank candidates by final_rank_score
5. Pick winner via exploit-or-explore policy
6. Persist tournament run + match results
7. Return AvatarTournamentResult with explanation
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.avatar_match_result import AvatarMatchResult
from app.models.avatar_policy_state import AvatarPolicyState
from app.models.avatar_tournament_run import AvatarTournamentRun
from app.schemas.avatar_tournament import (
    AvatarCandidateScore,
    AvatarTournamentRequest,
    AvatarTournamentResult,
)
from app.services.avatar.avatar_pair_optimizer import AvatarPairOptimizer
from app.services.avatar.avatar_policy_engine import (
    AvatarPolicyEngine,
    EXPLORATION_FLOOR,
)
from app.services.avatar.avatar_registry import AVATAR_REGISTRY
from app.services.avatar.avatar_scorecard import AvatarScorecard
from app.services.avatar.avatar_selection_explainer import AvatarSelectionExplainer
from app.services.avatar.avatar_weight_engine import AvatarWeightEngine


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AvatarTournamentEngine:
    """Runs a multi-candidate avatar selection tournament."""

    def __init__(self) -> None:
        self._scorecard = AvatarScorecard()
        self._pair_optimizer = AvatarPairOptimizer()
        self._weight_engine = AvatarWeightEngine()
        self._policy_engine = AvatarPolicyEngine()
        self._explainer = AvatarSelectionExplainer()

    # ── Public API ────────────────────────────────────────────────────────────

    def run_tournament(
        self,
        db: Session | None,
        request: AvatarTournamentRequest,
    ) -> AvatarTournamentResult:
        """Run a full tournament and return the selected avatar + ranking."""
        run_id = str(uuid.uuid4())

        # Resolve candidate list
        candidate_ids = list(request.candidate_avatar_ids)
        if not candidate_ids:
            candidate_ids = list(AVATAR_REGISTRY.keys())

        # Force-include specific IDs
        for fid in request.force_avatar_ids:
            if fid not in candidate_ids:
                candidate_ids.insert(0, fid)

        # Score all candidates
        scored = self._score_candidates(
            db=db,
            avatar_ids=candidate_ids,
            request=request,
        )
        ranked = sorted(scored, key=lambda x: x.final_rank_score, reverse=True)

        # Choose selection mode
        exploration_ratio = max(EXPLORATION_FLOOR, request.exploration_ratio)
        use_explore = random.random() < exploration_ratio
        selection_mode = "explore" if use_explore else "exploit"
        if request.force_avatar_ids:
            selection_mode = "forced_test"

        # Pick winner
        selected = self._pick_winner(ranked, selection_mode)
        is_exploration = selection_mode == "explore"

        # Build explanation
        explanation = self._explainer.build_tournament_explanation(
            selected_avatar_id=selected.avatar_id,
            ranked_candidates=[c.model_dump() for c in ranked],
            selection_mode=selection_mode,
        )

        # Persist to DB (non-fatal)
        if db is not None:
            try:
                self._persist_run(
                    db,
                    run_id=run_id,
                    request=request,
                    selection_mode=selection_mode,
                    ranked=ranked,
                    selected_avatar_id=selected.avatar_id,
                    is_exploration=is_exploration,
                )
            except Exception:
                pass

        return AvatarTournamentResult(
            tournament_run_id=run_id,
            selected_avatar_id=selected.avatar_id,
            ranked_candidates=ranked,
            selection_mode=selection_mode,
            explanation=explanation,
        )

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_candidates(
        self,
        *,
        db: Session | None,
        avatar_ids: list[str],
        request: AvatarTournamentRequest,
    ) -> list[AvatarCandidateScore]:
        scores: list[AvatarCandidateScore] = []
        policy_states = self._load_policy_states(db, avatar_ids) if db else {}

        for avatar_id in avatar_ids:
            profile = AVATAR_REGISTRY.get(avatar_id, {})
            policy = policy_states.get(avatar_id)
            state = policy.state if policy else "candidate"

            # Skip blocked / retired avatars entirely
            if state in ("blocked", "retired"):
                continue

            in_cooldown = self._policy_engine.is_in_cooldown(
                policy.cooldown_until if policy else None
            )
            base_weight = policy.priority_weight if policy else 0.5

            # Predict base score from registry profile affinity
            predicted_score = self._predict_score(
                profile=profile,
                request=request,
            )

            # Pair fit bonus
            pair_score = self._compute_pair_bonus(
                avatar_id=avatar_id,
                template_family=request.template_family,
                topic_class=request.topic_class,
            )
            pair_bonus = self._weight_engine.compute_pair_bonus(
                pair_score=pair_score, pair_confidence=1.0
            )

            # Continuity bonus
            continuity_confidence = policy.continuity_confidence if policy else None
            continuity_bonus = self._weight_engine.compute_continuity_bonus(
                continuity_confidence=continuity_confidence
            )

            # Governance penalty
            governance_penalty = self._policy_engine.compute_governance_penalty(
                has_continuity_break=False,
                has_brand_drift=False,
                has_retention_drop=False,
            )

            # Final rank score (penalise cooldown candidates heavily)
            final_rank_score = self._weight_engine.compute(
                base_priority_weight=base_weight,
                pair_bonus=pair_bonus,
                continuity_bonus=continuity_bonus,
                governance_penalty=governance_penalty + (0.4 if in_cooldown else 0.0),
            )

            scores.append(
                AvatarCandidateScore(
                    avatar_id=avatar_id,
                    predicted_score=round(predicted_score, 4),
                    continuity_score=continuity_confidence,
                    pair_fit_score=round(pair_score, 4),
                    governance_penalty=round(governance_penalty, 4),
                    final_rank_score=round(final_rank_score, 4),
                )
            )

        return scores

    def _predict_score(
        self,
        *,
        profile: dict[str, Any],
        request: AvatarTournamentRequest,
    ) -> float:
        """Simple affinity-based predicted score from registry profile."""
        score = 0.5  # default baseline

        # Topic class match
        topic_classes = profile.get("topic_classes") or []
        if request.topic_class and request.topic_class in topic_classes:
            score += 0.15

        # Content goal match
        content_goals = profile.get("content_goals") or []
        if request.content_goal and request.content_goal in content_goals:
            score += 0.15

        # Market match
        profile_market = profile.get("market_code")
        if profile_market and request.market_code:
            if profile_market == request.market_code:
                score += 0.10

        return min(round(score, 4), 1.0)

    def _compute_pair_bonus(
        self,
        *,
        avatar_id: str,
        template_family: str | None,
        topic_class: str | None,
    ) -> float:
        """Return a simple pair bonus. Phase 1: registry-based only."""
        profile = AVATAR_REGISTRY.get(avatar_id, {})
        topic_classes = profile.get("topic_classes") or []
        if topic_class and topic_class in topic_classes:
            return 0.8
        return 0.4

    # ── Selection ─────────────────────────────────────────────────────────────

    def _pick_winner(
        self,
        ranked: list[AvatarCandidateScore],
        selection_mode: str,
    ) -> AvatarCandidateScore:
        if not ranked:
            # Fallback to first registry avatar
            fallback_id = next(iter(AVATAR_REGISTRY), "narrator_dark_doc_v1")
            return AvatarCandidateScore(
                avatar_id=fallback_id,
                predicted_score=0.5,
                final_rank_score=0.5,
            )

        if selection_mode == "exploit":
            return ranked[0]

        if selection_mode == "explore" and len(ranked) > 1:
            # Pick from the lower half of the ranking
            exploration_pool = ranked[len(ranked) // 2:] or ranked
            return random.choice(exploration_pool)

        return ranked[0]

    # ── DB persistence ────────────────────────────────────────────────────────

    def _load_policy_states(
        self,
        db: Session,
        avatar_ids: list[str],
    ) -> dict[str, AvatarPolicyState]:
        rows = (
            db.query(AvatarPolicyState)
            .filter(AvatarPolicyState.avatar_id.in_(avatar_ids))
            .all()
        )
        return {r.avatar_id: r for r in rows}

    def _persist_run(
        self,
        db: Session,
        *,
        run_id: str,
        request: AvatarTournamentRequest,
        selection_mode: str,
        ranked: list[AvatarCandidateScore],
        selected_avatar_id: str,
        is_exploration: bool,
    ) -> None:
        now = _now()
        run = AvatarTournamentRun(
            id=run_id,
            project_id=request.project_id,
            workspace_id=request.workspace_id,
            template_family=request.template_family,
            platform=request.platform,
            status="completed",
            selection_mode=selection_mode,
            started_at=now,
            completed_at=now,
        )
        db.add(run)

        for rank, candidate in enumerate(ranked, start=1):
            db.add(
                AvatarMatchResult(
                    tournament_run_id=run_id,
                    avatar_id=candidate.avatar_id,
                    predicted_score=candidate.predicted_score,
                    predicted_retention=candidate.predicted_retention,
                    predicted_ctr=candidate.predicted_ctr,
                    predicted_conversion=candidate.predicted_conversion,
                    selection_rank=rank,
                    was_published=(candidate.avatar_id == selected_avatar_id),
                    was_exploration=is_exploration and (candidate.avatar_id == selected_avatar_id),
                    result_label="winner" if candidate.avatar_id == selected_avatar_id else "neutral",
                )
            )

        db.commit()
