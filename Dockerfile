FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

ENV UV_PYTHON=python3.11

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . /code

ENV PATH="/code/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--access-log", "--log-level", "info"]