#!/bin/bash
set -e

# Bootstrap backend .env.dev
BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -f "${BACKEND_DIR}/.env.dev" ]; then
  cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env.dev"
  echo ".env.dev created from .env.example"
else
  echo ".env.dev already exists"
fi

# Bootstrap frontend .env.local
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
if [ -d "${FRONTEND_DIR}" ]; then
  if [ ! -f "${FRONTEND_DIR}/.env.local" ]; then
    if [ -f "${FRONTEND_DIR}/.env.example" ]; then
      cp "${FRONTEND_DIR}/.env.example" "${FRONTEND_DIR}/.env.local"
      echo "frontend/.env.local created from frontend/.env.example"
    else
      touch "${FRONTEND_DIR}/.env.local"
      echo "frontend/.env.local created (empty — no .env.example found)"
    fi
  else
    echo "frontend/.env.local already exists"
  fi
fi