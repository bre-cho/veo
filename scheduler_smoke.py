#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta
from pprint import pprint

items = [
    {
        "job_id": "job-a",
        "score": 80,
        "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        "decision": {"avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"},
    },
    {
        "job_id": "job-b",
        "score": 95,
        "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        "decision": {"avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"},
    },
    {
        "job_id": "job-c",
        "score": 78,
        "avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
        "decision": {"avatar_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"},
    },
]

policy = {
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1": {"state": "priority", "cooldown_until": None},
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2": {"state": "cooldown", "cooldown_until": datetime.utcnow() + timedelta(days=2)},
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3": {"state": "candidate", "cooldown_until": None},
}


def avatar_is_publishable(state: dict | None) -> bool:
    if not state:
        return True
    if state["state"] in {"blocked", "retired"}:
        return False
    if state["state"] == "cooldown" and state["cooldown_until"]:
        return state["cooldown_until"] <= datetime.utcnow()
    return True


def score_item(item: dict) -> dict:
    avatar_state = policy.get(item["avatar_id"])
    final_score = item["score"]

    if not avatar_is_publishable(avatar_state):
        final_score -= 1000
    if avatar_state and avatar_state["state"] == "priority":
        final_score += 25
    if avatar_state and avatar_state["state"] == "candidate":
        final_score += 5

    return {
        **item,
        "policy_state": avatar_state["state"] if avatar_state else None,
        "final_score": final_score,
    }


scored = [score_item(item) for item in items]
ranked = sorted(scored, key=lambda x: x["final_score"], reverse=True)
selected = ranked[0]

print("=== SCHEDULER SMOKE RESULT ===")
pprint(ranked)
print("\nselected_job:", selected["job_id"])
print("selected_avatar:", selected["avatar_id"])
print("selected_score:", selected["final_score"])

if selected["job_id"] != "job-a":
    raise SystemExit("FAIL: expected job-a to win because job-b is cooldown and job-a is priority")

print("\nPASS: scheduler correctly avoided cooldown avatar and boosted priority avatar")
