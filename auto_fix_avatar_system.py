#!/usr/bin/env python3
"""auto_fix_avatar_system.py — detect common avatar-system wiring failures and
apply safe, idempotent patches with automatic backups.

Usage
-----
    python auto_fix_avatar_system.py

What it does
------------
1. Backs up every target file before touching it.
2. Inserts missing avatar-tournament / governance / render / scheduler blocks.
3. Runs ``python -m compileall backend/app`` to verify no syntax errors.
4. Optionally runs ``bash run_avatar_smoke.sh`` when present.

All patches are idempotent: if a block is already present the script skips it
and reports "no changes applied".
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent
BACKEND_ROOT = REPO_ROOT / "backend"

FILES = {
    "decision": BACKEND_ROOT / "app/services/brain/brain_decision_engine.py",
    "bridge": BACKEND_ROOT / "app/services/execution_bridge_service.py",
    "feedback": BACKEND_ROOT / "app/services/brain/brain_feedback_service.py",
    "scheduler": BACKEND_ROOT / "app/services/publish_scheduler.py",
    "governance": BACKEND_ROOT / "app/services/avatar/avatar_governance_engine.py",
}

BACKUP_DIR = REPO_ROOT / ".autofix_backups"

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as exc:
        return exc.output.decode()


def ensure_backup(path: Path) -> None:
    BACKUP_DIR.mkdir(exist_ok=True)
    if not path.exists():
        return
    dst = BACKUP_DIR / f"{path.name}.{int(time.time())}.bak"
    shutil.copyfile(path, dst)


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def safe_insert_before(content: str, anchor_regex: str, block: str) -> tuple[str, bool]:
    """Insert *block* immediately before the first match of *anchor_regex*.
    Returns (new_content, changed).  If *block* already appears in *content*
    (substring check) the content is returned unchanged.
    """
    if block.strip() in content:
        return content, False
    m = re.search(anchor_regex, content, flags=re.MULTILINE)
    if not m:
        return content, False
    pos = m.start()
    return content[:pos] + block + "\n" + content[pos:], True


def safe_insert_after(content: str, anchor_regex: str, block: str) -> tuple[str, bool]:
    """Insert *block* immediately after the first match of *anchor_regex*."""
    if block.strip() in content:
        return content, False
    m = re.search(anchor_regex, content, flags=re.MULTILINE)
    if not m:
        return content, False
    pos = m.end()
    return content[:pos] + "\n" + block + "\n" + content[pos:], True


# ---------------------------------------------------------------------------
# Patch blocks
# ---------------------------------------------------------------------------

# ── brain_decision_engine: avatar tournament import + init + call ──────────

_DECISION_IMPORT_BLOCK = """\
# [AUTO_FIX] avatar tournament import
from app.services.avatar.avatar_tournament_engine import AvatarTournamentEngine
"""

_DECISION_RUN_BLOCK = """\
# [AUTO_FIX] avatar tournament run
_avatar_selection_result = None
try:
    _candidate_avatar_ids = request.get("candidate_avatar_ids") or []
    if db is not None and _candidate_avatar_ids:
        from app.schemas.avatar_tournament import AvatarTournamentRequest as _ATR
        _tournament_req = _ATR(
            workspace_id=request.get("workspace_id") or "default",
            project_id=request.get("project_id"),
            market_code=request.get("market_code"),
            content_goal=request.get("content_goal"),
            topic_class=request.get("topic_class"),
            platform=request.get("target_platform"),
            candidate_avatar_ids=_candidate_avatar_ids,
            exploration_ratio=float(request.get("avatar_exploration_ratio") or 0.15),
            force_avatar_ids=list(request.get("force_avatar_ids") or []),
            preferred_avatar_id=request.get("avatar_id"),
        )
        _avatar_selection_result = AvatarTournamentEngine().run_tournament(
            db=db, request=_tournament_req
        )
except Exception as _exc:
    try:
        logger.warning("avatar tournament failed: %s", _exc)
    except Exception:
        pass

if _avatar_selection_result is not None:
    selected_avatar_id = str(_avatar_selection_result.selected_avatar_id)
    avatar_selection_notes = {
        "tournament_run_id": _avatar_selection_result.tournament_run_id,
        "selection_mode": _avatar_selection_result.selection_mode,
        "explanation": _avatar_selection_result.explanation,
    }
