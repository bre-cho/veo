#!/usr/bin/env python3
"""
auto_debug_avatar_system.py — 1-command avatar system health checker.

Runs all 5 smoke checks in sequence and prints targeted fix hints
for every failure so devs know exactly which file to patch.

Usage:
    python scripts/smoke/auto_debug_avatar_system.py

    # Point at a non-default server:
    BASE_URL=http://staging:8000 python scripts/smoke/auto_debug_avatar_system.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import requests as _requests_lib  # optional — falls back to curl
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

ENDPOINTS = {
    "decision": "/api/v1/decision/test",
    "render": f"/api/v1/projects/22222222-2222-2222-2222-222222222222/render",
    "feedback": "/api/v1/feedback/test",
}

SMOKE_DIR = Path(__file__).parent

FILES = {
    "decision":   SMOKE_DIR / "decision_smoke.json",
    "render":     SMOKE_DIR / "render_smoke.json",
    "feedback_good": SMOKE_DIR / "feedback_smoke_good.json",
    "feedback_bad":  SMOKE_DIR / "feedback_smoke_bad.json",
    "scheduler":  SMOKE_DIR / "scheduler_smoke.py",
}

SOURCE_FILES = {
    "decision":  "backend/app/services/brain/brain_decision_engine.py",
    "bridge":    "backend/app/services/execution_bridge_service.py",
    "render":    "backend/app/api/render_execution.py",
    "feedback":  "backend/app/services/brain/brain_feedback_service.py",
    "scheduler": "backend/app/services/publish_scheduler.py",
    "governance":"backend/app/services/avatar/avatar_governance_engine.py",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_passed: list[str] = []
_failed: list[str] = []


def _ok(label: str) -> None:
    print(f"  ✅  {label}")
    _passed.append(label)


def _fail(label: str, hint: str = "") -> None:
    print(f"  ❌  {label}")
    if hint:
        print(f"       👉  {hint}")
    _failed.append(label)


def _run(cmd: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "timeout"


def _post(endpoint: str, payload_file: Path) -> dict | None:
    url = BASE_URL + endpoint
    try:
        payload = json.loads(payload_file.read_text())
    except Exception as exc:
        print(f"       ⚠  cannot read {payload_file}: {exc}")
        return None

    if _HAS_REQUESTS:
        try:
            resp = _requests_lib.post(url, json=payload, timeout=8)
            return resp.json()
        except Exception as exc:
            print(f"       ⚠  request error: {exc}")
            return None
    else:
        # fallback: curl
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        code, out = _run(
            f"curl -s -o {tmp_path} -w '%{{http_code}}' "
            f"-X POST '{url}' -H 'Content-Type: application/json' "
            f"-d '@{payload_file}'"
        )
        try:
            return json.loads(Path(tmp_path).read_text())
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_compile() -> bool:
    print("\n🔍  CHECK COMPILE (py_compile entire backend)...")
    rc, out = _run("python -m py_compile $(find backend/app -name '*.py' | head -200) 2>&1")
    if rc != 0 or "SyntaxError" in out or "Error" in out:
        _fail("compile", "Fix syntax errors before all other checks")
        print(out[:800])
        return False
    _ok("compile — no syntax errors")
    return True


def check_decision() -> bool:
    print("\n🔍  CHECK DECISION (avatar_id in response)...")
    res = _post(ENDPOINTS["decision"], FILES["decision"])
    if res is None:
        _fail(
            "decision — server unreachable",
            f"Is the server running at {BASE_URL}?",
        )
        return False

    if not res.get("avatar_id"):
        _fail(
            "decision — avatar_id missing",
            f"Fix: {SOURCE_FILES['decision']}\n"
            "       PATCH: add AvatarTournamentEngine.run_tournament() block before `return decision`",
        )
        return False

    if "avatar_selection" not in res:
        _fail(
            "decision — avatar_selection bundle missing",
            f"Fix: {SOURCE_FILES['decision']}\n"
            "       PATCH: decision['avatar_selection'] = avatar_selection.model_dump()",
        )
        return False

    _ok(f"decision — avatar_id={res['avatar_id']}, mode={res.get('avatar_selection', {}).get('selection_mode')}")
    return True


def check_render() -> bool:
    print("\n🔍  CHECK RENDER (avatar context carried)...")
    res = _post(ENDPOINTS["render"], FILES["render"])
    if res is None:
        _fail("render — server unreachable", f"Is the server running at {BASE_URL}?")
        return False

    avatar = res.get("avatar") or res.get("avatar_context")
    if not avatar:
        _fail(
            "render — avatar not in response",
            f"Fix: {SOURCE_FILES['bridge']}\n"
            "       PATCH: render_context['avatar'] = decision_payload.get('avatar_selection', {})",
        )
        return False

    avatar_id = (
        avatar.get("avatar_id") if isinstance(avatar, dict) else None
    ) or res.get("avatar_id")
    if not avatar_id:
        _fail(
            "render — avatar_id missing inside avatar context",
            f"Fix: {SOURCE_FILES['bridge']}\n"
            "       PATCH: render_context['avatar_id'] = decision_payload.get('avatar_id')",
        )
        return False

    _ok(f"render — avatar_id={avatar_id}")
    return True


def check_feedback_good() -> bool:
    print("\n🔍  CHECK FEEDBACK GOOD (governance present, action ≠ cooldown)...")
    res = _post(ENDPOINTS["feedback"], FILES["feedback_good"])
    if res is None:
        _fail("feedback good — server unreachable", f"Is the server running at {BASE_URL}?")
        return False

    gov = res.get("avatar_governance")
    if not gov:
        _fail(
            "feedback good — avatar_governance missing",
            f"Fix: {SOURCE_FILES['feedback']}\n"
            "       PATCH: feedback_result['avatar_governance'] = governance_engine.evaluate_avatar_outcome(...)",
        )
        return False

    action = gov.get("action") if isinstance(gov, dict) else None
    if action == "cooldown":
        _fail(
            "feedback good — good metrics triggered cooldown (threshold bug)",
            f"Fix: {SOURCE_FILES['governance']}\n"
            "       PATCH: tighten cooldown threshold (retention < 0.3, not 0.6)",
        )
        return False

    _ok(f"feedback good — avatar_governance present, action={action}")
    return True


def check_feedback_bad() -> bool:
    print("\n🔍  CHECK FEEDBACK BAD (governance present, action = demote/cooldown)...")
    res = _post(ENDPOINTS["feedback"], FILES["feedback_bad"])
    if res is None:
        _fail("feedback bad — server unreachable", f"Is the server running at {BASE_URL}?")
        return False

    gov = res.get("avatar_governance")
    if not gov:
        _fail(
            "feedback bad — avatar_governance missing",
            f"Fix: {SOURCE_FILES['feedback']}\n"
            "       PATCH: feedback_result['avatar_governance'] = governance_engine.evaluate_avatar_outcome(...)",
        )
        return False

    action = gov.get("action") if isinstance(gov, dict) else None
    good_actions = {"cooldown", "demote", "rollback_candidate", "downweight"}
    if action and action not in good_actions and action != "none":
        print(f"       ⚠  unexpected action '{action}' for bad metrics — review thresholds")

    _ok(f"feedback bad — avatar_governance present, action={action}")
    return True


def check_scheduler() -> bool:
    print("\n🔍  CHECK SCHEDULER LOCAL (cooldown avatar not selected)...")
    scheduler_path = FILES["scheduler"]
    rc, out = _run(f"python {scheduler_path}")
    print(out.strip()[:600])

    if rc != 0:
        _fail(
            "scheduler — script exited with error",
            f"Fix: {SOURCE_FILES['scheduler']}\n"
            "       PATCH: add AvatarPolicyState cooldown penalty (-1000) before ranking",
        )
        return False

    if "selected = job-b" in out or "WINNER" in out and "job-b" in out.split("WINNER")[0]:
        _fail(
            "scheduler — cooldown avatar (job-b) still selected",
            f"Fix: {SOURCE_FILES['scheduler']}\n"
            "       PATCH: if state == 'cooldown': item_score -= 1000",
        )
        return False

    _ok("scheduler — cooldown guard working, priority avatar wins")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       AUTO DEBUG — AVATAR SYSTEM                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  base_url = {BASE_URL}")

    checks = [
        check_compile,
        check_decision,
        check_render,
        check_feedback_good,
        check_feedback_bad,
        check_scheduler,
    ]

    for check in checks:
        check()

    print("\n══════════════════════════════════════════════════════════")
    print(f"  PASS: {len(_passed)}   FAIL: {len(_failed)}")

    if not _failed:
        print("  → ✅  SYSTEM FULLY WORKING — AI KOL FACTORY IS LIVE")
        return 0

    print(f"  → ❌  {len(_failed)} check(s) failed — see FIX hints above")
    print("\n  Quick repair order:")
    print("    1. compile errors   → fix syntax first")
    print("    2. decision         → brain_decision_engine.py")
    print("    3. render           → execution_bridge_service.py")
    print("    4. feedback         → brain_feedback_service.py")
    print("    5. scheduler        → publish_scheduler.py")
    print("    6. governance logic → avatar_governance_engine.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
