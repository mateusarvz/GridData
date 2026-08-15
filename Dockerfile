# ---------- Stage 1: Build do frontend ----------
FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_URL
ARG APP_BASE_URL
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL:-${SUPABASE_URL:-}} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY:-${SUPABASE_ANON_KEY:-}} \
    VITE_API_URL=${VITE_API_URL:-${API_URL:-${APP_BASE_URL:-}}}
RUN npm run build

# ---------- Stage 2: Instala dependências Python (sem dev) ----------
FROM python:3.12-bookworm AS python-builder
WORKDIR /build
COPY backend/pyproject.toml backend/poetry.lock ./
RUN python3 -m pip install --no-cache-dir --break-system-packages poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --without dev

# ---------- Stage 3: Imagem final enxuta ----------
FROM python:3.12-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    MPLBACKEND=Agg \
    PORT=8000

# Libs de runtime (sem build-essential, node, gnupg, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libpq5 \
    libfreetype6 \
    libpng16-16 \
    libgomp1 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Copia site-packages e binários instalados pelo Poetry
COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Código da aplicação
COPY backend/app ./app
COPY backend/DADOS_PARA_LANGCHAIN ./DADOS_PARA_LANGCHAIN
COPY backend/start.sh ./backend/start.sh
COPY backend/scripts ./backend/scripts

# Frontend buildado
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

RUN chmod +x /app/backend/start.sh /app/backend/scripts/load_env.sh

EXPOSE 8000
CMD ["/app/backend/start.sh"]