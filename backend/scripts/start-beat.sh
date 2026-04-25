#!/bin/bash
set -e

echo "Waiting for Postgres..."
python /app/scripts/wait_for_postgres.py

echo "Verifying runtime DB schema..."
python /app/scripts/verify_runtime_schema.py

echo "Starting Celery beat..."
celery -A app.core.celery_app.celery_app beat -l info