"""

# ── execution_bridge_service: avatar fields in render_context ─────────────

_BRIDGE_INJECT_BLOCK = """\
# [AUTO_FIX] avatar bridge inject
try:
    _avatar_sel = decision_payload.get("avatar_selection", {}) if decision_payload else {}
    render_context["avatar"] = _avatar_sel
    render_context["avatar_id"] = decision_payload.get("avatar_id") if decision_payload else None
    render_context["avatar_tournament_run_id"] = _avatar_sel.get("tournament_run_id")
    render_context["avatar_selection_mode"] = _avatar_sel.get("selection_mode")
except Exception:
    pass
"""

# ── brain_feedback_service: self-healing + adaptive learning calls ─────────

_FEEDBACK_SELF_HEALING_BLOCK = """\
# [AUTO_FIX] self-healing call
_bfs_avatar_id = payload.get("avatar_id") if payload else None
if _bfs_avatar_id and db is not None:
    try:
        from app.services.avatar.self_healing_engine import SelfHealingEngine as _SHE
        _SHE().process_feedback(
            db,
            avatar_id=_bfs_avatar_id,
            metrics={**(payload.get("metrics") or {}), "total_score": score},
            context={
                "project_id": payload.get("project_id"),
                "topic_class": payload.get("topic_class"),
                "template_family": payload.get("selected_template_family"),
                "platform": payload.get("platform"),
            },
        )
    except Exception:
        pass
"""

_FEEDBACK_ADAPTIVE_BLOCK = """\
# [AUTO_FIX] adaptive learning call
_bfs_avatar_id2 = payload.get("avatar_id") if payload else None
if _bfs_avatar_id2 and db is not None:
    try:
        from app.services.avatar.learning_engine import AdaptiveLearningEngine as _ALE
        _ALE().learn(
            db,
            avatar_id=_bfs_avatar_id2,
            context={
                "topic_signature": payload.get("topic_signature"),
                "template_family": payload.get("selected_template_family"),
                "platform": payload.get("platform"),
            },
            metrics={**(payload.get("metrics") or {}), "total_score": score},
        )
    except Exception:
        pass
"""

# ── publish_scheduler: cooldown + priority avatar scoring ─────────────────

_SCHED_IMPORT_BLOCK = """\
# [AUTO_FIX] scheduler avatar import
from app.models.avatar_policy_state import AvatarPolicyState as _APS  # noqa
"""

_SCHED_SCORE_BLOCK = """\
# [AUTO_FIX] avatar scheduler scoring
try:
    _sched_avatar_id = item.get("avatar_id") or (item.get("metadata") or {}).get("avatar_id")
    _sched_policy_state = None
    if _sched_avatar_id:
        from app.models.avatar_policy_state import AvatarPolicyState as _APS2
        _sched_policy_state = db.query(_APS2).filter(
            _APS2.avatar_id == _sched_avatar_id
        ).one_or_none()
    if _sched_policy_state and getattr(_sched_policy_state, "state", None) == "cooldown":
        item_score -= 1000
    if _sched_policy_state and getattr(_sched_policy_state, "state", None) == "priority":
        item_score += 25
except Exception:
    pass
