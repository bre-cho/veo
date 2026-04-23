from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from random import random
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.avatar_match_result import AvatarMatchResult
from app.models.avatar_policy_state import AvatarPolicyState
from app.models.avatar_tournament_run import AvatarTournamentRun
from app.schemas.avatar_tournament import AvatarCandidateScore, AvatarTournamentRequest, AvatarTournamentResult
from app.services.avatar.avatar_pair_learning_engine import AvatarPairLearningEngine
from app.services.avatar.avatar_policy_engine import AvatarPolicyEngine
from app.services.avatar.avatar_scorecard import AvatarScorecardService
from app.services.avatar.avatar_selection_explainer import AvatarSelectionExplainer
from app.services.avatar.avatar_weight_engine import AvatarWeightEngine


class AvatarTournamentEngine:
    def __init__(
        self,
        db: Session,
        scorecard_service: AvatarScorecardService | None = None,
        pair_learning_engine: AvatarPairLearningEngine | None = None,
        policy_engine: AvatarPolicyEngine | None = None,
        weight_engine: AvatarWeightEngine | None = None,
        selection_explainer: AvatarSelectionExplainer | None = None,
    ) -> None:
        self.db = db
        self.scorecard_service = scorecard_service or AvatarScorecardService()
        self.pair_learning_engine = pair_learning_engine or AvatarPairLearningEngine()
        self.policy_engine = policy_engine or AvatarPolicyEngine()
        self.weight_engine = weight_engine or AvatarWeightEngine()
        self.selection_explainer = selection_explainer or AvatarSelectionExplainer()

    def run_tournament(self, payload: AvatarTournamentRequest) -> AvatarTournamentResult:
        run = AvatarTournamentRun(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            topic_id=payload.topic_id,
            template_family=payload.template_family,
            topic_signature=payload.topic_signature,
            platform=payload.platform,
            status="running",
            selection_mode="exploit",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()

        ranked = self._rank_candidates(payload)
        selected, selection_mode = self._pick_candidate(ranked, payload.exploration_ratio)
        explanation = {
            "selected_avatar_id": str(selected.avatar_id) if selected else None,
            "selection_mode": selection_mode,
            "candidate_count": len(ranked),
        }

        for idx, candidate in enumerate(ranked, start=1):
            self.db.add(
                AvatarMatchResult(
                    tournament_run_id=run.id,
                    avatar_id=candidate.avatar_id,
                    template_id=candidate.template_id,
                    topic_signature=payload.topic_signature,
                    platform=payload.platform,
                    predicted_score=candidate.predicted_score,
                    predicted_ctr=candidate.predicted_ctr,
                    predicted_retention=candidate.predicted_retention,
                    predicted_conversion=candidate.predicted_conversion,
                    continuity_score=candidate.continuity_score,
                    brand_fit_score=candidate.brand_fit_score,
                    pair_fit_score=candidate.pair_fit_score,
                    governance_penalty=candidate.governance_penalty,
                    final_rank_score=candidate.final_rank_score,
                    selection_rank=idx,
                    was_published=(selected is not None and candidate.avatar_id == selected.avatar_id),
                    was_exploration=(selection_mode == "explore" and selected is not None and candidate.avatar_id == selected.avatar_id),
                )
            )

        run.selected_avatar_id = selected.avatar_id if selected else None
        run.selection_mode = selection_mode
        run.status = "completed"
        run.explanation_json = json.dumps(explanation)
        run.completed_at = datetime.now(timezone.utc)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        return AvatarTournamentResult(
            tournament_run_id=run.id,
            selected_avatar_id=run.selected_avatar_id,
            ranked_candidates=ranked,
            selection_mode=selection_mode,
            explanation=explanation,
            created_at=run.created_at,
        )

    def _rank_candidates(self, payload: AvatarTournamentRequest) -> list[AvatarCandidateScore]:
        now = datetime.now(timezone.utc)
        ranked: list[AvatarCandidateScore] = []
        for avatar_id in payload.candidate_avatar_ids:
            state = self._get_policy_state(avatar_id)
            predicted = self.scorecard_service.build_predicted_scorecard(avatar_id=avatar_id, context=payload.metadata)
            pair = self.pair_learning_engine.get_pair_features(
                avatar_id=avatar_id,
                template_family=payload.template_family,
                topic_signature=payload.topic_signature,
                platform=payload.platform,
            )
            continuity_bonus = max((predicted.get("continuity_score") or 0.0) - 0.5, 0.0)
            exploration_bonus = 0.0
            governance_penalty = self.weight_engine.compute_governance_penalty(
                state=state.state,
                risk_weight=float(state.risk_weight),
                cooldown_until=state.cooldown_until,
                now=now,
            )
            final_score = self.weight_engine.compute_final_score(
                base_score=float(predicted["predicted_score"]),
                priority_weight=float(state.priority_weight),
                pair_bonus=float(pair["pair_bonus"]),
                continuity_bonus=continuity_bonus,
                exploration_bonus=exploration_bonus,
                governance_penalty=governance_penalty,
            )
            ranked.append(
                AvatarCandidateScore(
                    avatar_id=avatar_id,
                    predicted_score=float(predicted["predicted_score"]),
                    predicted_ctr=predicted.get("predicted_ctr"),
                    predicted_retention=predicted.get("predicted_retention"),
                    predicted_conversion=predicted.get("predicted_conversion"),
                    continuity_score=predicted.get("continuity_score"),
                    brand_fit_score=predicted.get("brand_fit_score"),
                    pair_fit_score=float(pair["pair_fit_score"]),
                    pair_confidence=float(pair["pair_confidence"]),
                    governance_penalty=governance_penalty,
                    final_rank_score=final_score,
                )
            )
        ranked.sort(key=lambda item: item.final_rank_score, reverse=True)
        return ranked

    def _pick_candidate(self, ranked: list[AvatarCandidateScore], exploration_ratio: float) -> tuple[AvatarCandidateScore | None, str]:
        if not ranked:
            return None, "exploit"
        if len(ranked) > 1 and random() < max(exploration_ratio, self.policy_engine.get_exploration_floor()):
            return ranked[1], "explore"
        return ranked[0], "exploit"

    def _get_policy_state(self, avatar_id: UUID) -> AvatarPolicyState:
        state = self.db.query(AvatarPolicyState).filter(AvatarPolicyState.avatar_id == avatar_id).one_or_none()
        if state:
            return state
        state = AvatarPolicyState(avatar_id=avatar_id)
        self.db.add(state)
        self.db.flush()
        return state
