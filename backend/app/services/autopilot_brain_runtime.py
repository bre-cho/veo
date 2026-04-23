from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.pattern_memory import PatternMemory
from app.schemas.autopilot_brain import (
    AutopilotBrainCompileRequest,
    AutopilotBrainCompileResponse,
    BrainMemoryMatch,
    BrainScorecard,
    BrainSeriesEpisode,
    SEOBridge,
)


_RUNTIME_CLASSIFICATION = [
    (96, "DOMINATION CORE", "DOMINATION"),
    (93, "SCALE CLUSTER", "SCALE"),
    (90, "WINNER", "WINNER"),
    (80, "TEST", "TEST"),
    (0, "BLOCK", "BLOCK"),
]


@dataclass
class _ScoreBundle:
    attention: int
    retention: int
    trust: int
    conversion: int
    scaling: int

    @property
    def total(self) -> int:
        return self.attention + self.retention + self.trust + self.conversion + self.scaling


class AutopilotBrainRuntime:
    """Embed Custom GPT operating principles into the existing codebase.

    This service does not replace render execution. It compiles user topic/script
    into the same decision structure the assistant uses: SIGNAL -> DECISION ->
    SERIES -> SEO BRIDGE -> MEMORY UPDATE.
    """

    def compile(
        self,
        db: Session | None,
        req: AutopilotBrainCompileRequest,
    ) -> AutopilotBrainCompileResponse:
        text = (req.script_text or req.topic or "").strip()
        if not text:
            raise ValueError("topic or script_text is required")

        score_bundle = self._score_runtime(text=text, platform=req.platform, audience=req.audience)
        scorecard = self._to_scorecard(score_bundle)
        memory_matches = self._recall_matches(db=db, text=text, niche=req.niche, platform=req.platform)
        series_map = self._build_series_map(text)
        seo_bridge = self._build_seo_bridge(req=req, scorecard=scorecard, series_map=series_map)

        runtime_memory_payload = {
            "brain_version": "custom-gpt-runtime-v1",
            "pipeline": [
                "INPUT",
                "SIGNAL",
                "DECISION",
                "SCRIPT_OR_SCENE",
                "CONTINUITY",
                "SEO_BRIDGE",
                "PUBLISH",
                "MEMORY_UPDATE",
            ],
            "decision": scorecard.decision,
            "classification": scorecard.classification,
            "continuity_rule": "no closure ending; every video must lead to the next episode",
            "distribution_rule": "prepare YouTube SEO package before provider upload",
            "series_anchor": [ep.model_dump() for ep in series_map],
            "memory_matches": [m.model_dump() for m in memory_matches],
        }

        if db is not None and req.store_if_winner and scorecard.total >= 90:
            self.store_winner_dna(
                db=db,
                source_text=text,
                niche=req.niche,
                platform=req.platform,
                seo_bridge=seo_bridge.model_dump(),
                runtime_memory_payload=runtime_memory_payload,
                scorecard=scorecard.model_dump(),
            )

        return AutopilotBrainCompileResponse(
            command_path="RUN_SIGNAL_TO_BREAKOUT_PLAN" if req.topic else "RUN_FULL_KOL_AUTOPILOT_STACK",
            scorecard=scorecard,
            memory_matches=memory_matches,
            series_map=series_map,
            seo_bridge=seo_bridge,
            runtime_memory_payload=runtime_memory_payload,
        )

    def store_winner_dna(
        self,
        db: Session,
        *,
        source_text: str,
        niche: str | None,
        platform: str,
        seo_bridge: dict[str, Any],
        runtime_memory_payload: dict[str, Any],
        scorecard: dict[str, Any],
    ) -> PatternMemory:
        row = PatternMemory(
            id=str(uuid.uuid4()),
            pattern_type="autopilot_brain_winner_dna",
            market_code=platform,
            content_goal=niche,
            source_id=None,
            score=float(scorecard.get("total", 0)),
            payload={
                "source_text": source_text,
                "scorecard": scorecard,
                "seo_bridge": seo_bridge,
                "runtime_memory_payload": runtime_memory_payload,
            },
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def _score_runtime(self, *, text: str, platform: str, audience: str | None) -> _ScoreBundle:
        lower = text.lower()
        words = re.findall(r"\w+", text)
        word_count = len(words)
        curiosity_terms = ["secret", "hidden", "truth", "why", "how", "inside", "nobody", "quietly", "wrong"]
        conflict_terms = ["vs", "while", "but", "instead", "replacing", "losing", "mistake", "war"]
        money_terms = ["money", "profit", "business", "income", "sell", "growth", "market"]
        trust_terms = ["proof", "system", "data", "case", "step", "framework"]

        attention = 9 + min(11, sum(1 for t in curiosity_terms if t in lower))
        if any(t in lower for t in conflict_terms):
            attention = min(20, attention + 3)

        retention = 8 + min(6, math.ceil(word_count / 80))
        if "while" in lower or "but" in lower:
            retention = min(20, retention + 3)
        if audience:
            retention = min(20, retention + 1)

        trust = 8 + min(5, sum(1 for t in trust_terms if t in lower))
        if any(x in lower for x in ["scam", "guaranteed", "overnight"]):
            trust = max(5, trust - 4)

        conversion = 7 + min(6, sum(1 for t in money_terms if t in lower))
        if platform.lower() in {"youtube", "shorts"}:
            conversion = min(20, conversion + 2)

        scaling = 8
        if any(k in lower for k in ["system", "series", "next", "part", "episode", "framework"]):
            scaling += 6
        if word_count > 30:
            scaling += 2
        scaling = min(20, scaling)

        return _ScoreBundle(
            attention=min(20, attention),
            retention=min(20, retention),
            trust=min(20, trust),
            conversion=min(20, conversion),
            scaling=min(20, scaling),
        )

    def _to_scorecard(self, bundle: _ScoreBundle) -> BrainScorecard:
        total = bundle.total
        for threshold, classification, decision in _RUNTIME_CLASSIFICATION:
            if total >= threshold:
                return BrainScorecard(
                    attention=bundle.attention,
                    retention=bundle.retention,
                    trust=bundle.trust,
                    conversion=bundle.conversion,
                    scaling=bundle.scaling,
                    total=total,
                    classification=classification,
                    decision=decision,
                )
        raise RuntimeError("unreachable classification state")

    def _recall_matches(
        self,
        *,
        db: Session | None,
        text: str,
        niche: str | None,
        platform: str,
        limit: int = 3,
    ) -> list[BrainMemoryMatch]:
        if db is None:
            return []

        rows = (
            db.query(PatternMemory)
            .filter(PatternMemory.pattern_type == "autopilot_brain_winner_dna")
            .order_by(PatternMemory.created_at.desc())
            .limit(20)
            .all()
        )
        target_tokens = set(re.findall(r"\w+", text.lower()))
        matches: list[BrainMemoryMatch] = []
        for row in rows:
            payload = row.payload or {}
            source_text = str(payload.get("source_text") or "")
            source_tokens = set(re.findall(r"\w+", source_text.lower()))
            if not source_tokens:
                continue
            overlap = len(target_tokens & source_tokens) / max(1, len(target_tokens | source_tokens))
            if niche and niche.lower() in source_text.lower():
                overlap += 0.08
            if platform.lower() in str(payload.get("runtime_memory_payload", {})).lower():
                overlap += 0.04
            if overlap < 0.10:
                continue
            matches.append(
                BrainMemoryMatch(
                    source_id=row.id,
                    score=round(min(0.99, overlap), 3),
                    summary=f"Winner DNA recalled from similar topic pattern: {source_text[:90]}",
                    payload=payload,
                )
            )
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:limit]

    def _build_series_map(self, text: str) -> list[BrainSeriesEpisode]:
        seed = self._short_title_seed(text)
        purposes = [
            ("strong hook", "Reveal the surface-level promise but keep the core mechanism hidden."),
            ("deepen topic", "Show the system behind the surface result and open a bigger question."),
            ("tension", "Expose the cost of doing it wrong and who is losing time or money."),
            ("reveal", "Reveal the missing operating model most viewers never build."),
            ("escalation", "Show how the method scales and what happens when the user turns it into a machine."),
        ]
        episodes = []
        for idx, (purpose, unresolved) in enumerate(purposes, start=1):
            episodes.append(
                BrainSeriesEpisode(
                    episode_index=idx,
                    working_title=f"{seed} — Part {idx}",
                    purpose=purpose,
                    unresolved_loop=unresolved,
                )
            )
        return episodes

    def _build_seo_bridge(
        self,
        *,
        req: AutopilotBrainCompileRequest,
        scorecard: BrainScorecard,
        series_map: list[BrainSeriesEpisode],
    ) -> SEOBridge:
        seed = self._short_title_seed(req.topic or req.script_text or "Untitled")
        title = seed if len(seed) <= 100 else seed[:97] + "..."
        next_titles = [ep.working_title for ep in series_map[1:4]]
        description = (
            f"{title}\n\n"
            f"This video breaks down the real operating model behind the topic, not surface-level prompting. "
            f"Score: {scorecard.total}/100 ({scorecard.classification}).\n\n"
            f"What you will uncover in this series:\n"
            f"- Why most people stay stuck at the tool level\n"
            f"- What system builders do differently\n"
            f"- Which hidden step creates repeatable output and growth\n\n"
            f"Keep going with the next chapters in this chain:\n"
            + "\n".join(f"- {t}" for t in next_titles)
            + "\n\n"
            + "There is still one hidden layer not fully revealed in this episode. Watch the next video in the chain to connect the missing part."
        )
        pinned_comment = (
            "Start here, then continue the series in order so the hidden system makes sense end-to-end. "
            + " → ".join([ep.working_title for ep in series_map[:3]])
            + "\nThe next episode reveals the part most viewers still miss."
        )
        video_hashtags = self._hashtags_from_text(req.topic or req.script_text or "video", prefix="#")[:5]
        channel_hashtags = ["#AIAutomation", "#BreakoutSystems", "#HiddenMechanics"]
        tags = [tag.lstrip("#") for tag in (video_hashtags + channel_hashtags)]
        thumbnail_brief = (
            "High contrast YouTube thumbnail. Left side = viewer making the common mistake. "
            "Right side = system/result/profit/dashboard payoff. One short accusatory phrase in 3-5 words."
        )
        return SEOBridge(
            title=title,
            thumbnail_brief=thumbnail_brief,
            description=description,
            pinned_comment=pinned_comment,
            video_hashtags=video_hashtags,
            channel_hashtags=channel_hashtags,
            tags=tags,
        )

    @staticmethod
    def _hashtags_from_text(text: str, prefix: str = "#") -> list[str]:
        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", text.title()) if len(t) > 2]
        seen: set[str] = set()
        out: list[str] = []
        for token in tokens:
            tag = prefix + token.replace(" ", "")
            if tag.lower() in seen:
                continue
            seen.add(tag.lower())
            out.append(tag)
            if len(out) >= 8:
                break
        return out

    @staticmethod
    def _short_title_seed(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        if len(cleaned) <= 86:
            return cleaned
        parts = cleaned.split()
        out = []
        for part in parts:
            out.append(part)
            if len(" ".join(out)) > 82:
                break
        return " ".join(out).strip()
