#!/bin/bash
set -e

echo "Waiting for Postgres..."
python /app/scripts/wait_for_postgres.py

echo "Verifying runtime DB schema..."
python /app/scripts/verify_runtime_schema.py

echo "Starting Celery worker..."
celery -A app.core.celery_app.celery_app worker -l info \
  -Q celery,render_dispatch,render_poll,render_postprocess,render_callback,render_maintenance,audio,template,autopilot,drama
