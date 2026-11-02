# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Dockerfile (non-root, Python 3.12 slim), `.dockerignore` and `docker-compose.yml`.
- CI job that builds and smoke-tests the Docker image.
- Docker instructions in README, CONTRIBUTING and SECURITY.

## [0.1.0] - 2026-11-02

### Added
- Summarize one article URL into a working title, a 150–250 word summary and 5 key points using Claude.
- Create a WordPress draft through the REST API, with a "Read more" link to the original article.
- Checks for copied text, bullet count and summary length, with one automatic retry.
- `--dry-run`, `--json` and `--html-file` options.
- Offline test suite and GitHub Actions workflow.
