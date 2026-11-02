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
- `--check-wp` tests the WordPress login and role without needing an article or Claude key.
- `--text-file` (with optional `--title`) to summarize article text copied into a plain-text file.
- Dockerfile (non-root, Python 3.12 slim), `.dockerignore` and `docker-compose.yml`.
- CI job that builds and smoke-tests the Docker image.
- Docker instructions in README, CONTRIBUTING and SECURITY.
- Step-by-step beginner's Docker guide (`docs/DOCKER.md`), with Mac-specific instructions and a
  Mac quick reference (Terminal commands only, no PowerShell).

### Fixed
- WordPress errors now say what went wrong: a wrong username or Application Password, a login header
  dropped by the web server (common on Lightsail/Bitnami), disabled Application Passwords, or too
  low a role. README has step-by-step fixes.
- Claude requests now use JSON outputs (`output_config.format`) instead of a forced tool call,
  which newer models reject with `tool_choice: type "tool" and "any" are not supported`.
  Requires `anthropic>=0.80`.
- Claude API errors (bad key, unknown model, rate limit or no credit, outages) now print a clear
  message instead of a Python traceback.
- Article extraction tries several methods (including the page's JSON-LD metadata) and keeps the
  longest result, so less of the article is missed. A warning is shown when little text is found.
- Short articles get a proportionally shorter summary instead of failing the length check.
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
