# Signal Brief – article curation and summarizer
# Build:  docker build -t signal-brief .
# Run:    docker run --rm --env-file .env signal-brief https://example.com/article
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
RUN useradd --create-home --uid 10001 signalbrief
USER signalbrief

# Mount a folder here to use --html-file with saved pages
WORKDIR /data

ENTRYPOINT ["python", "/app/summarize.py"]
CMD ["--help"]
