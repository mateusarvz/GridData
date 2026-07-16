FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema e Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

# Copiar arquivos de configuração do Poetry
COPY pyproject.toml poetry.lock* ./

# Instalar dependências sem o próprio pacote
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copiar o código fonte
COPY . .

# Instalar a aplicação
RUN poetry install --no-interaction --no-ansi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
