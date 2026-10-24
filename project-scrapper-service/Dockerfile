FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT="1" \
    POETRY_NO_INTERACTION="1"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

ENV PATH="/app/.venv/bin:$PATH"

COPY src /app/src
COPY migrations /app/migrations

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]