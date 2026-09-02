FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system taskcli \
    && useradd \
        --system \
        --gid taskcli \
        --no-create-home \
        taskcli

WORKDIR /app

COPY pyproject.toml .
COPY src ./src

RUN pip install --no-cache-dir .

COPY alembic.ini .
COPY alembic ./alembic

USER taskcli

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=10s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).read()"

CMD ["uvicorn", "task_cli.api:app", "--host", "0.0.0.0", "--port", "8000"]
