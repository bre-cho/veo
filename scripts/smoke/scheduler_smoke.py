#!/usr/bin/env python3
"""
scheduler_smoke.py — local smoke test for avatar cooldown/priority scheduling behavior.

Does NOT require a running server or DB connection.
Simulates the _avatar_is_publishable() guard and priority/cooldown scoring
that publish_scheduler applies when ranking queue items.

Expected result:
  job-a (priority avatar) wins even though its raw score (80) is lower than job-b (95).
  job-b is on cooldown and gets a -1000 penalty, dropping it to the bottom.
  job-c (candidate) gets a small +5 boost but still loses to job-a.

Run:
  python scripts/smoke/scheduler_smoke.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Simulated queue items
# ---------------------------------------------------------------------------
ITEMS: list[dict] = [
    {"job_id": "job-a", "score": 80,  "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"},
    {"job_id": "job-b", "score": 95,  "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"},
    {"job_id": "job-c", "score": 78,  "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"},
]

# ---------------------------------------------------------------------------
# Simulated AvatarPolicyState rows
# (mirrors what publish_scheduler queries from DB)
# ---------------------------------------------------------------------------
POLICY: dict[str, dict] = {
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1": {
        "state": "priority",
        "priority_weight": 1.0,
        "cooldown_until": None,
    },
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2": {
        "state": "cooldown",
        "priority_weight": 0.0,
        "cooldown_until": datetime.utcnow() + timedelta(days=2),
    },
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3": {
        "state": "candidate",
        "priority_weight": 0.2,
        "cooldown_until": None,
    },
}

# Score adjustments — must match publish_scheduler constants
PRIORITY_BONUS = 25
CANDIDATE_BONUS = 5
COOLDOWN_PENALTY = 1000
BLOCKED_STATES = {"blocked", "retired"}


def avatar_is_publishable(policy: dict | None) -> bool:
    """Mirror of publish_scheduler._avatar_is_publishable()."""
    if not policy:
        return True
    if policy["state"] in BLOCKED_STATES:
        return False
    if policy["state"] == "cooldown" and policy["cooldown_until"]:
        return policy["cooldown_until"] <= datetime.utcnow()
    return True


def rank_items(items: list[dict]) -> list[dict]:
    ranked = []
    for item in items:
        avatar_id = item["avatar_id"]
        policy = POLICY.get(avatar_id)
        score = item["score"]

        if not avatar_is_publishable(policy):
            score -= COOLDOWN_PENALTY
        elif policy:
            if policy["state"] == "priority":
                score += PRIORITY_BONUS
            elif policy["state"] == "candidate":
                score += CANDIDATE_BONUS

        ranked.append({**item, "final_score": score, "policy_state": policy["state"] if policy else "none"})

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked


def main() -> int:
    print("=" * 60)
    print("AVATAR SCHEDULER SMOKE TEST")
    print("=" * 60)

    ranked = rank_items(ITEMS)

    print("\nRanked items:")
    for i, item in enumerate(ranked):
        marker = "  <-- WINNER" if i == 0 else ""
        print(
            f"  [{i + 1}] job={item['job_id']}  avatar={item['avatar_id'][-3:]}  "
            f"raw={item['score']}  final={item['final_score']}  "
            f"state={item['policy_state']}{marker}"
        )

    winner = ranked[0]
    avatar_suffix = winner["avatar_id"][-3:]
    print(f"\nSelected: {winner['job_id']} / avatar ...{avatar_suffix}")

    # ---------------------------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------------------------
    errors: list[str] = []

    if winner["job_id"] != "job-a":
        errors.append(
            f"FAIL: expected job-a to win (priority avatar), got {winner['job_id']}"
        )

    cooldown_item = next(x for x in ranked if x["job_id"] == "job-b")
    if cooldown_item["final_score"] >= 0:
        errors.append(
            f"FAIL: cooldown avatar should have negative score, got {cooldown_item['final_score']}"
        )

    priority_item = next(x for x in ranked if x["job_id"] == "job-a")
    if priority_item["final_score"] != 80 + PRIORITY_BONUS:
        errors.append(
            f"FAIL: priority avatar score should be {80 + PRIORITY_BONUS}, got {priority_item['final_score']}"
        )

    if errors:
        print("\n" + "\n".join(errors))
        print("\nResult: NO-GO scheduler smoke")
        return 1

    print("\nResult: GO scheduler smoke ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
