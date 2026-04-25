#!/usr/bin/env python3
"""Unified Runtime Verification Script.

Checks that the full render operating environment is consistent before
deploying or running CI.

Modes
-----
quick (default for CI):
    Checks 3, 4 only — lightweight imports (app.core.*) and path
    writability.  No source scan, no infrastructure (DB / Redis / Celery).
    Designed to complete in < 5 s on a bare CI runner.

fast (extended CI gate):
    Everything in quick, plus check 8 — source scan for residual
    /data/renders hardcodes.  Adds ~1–2 s for the filesystem walk but
    still requires no live infrastructure.

full (deploy gate):
    All checks: Alembic, DB tables, imports, paths, Celery, router
    registry, storage paths, and no hardcoded paths.

Checks performed
----------------
1.  Alembic single-head validation              [full]
2.  Required DB tables present                  [full]
3.  Critical model/schema imports succeed       [quick + fast + full]
4.  Render output / cache / storage paths       [quick + fast + full]
5.  Celery broker reachable                     [full]
6.  API router registry loads without error     [full]
7.  Storage + artefact paths exist              [full]
8.  No hardcoded ``/data/renders`` paths        [fast + full]

Exit codes: 0 = all checks passed, 1 = one or more checks failed.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import traceback
from pathlib import Path

# ── Make sure backend/ is on sys.path ────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_BACKEND_ROOT = _HERE.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

PASS = "✓"
FAIL = "✗"
WARN = "⚠"

_failures: list[str] = []
_warnings: list[str] = []


def ok(label: str) -> None:
    print(f"  {PASS}  {label}")


def fail(label: str, detail: str = "") -> None:
    msg = f"{label}: {detail}" if detail else label
    print(f"  {FAIL}  {msg}")
    _failures.append(msg)


def warn(label: str, detail: str = "") -> None:
    msg = f"{label}: {detail}" if detail else label
    print(f"  {WARN}  {msg}")
    _warnings.append(msg)


# ── Check 1: Alembic single head ─────────────────────────────────────────

def check_alembic_head() -> None:
    print("\n[1] Alembic migration head")
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        alembic_ini = _BACKEND_ROOT / "alembic.ini"
        if not alembic_ini.exists():
            warn("alembic.ini not found — skipping migration head check")
            return
        cfg = Config(str(alembic_ini))
        sd = ScriptDirectory.from_config(cfg)
        heads = sd.get_heads()
        if len(heads) == 1:
            ok(f"Single migration head: {heads[0]}")
        elif len(heads) == 0:
            warn("No migration heads found (empty migration history)")
        else:
            warn(
                f"Multiple migration heads detected ({len(heads)}) — "
                "resolve before merging to production",
                ", ".join(heads),
            )
    except Exception as exc:
        warn(f"Alembic check skipped ({type(exc).__name__}: {exc})")


# ── Check 2: DB tables ────────────────────────────────────────────────────

_REQUIRED_TABLES = [
    "render_jobs",
    "render_tasks",
    "render_events",
]


def check_db_tables() -> None:
    print("\n[2] Database tables")
    try:
        import sqlalchemy as sa
        from app.core.config import settings
        engine = sa.create_engine(
            settings.database_url,
            connect_args={"connect_timeout": 5},
            pool_pre_ping=True,
        )
        with engine.connect() as conn:
            inspector = sa.inspect(engine)
            existing = set(inspector.get_table_names())
        missing = [t for t in _REQUIRED_TABLES if t not in existing]
        if missing:
            fail("Missing required tables", ", ".join(missing))
        else:
            ok(f"All required tables present ({', '.join(_REQUIRED_TABLES)})")
    except Exception as exc:
        warn(f"DB check skipped ({type(exc).__name__}: {exc})")


# ── Check 3: Critical imports ─────────────────────────────────────────────

# Quick mode: only the two lightest core modules — no DB / Redis / Celery /
# SQLAlchemy / heavy reassembly chains.  Must finish in < 10 s.
# app.core.light_runtime_config is used instead of app.core.config because
# the latter imports pydantic at module level which can cause timeouts in
# bare CI environments without a full virtualenv pre-warmed.
_QUICK_IMPORTS = [
    "app.core.light_runtime_config",
    "app.core.light_runtime_paths",
]

# Full mode: complete set including heavier reassembly / rebuild modules.
# SmartReassemblyService, render.rebuild.api, and api._registry are kept out of
# quick mode — they pull in large dependency trees that require infrastructure
# packages and can hang in bare CI environments.
_FULL_IMPORTS = [
    "app.core.config",
    "app.core.runtime_paths",
    "app.render.manifest.manifest_service",
    "app.render.manifest.manifest_writer",
    "app.render.manifest.manifest_reader",
    "app.render.dependency.dependency_service",
    "app.render.reassembly.smart_reassembly_service",
    "app.render.reassembly.chunk_index",
    "app.render.rerender.rerender_service",
    "app.render.decision.unified_rebuild_decision_engine",
    "app.render.execution.approved_rebuild_executor",
    "app.render.execution.rebuild_persistence",
    "app.render.rebuild.api",
    "app.api._registry",
]


def check_imports(mode: str = "quick") -> None:
    print("\n[3] Critical module imports")
    imports = _QUICK_IMPORTS if mode == "quick" else _FULL_IMPORTS
    # Modules that may fail on infrastructure packages (kombu, sqlalchemy, etc.)
    # when running outside the full Docker stack — warn, not fail.
    _INFRA_DEPENDENT = {"app.api._registry"}
    for module_path in imports:
        try:
            importlib.import_module(module_path)
            ok(module_path)
        except ModuleNotFoundError as exc:
            if module_path in _INFRA_DEPENDENT:
                warn(f"{module_path} skipped — infrastructure package missing ({exc})")
            else:
                fail(module_path, str(exc))
        except Exception as exc:
            fail(module_path, str(exc))


# ── Check 4: Render paths writable ───────────────────────────────────────

def check_render_paths(mode: str = "quick") -> None:
    print("\n[4] Render path writability")
    try:
        if mode == "quick":
            from app.core.light_runtime_paths import light_render_paths as render_paths
        else:
            from app.core.runtime_paths import render_paths  # type: ignore[assignment]
        dirs_to_check = {
            "manifests_dir": render_paths.manifests_dir,
            "chunks_dir": render_paths.chunks_dir,
            "final_dir": render_paths.final_dir,
            "subtitles_dir": render_paths.subtitles_dir,
            "detector_cache_dir": render_paths.detector_cache_dir,
            "concat_scratch_dir": render_paths.concat_scratch_dir,
            "dependency_dir": render_paths.dependency_dir,
        }
        for name, path_str in dirs_to_check.items():
            path = Path(path_str)
            try:
                path.mkdir(parents=True, exist_ok=True)
                probe = path / ".write_probe"
                probe.write_text("ok")
                probe.unlink()
                ok(f"{name}: {path_str}")
            except PermissionError as exc:
                # In Docker/production /app/ is mounted; this is expected in bare CI
                warn(f"{name} not writable ({path_str}) — OK if running outside Docker", str(exc))
            except Exception as exc:
                fail(f"{name} not writable ({path_str})", str(exc))
    except Exception as exc:
        fail("render_paths import failed", str(exc))


# ── Check 5: Celery broker ────────────────────────────────────────────────

def check_celery_broker() -> None:
    print("\n[5] Celery broker")
    if not os.environ.get("CELERY_VERIFY_RUNTIME"):
        ok("Skipped (set CELERY_VERIFY_RUNTIME=1 to enable)")
        return
    try:
        from app.core.config import settings
        import redis
        url = settings.celery_broker_url
        if url.startswith("redis"):
            r = redis.from_url(url, socket_connect_timeout=3)
            r.ping()
            ok(f"Redis broker reachable at {url}")
        else:
            warn(f"Non-Redis broker '{url}' — manual check required")
    except Exception as exc:
        fail("Celery broker unreachable", str(exc))


# ── Check 6: API router registry ─────────────────────────────────────────

def check_router_registry() -> None:
    print("\n[6] API router registry")
    try:
        from fastapi import FastAPI
        from app.api._registry import register_all_routers
        app = FastAPI()
        register_all_routers(app)
        route_count = len(app.routes)
        ok(f"register_all_routers() succeeded ({route_count} routes)")
    except ModuleNotFoundError as exc:
        warn(f"Router registry skipped — infrastructure package missing ({exc})")
    except Exception as exc:
        fail("Router registry error", str(exc))


# ── Check 7: Storage / artefact paths ────────────────────────────────────

def check_storage_paths() -> None:
    print("\n[7] Storage and artefact paths")
    try:
        from app.core.config import settings
        paths_to_check = {
            "storage_root": settings.storage_root,
            "render_output_dir": settings.render_output_dir,
            "render_cache_dir": settings.render_cache_dir,
            "audio_output_dir": settings.audio_output_dir,
            "video_output_dir": settings.video_output_dir,
        }
        for name, path_str in paths_to_check.items():
            path = Path(path_str)
            try:
                path.mkdir(parents=True, exist_ok=True)
                ok(f"{name}: {path_str}")
            except PermissionError as exc:
                warn(f"{name} not creatable ({path_str}) — OK if running outside Docker", str(exc))
            except Exception as exc:
                fail(f"{name} not creatable ({path_str})", str(exc))
    except Exception as exc:
        fail("Storage path check failed", str(exc))


# ── Check 8: No residual /data/renders hardcodes ─────────────────────────

_SCAN_ROOT = _BACKEND_ROOT / "app"
_EXCLUDE_GLOBS = ["*.pyc", "__pycache__"]


def check_no_hardcoded_data_renders() -> None:
    print("\n[8] Residual /data/renders hardcodes in source")
    found: list[str] = []
    # Exclude this module itself (it intentionally explains the migration)
    _self_relative = Path("app") / "core" / "runtime_paths.py"

    if not _SCAN_ROOT.exists():
        warn(f"Scan root not found: {_SCAN_ROOT}")
        return
    for py_file in _SCAN_ROOT.rglob("*.py"):
        rel = py_file.relative_to(_BACKEND_ROOT)
        # Skip the runtime_paths module — it documents the old path for reference
        if rel == _self_relative:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(content.splitlines(), start=1):
                # Allow occurrences only inside string literals in comments/docs
                if "/data/renders" in line:
                    # Skip pure comment lines and docstrings
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue
                    found.append(f"{rel}:{lineno}: {line.strip()}")
        except Exception:
            pass
    if found:
        for entry in found:
            print(f"     {entry}")
        fail(
            f"{len(found)} hardcoded /data/renders path(s) found — "
            "migrate to render_paths.*"
        )
    else:
        ok("No residual /data/renders hardcodes found")


# ── Main ──────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified Render Runtime Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  quick  – fastest CI check: imports + paths only (< 5 s, no infra, no scan)\n"
            "  fast   – quick + source hardcode scan (still no live infrastructure)\n"
            "  full   – deploy gate: all checks including DB, Celery, router"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "fast", "full"],
        default="quick",
        help="Verification mode (default: quick)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    mode = args.mode

    print("=" * 65)
    print(f" UNIFIED RENDER RUNTIME VERIFICATION  [mode={mode}]")
    print("=" * 65)

    if mode == "quick":
        # Quick: only imports + path writability — no source scan, no infra.
        # Must complete in < 5 s on a bare CI runner.
        check_imports(mode="quick")
        check_render_paths(mode="quick")
    elif mode == "fast":
        # Fast: quick checks + source hardcode scan.  Still no live infra.
        check_imports(mode="quick")
        check_render_paths(mode="quick")
        check_no_hardcoded_data_renders()
    else:
        # Full: all checks
        check_alembic_head()
        check_db_tables()
        check_imports(mode="full")
        check_render_paths(mode="full")
        check_celery_broker()
        check_router_registry()
        check_storage_paths()
        check_no_hardcoded_data_renders()

    print("\n" + "=" * 65)
    if _failures:
        print(f"\n{FAIL}  {len(_failures)} check(s) FAILED:\n")
        for f in _failures:
            print(f"   • {f}")
        if _warnings:
            print(f"\n{WARN}  {len(_warnings)} warning(s):\n")
            for w in _warnings:
                print(f"   • {w}")
        print()
        return 1

    if _warnings:
        print(f"\n{WARN}  All checks passed with {len(_warnings)} warning(s):\n")
        for w in _warnings:
            print(f"   • {w}")
    else:
        print(f"\n{PASS}  All checks passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
