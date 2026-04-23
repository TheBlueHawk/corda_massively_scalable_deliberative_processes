FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY apps/api ./apps/api
COPY msdp ./msdp

RUN uv sync --frozen --no-dev

CMD ["sh", "-c", "uv run uvicorn main:app --app-dir apps/api --host 0.0.0.0 --port ${PORT:-8080}"]
