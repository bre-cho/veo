#!/bin/bash
set -e

echo "Waiting for Postgres..."
python /app/scripts/wait_for_postgres.py

if [[ "${BACKEND_SCHEMA_BOOTSTRAP:-}" == "metadata-create-all" ]]; then
	echo "Bootstrapping schema from SQLAlchemy metadata..."
	python /app/scripts/bootstrap_metadata_schema.py
else
	echo "Running Alembic migrations..."
	if ! alembic upgrade head; then
		echo "WARNING: Alembic migration failed. Proceeding with service startup anyway." >&2
	fi
fi

echo "Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload