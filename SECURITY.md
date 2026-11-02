# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, use GitHub's
[private vulnerability reporting](https://github.com/n8xja/DefensiveDispatch/security/advisories/new)
for this repository. Include a description, steps to reproduce, and the impact you expect.
You should get a response within a few days.

## Handling credentials

- Keep `ANTHROPIC_API_KEY` and `WP_APP_PASSWORD` in `.env`, which is excluded by `.gitignore`.
- Use a dedicated WordPress Application Password for this tool so it can be revoked on its own
  (*Users → Profile → Application Passwords → Revoke*).
- Use a WordPress account with the lowest role that can create posts (Author).
- Only connect to WordPress over HTTPS.
- With Docker, pass settings at run time (`--env-file .env` or Compose's `env_file`). Never copy
  `.env` into an image or push an image that contains it; `.dockerignore` excludes it from builds.
- If a key or password is ever committed, revoke it immediately, then remove it from the history.
