#!/bin/bash
set -euo pipefail

cd /app

if [ -f /app/backend/.env ]; then
  eval "$(/app/backend/scripts/load_env.sh /app/backend/.env)"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
