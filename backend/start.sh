#!/bin/bash
set -euo pipefail

cd /app

if [ -f /app/backend/.env ]; then
  eval "$(/app/backend/scripts/load_env.sh /app/backend/.env)"
fi

export VITE_SUPABASE_URL="${VITE_SUPABASE_URL:-${SUPABASE_URL:-}}"
export VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY:-${SUPABASE_ANON_KEY:-}}"
export VITE_API_URL="${VITE_API_URL:-${API_URL:-${APP_BASE_URL:-}}}"

if [ ! -d frontend/dist ]; then
  echo "Building frontend assets..."
  cd /app/frontend
  npm ci
  npm run build
  cd /app
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