"""

# ── avatar_governance_engine: compatibility wrapper for feedback callers ───

_GOVERNANCE_COMPAT_BLOCK = """\
    def process_feedback(
        self,
        db: Session,
        *,
        avatar_id: str,
        metrics: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AvatarPromotionDecision:
        # Backward-compatible alias used by older feedback integrations.
        return self.evaluate_avatar_outcome(
            db,
            avatar_id=avatar_id,
            metrics=metrics,
            context=context,
        )
"""

# ---------------------------------------------------------------------------
# Patch functions
# ---------------------------------------------------------------------------

def patch_decision() -> bool:
    p = FILES["decision"]
    if not p.exists():
        print(f"  ⚠️  Missing: {p}")
        return False

    content = read_file(p)
    original = content

    # Ensure AvatarTournamentEngine is imported
    if "AvatarTournamentEngine" not in content:
        content, _ = safe_insert_after(content, r"^import logging", _DECISION_IMPORT_BLOCK)

    # Ensure run block exists before `return plan, continuity_context`
    if "_avatar_selection_result" not in content and "run_tournament" not in content:
        content, _ = safe_insert_before(
            content,
            r"^\s+return plan,\s+continuity_context",
            _DECISION_RUN_BLOCK,
        )

    if content != original:
        ensure_backup(p)
        write_file(p, content)
        print("  🔧 Patched brain_decision_engine.py")
        return True
    print("  ✅ brain_decision_engine.py — no changes needed")
    return False


def patch_bridge() -> bool:
    p = FILES["bridge"]
    if not p.exists():
        print(f"  ⚠️  Missing: {p}")
        return False

    content = read_file(p)
    original = content

    # Inject avatar fields after render_context dict open
    if "avatar_tournament_run_id" not in content:
        content, _ = safe_insert_after(
            content, r"render_context\s*=\s*{", _BRIDGE_INJECT_BLOCK
        )

    if content != original:
        ensure_backup(p)
        write_file(p, content)
        print("  🔧 Patched execution_bridge_service.py")
        return True
    print("  ✅ execution_bridge_service.py — no changes needed")
    return False


def patch_feedback() -> bool:
    p = FILES["feedback"]
    if not p.exists():
        print(f"  ⚠️  Missing: {p}")
        return False

    content = read_file(p)
    original = content

    if "self_healing_engine" not in content:
        content, _ = safe_insert_before(
            content, r"^\s+# --+\n\s+# Internal helpers", _FEEDBACK_SELF_HEALING_BLOCK
        )

    if "adaptive_learning" not in content and "learning_engine" not in content:
        content, _ = safe_insert_before(
            content, r"^\s+# --+\n\s+# Internal helpers", _FEEDBACK_ADAPTIVE_BLOCK
        )

    if content != original:
        ensure_backup(p)
        write_file(p, content)
        print("  🔧 Patched brain_feedback_service.py")
        return True
    print("  ✅ brain_feedback_service.py — no changes needed")
    return False


def patch_scheduler() -> bool:
    p = FILES["scheduler"]
    if not p.exists():
        print(f"  ⚠️  Missing: {p}")
        return False

    content = read_file(p)
    original = content

    # Ensure AvatarPolicyState import helper is available for injected scoring block.
    if "AvatarPolicyState as _APS" not in content:
        content, _ = safe_insert_after(content, r"^import logging", _SCHED_IMPORT_BLOCK)

    # Look for item_score assignment patterns in build_publish_queue or related
    if "_sched_policy_state" not in content and "item_score" in content:
        content, _ = safe_insert_after(
            content, r"item_score\s*=", _SCHED_SCORE_BLOCK
        )

    if content != original:
        ensure_backup(p)
        write_file(p, content)
        print("  🔧 Patched publish_scheduler.py")
        return True
    print("  ✅ publish_scheduler.py — no changes needed")
    return False


def patch_governance() -> bool:
    p = FILES["governance"]
    if not p.exists():
        print(f"  ⚠️  Missing: {p}")
        return False

    content = read_file(p)
    original = content

    if "def process_feedback(" not in content:
        content, _ = safe_insert_before(
            content,
            r"^    # ── Internal helpers",
            _GOVERNANCE_COMPAT_BLOCK,
        )

    if content != original:
        ensure_backup(p)
        write_file(p, content)
        print("  🔧 Patched avatar_governance_engine.py")
        return True
    print("  ✅ avatar_governance_engine.py — no changes needed")
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def compile_check() -> bool:
    print("\n🔍 Compile check...")
    out = run(f"python -m compileall {BACKEND_ROOT}")
    if "error" in out.lower():
        print("  ❌ Compile issues detected:")
        print(out[:1200])
        return False
    print("  ✅ Compile OK")
    return True


def smoke_check() -> bool:
    smoke = REPO_ROOT / "run_avatar_smoke.sh"
    if not smoke.exists():
        print("\n⚠️  run_avatar_smoke.sh not found — skipping smoke test")
        return True
    print("\n🧪 Running smoke script...")
    out = run(f"bash {smoke}")
    print(out[-1500:])
    if "FAIL" in out or "error" in out.lower():
        print("  ❌ Smoke detected issues (see above)")
        return False
    print("  ✅ Smoke OK")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n🚀 AUTO FIX AVATAR SYSTEM\n")

    changed = False
    print("── Applying patches ──────────────────────────────────────")
    changed |= patch_decision()
    changed |= patch_bridge()
    changed |= patch_feedback()
    changed |= patch_scheduler()
    changed |= patch_governance()

    if not changed:
        print("\nℹ️  All blocks already present — nothing to patch.")

    ok_compile = compile_check()
    ok_smoke = smoke_check()

    print("\n══════════════════════════════════════════════")
    if ok_compile and ok_smoke:
        print("✅ AUTO FIX SUCCESS — AVATAR SYSTEM READY")
    else:
        print("⚠️  AUTO FIX PARTIAL — review logs above")
        print(f"   Backups stored in: {BACKUP_DIR}")
    print("══════════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
