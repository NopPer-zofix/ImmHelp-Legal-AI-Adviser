# Flask API served by gunicorn. Built by ../docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes don't reinstall them
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Don't run as root inside the container
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/chroma_db \
    && chown -R app:app /app
USER app

EXPOSE 5000

# One worker process with threads: server.py indexes documents when it is imported, and the
# "answers in progress" counter is per process. /ask can take a while, hence the long timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", \
     "--timeout", "180", "--access-logfile", "-", "wsgi:app"]
