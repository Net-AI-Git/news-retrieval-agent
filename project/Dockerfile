FROM        python:3.12.8-slim-bookworm AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.10.9 /uv /bin/uv
WORKDIR     /src

ENV         PYTHONUNBUFFERED=1 \
            PYTHONDONTWRITEBYTECODE=1 \
            UV_COMPILE_BYTECODE=1 \
            UV_LINK_MODE=copy

COPY        pyproject.toml uv.lock README.md ./
RUN         uv sync --frozen --no-dev --no-install-project

COPY        src ./src
COPY        static ./static
COPY        main.py ./
# --------------------------------------------------------------------
FROM        python:3.12.8-slim-bookworm AS runtime
WORKDIR     /src

ENV         PYTHONUNBUFFERED=1 \
            PYTHONDONTWRITEBYTECODE=1 \
            PATH="/src/.venv/bin:$PATH"

COPY        --from=builder /src/.venv ./.venv
COPY        --from=builder /src/src ./src
COPY        --from=builder /src/static ./static
COPY        --from=builder /src/main.py ./

EXPOSE      8000

CMD         ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
