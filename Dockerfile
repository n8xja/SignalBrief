# Defensive Dispatch – article summarizer
# Build:  docker build -t defensive-dispatch .
# Run:    docker run --rm --env-file .env defensive-dispatch https://example.com/article
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY summarize.py .

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 dispatch
USER dispatch

# Mount a folder here to use --html-file with saved pages
WORKDIR /data

ENTRYPOINT ["python", "/app/summarize.py"]
CMD ["--help"]
