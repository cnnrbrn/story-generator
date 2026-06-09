# Multi-stage, uv-based image. Two targets:
#   dev  — installs test deps, runs uvicorn with --reload (code is bind-mounted)
#   prod — lean (no dev deps), plain uvicorn
# Compose picks the target: docker-compose.override.yml -> dev, prod.yml -> prod.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
# Resolve dependencies first for better layer caching. Copy the lockfile too so
# installs are reproducible.
COPY pyproject.toml uv.lock ./

# --- Development image: includes dev deps (pytest, httpx), hot-reload server ---
FROM base AS dev
RUN uv sync
COPY app ./app
EXPOSE 8000
# In dev, compose bind-mounts ./backend/app over /app/app so edits reload live.
CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Production image: no dev deps, no reload ---
FROM base AS prod
RUN uv sync --no-dev
COPY app ./app
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
