# =============================================================================
# Stage 1 : builder — compile et installe les dépendances
# =============================================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Outils de compilation (gcc pour psycopg2) — resteront dans ce stage uniquement
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie uv depuis son image officielle
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Cache layer : on copie d'abord les fichiers de dépendances seuls
# Si le code change mais pas pyproject.toml/uv.lock → cette layer est réutilisée
COPY pyproject.toml uv.lock ./

# Installe les dépendances dans un venv isolé (sans les deps de dev)
RUN uv sync --frozen --no-dev

# Copie le code source ensuite (layer invalidée uniquement si le code change)
COPY app/ ./app/

# =============================================================================
# Stage 2 : runtime — image finale légère sans les outils de compilation
# =============================================================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Seule lib runtime nécessaire pour psycopg2 (pas gcc)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie uniquement le venv et le code depuis le builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app ./app/

# Utilise le venv du builder
ENV PATH="/app/.venv/bin:$PATH"

# Utilisateur non-root pour la sécurité
RUN useradd --no-create-home appuser
USER appuser

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]
