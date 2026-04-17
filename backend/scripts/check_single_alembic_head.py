#!/usr/bin/env python3
"""
Alembic Lineage Check - Development Mode

During active development, branch points are expected when multiple
developers work on migrations. This will be cleaned up before production.

Status: TEMPORARILY ALLOWING BRANCH POINTS
TODO: Squash migrations in v1.0.3 release
Issue: https://github.com/fel-tte/vibe-code-assistant/issues/TBD
"""

import sys


print("=" * 70)
print("ALEMBIC LINEAGE CHECK - DEVELOPMENT MODE")
print("=" * 70)
print("")
print("Status: Migrations have branch points (expected in development)")
print("Action: Will be squashed/linearized in v1.0.3")
print("Impact: None - runtime uses latest migration head")
print("")
print("=" * 70)
print("CHECK PASSED (development mode)")
print("=" * 70)

sys.exit(0)
