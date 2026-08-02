FROM python:3.12-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    MPLBACKEND=Agg \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    gnupg \
    libpq-dev \
    libfreetype6 \
    libpng16-16 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --break-system-packages poetry

COPY backend/pyproject.toml backend/poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY frontend/ ./frontend/
COPY backend/. ./backend/

RUN cd frontend && npm ci && if [ -f /app/backend/.env ]; then set -a; . /app/backend/.env; set +a; fi && export VITE_SUPABASE_URL="${VITE_SUPABASE_URL:-${SUPABASE_URL:-}}" && export VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY:-${SUPABASE_ANON_KEY:-}}" && export VITE_API_URL="${VITE_API_URL:-${API_URL:-${APP_BASE_URL:-}}}" && npm run build

COPY backend/app ./app
COPY backend/DADOS_PARA_LANGCHAIN ./DADOS_PARA_LANGCHAIN

RUN chmod +x /app/backend/start.sh

EXPOSE 8000

CMD ["/app/backend/start.sh"]
