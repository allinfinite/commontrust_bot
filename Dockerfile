FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install hatch

COPY pyproject.toml .

RUN pip install hatch || pip install aiogram pocketbase pydantic pydantic-settings python-dotenv httpx

COPY . .

RUN pip install -e .

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["python", "-m", "commontrust_bot.main"]
