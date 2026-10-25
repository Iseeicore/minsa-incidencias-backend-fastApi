FROM python:3.14.7-slim-bookworm AS build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.14.7-slim-bookworm AS runtime

RUN useradd --system --uid 10001 --no-create-home app

WORKDIR /app

COPY --from=build /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=3033

USER app

EXPOSE 3033

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/salud', timeout=3)"]

CMD ["python", "-m", "app"]
