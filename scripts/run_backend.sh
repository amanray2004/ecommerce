#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d venv ]]; then
  echo "venv not found in $ROOT_DIR. Create it first: python3 -m venv venv"
  exit 1
fi

source venv/bin/activate

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
elif [[ -f scripts/backend.env ]]; then
  set -a
  source scripts/backend.env
  set +a
else
  echo ".env not found. Create it from .env.example (or use scripts/backend.env fallback)."
  exit 1
fi

exec python -m uvicorn app.main:app --reload
