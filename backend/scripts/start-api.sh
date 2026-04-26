#!/bin/bash
set -e

echo "Waiting for Postgres..."
python /app/scripts/wait_for_postgres.py

if [[ "${BACKEND_SCHEMA_BOOTSTRAP:-}" == "metadata-create-all" ]]; then
	echo "Bootstrapping schema from SQLAlchemy metadata..."
	python /app/scripts/bootstrap_metadata_schema.py
	echo "Stamping Alembic version to head..."
	alembic stamp head
else
	echo "Running Alembic migrations..."
	alembic upgrade head
fi

echo "Verifying runtime DB schema..."
python /app/scripts/verify_runtime_schema.py

echo "Starting FastAPI..."
if [[ "${APP_ENV:-production}" == "dev" ]]; then
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  uvicorn app.main:app --host 0.0.0.0 --port 8000
fi