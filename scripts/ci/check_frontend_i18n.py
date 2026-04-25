#!/usr/bin/env python3
"""CI guard: detect English-hardcoded strings in frontend components.

Scans ``frontend/src/components/`` and ``frontend/src/app/`` for common
English UI strings that should be going through the i18n ``useT()`` hook
instead of being hardcoded.

Patterns checked (case-insensitive):
  - English button labels: "Save", "Cancel", "Close", "Next", "Back", etc.
  - English section headings like "Dashboard", "Settings", "Render Jobs" in
    JSX text nodes (not in import paths or comments).

Exit codes: 0 = clean, 1 = violations found.

NOTE: This is a heuristic check — it flags *common* English strings in JSX
text content.  It intentionally allows English in:
  - import statements
  - TypeScript type annotations
  - URL/path strings
  - className values
  - console.log / comments
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Repo root relative to this script
_SCRIPT = Path(__file__).resolve()
_REPO_ROOT = _SCRIPT.parent.parent.parent
_SCAN_DIRS = [
    _REPO_ROOT / "frontend" / "src" / "components",
    _REPO_ROOT / "frontend" / "src" / "app",
]

# Patterns that are suspicious as hardcoded English in JSX text / string props
# (not exhaustive, but catches the most common cases)
_SUSPICIOUS_PATTERNS: list[re.Pattern[str]] = [
    # Button / action labels
    re.compile(r'>\s*(Save|Cancel|Close|Next|Back|Confirm|Submit|Delete|Edit|Create|Update)\s*<', re.IGNORECASE),
    # Section/page headings as JSX text
    re.compile(r'>\s*(Dashboard|Settings|Render Jobs|Script Upload|Templates|Autopilot|Strategy|Marketplace|Analytics|Wallet|Governance)\s*<', re.IGNORECASE),
    # Common status/label strings
    re.compile(r'>\s*(Loading\.\.\.|No events yet|No incidents|Realtime Progress)\s*<', re.IGNORECASE),
]

# Lines that are explicitly allowlisted (substring match)
_ALLOWLIST_SUBSTRINGS = [
    "//",          # comment
    "/*",          # comment
    "import ",     # import statement
    "className=",  # class attribute
    "href=",       # URL
    "console.",    # console call
    "useT(",       # already using i18n
    't("',         # already using i18n
    "// i18n-ok",  # explicit opt-out comment
]


def is_allowlisted(line: str) -> bool:
    stripped = line.strip()
    return any(sub in stripped for sub in _ALLOWLIST_SUBSTRINGS)


def scan_file(path: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return violations
    for lineno, line in enumerate(content.splitlines(), start=1):
        if is_allowlisted(line):
            continue
        for pat in _SUSPICIOUS_PATTERNS:
            if pat.search(line):
                violations.append((lineno, line.strip()))
                break
    return violations


def main() -> int:
    all_violations: list[tuple[Path, int, str]] = []

    for scan_dir in _SCAN_DIRS:
        if not scan_dir.exists():
            print(f"  ⚠  Scan directory not found: {scan_dir} (skipping)")
            continue
        for tsx_file in scan_dir.rglob("*.tsx"):
            file_violations = scan_file(tsx_file)
            for lineno, line in file_violations:
                rel = tsx_file.relative_to(_REPO_ROOT)
                all_violations.append((rel, lineno, line))

    if all_violations:
        print(f"\n✗  {len(all_violations)} potential English hardcode(s) found:\n")
        for rel, lineno, line in all_violations:
            print(f"   {rel}:{lineno}: {line[:120]}")
        print(
            "\n  Add // i18n-ok to the line to suppress if intentional,"
            " or route the string through useT().\n"
        )
        return 1

    print("✓  No suspicious English hardcodes found in frontend components.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
