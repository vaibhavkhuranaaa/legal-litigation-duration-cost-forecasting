FROM node:22-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.11.29 AS uv
FROM python:3.12-slim

RUN groupadd --system planner && useradd --system --gid planner --home-dir /app planner
WORKDIR /app
COPY --from=uv /uv /bin/uv
COPY runtime-requirements.txt ./
RUN uv venv .venv && uv pip sync --python .venv/bin/python runtime-requirements.txt
COPY src/litigation_planner/__init__.py ./src/litigation_planner/__init__.py
COPY src/litigation_planner/api.py ./src/litigation_planner/api.py
COPY src/litigation_planner/demo.py ./src/litigation_planner/demo.py
COPY src/litigation_planner/http_security.py ./src/litigation_planner/http_security.py
COPY src/litigation_planner/milestones.py ./src/litigation_planner/milestones.py
COPY src/litigation_planner/scenarios.py ./src/litigation_planner/scenarios.py
COPY scripts/build_demo_seed.py ./scripts/build_demo_seed.py
COPY --from=frontend /web/dist ./frontend/dist
COPY frontend/src/full-population.v1.json ./release/full-population.json
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    DEMO_DB_PATH=/app/release/demo.sqlite \
    POPULATION_CUBE_PATH=/app/release/full-population.json \
    STATIC_DIR=/app/frontend/dist
RUN .venv/bin/python scripts/build_demo_seed.py --output /app/release/demo.sqlite \
    && chown -R planner:planner /app/release
USER planner
EXPOSE 8080
CMD ["uvicorn", "litigation_planner.api:app", "--host", "0.0.0.0", "--port", "8080", "--limit-concurrency", "100", "--timeout-keep-alive", "5", "--no-access-log"]
