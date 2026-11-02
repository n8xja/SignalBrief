# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Project renamed to **Signal Brief** (repository `SignalBrief`, Docker image `signal-brief`).
- README introduction rewritten around curation and respect for the original authors.
- Site-specific URLs replaced with generic examples.
- Documented the minimum WordPress role as **Contributor** (previously listed as Author), with a
  recommended dedicated-user setup.

### Added
- Dockerfile (non-root, Python 3.12 slim), `.dockerignore` and `docker-compose.yml`.
- CI job that builds and smoke-tests the Docker image.
- Docker instructions in README, CONTRIBUTING and SECURITY.
- Step-by-step beginner's Docker guide (`docs/DOCKER.md`).

### Fixed
- Page fetching now sends standard browser headers, uses separate connect/read timeouts and
  retries once on a timeout. This fixes read timeouts from sites that stall non-browser requests.
  If a site still blocks it, the error now explains how to use `--html-file`.
- A missing `--html-file` now prints a clear error instead of a Python traceback.

## [0.1.0] - 2026-11-02

### Added
- Summarize one article URL into a working title, a 150–250 word summary and 5 key points using Claude.
- Create a WordPress draft through the REST API, with a "Read more" link to the original article.
- Checks for copied text, bullet count and summary length, with one automatic retry.
- `--dry-run`, `--json` and `--html-file` options.
- Offline test suite and GitHub Actions workflow.
