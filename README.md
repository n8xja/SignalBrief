# Signal Brief

[![Tests](https://github.com/n8xja/SignalBrief/actions/workflows/tests.yml/badge.svg)](https://github.com/n8xja/SignalBrief/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Curate the articles your readers should know about, and make the write-up your own.**

Signal Brief helps you pick out the important stories from the noise and share them
responsibly. Give it the URL of an article worth passing on. It fetches the page, has
[Claude](https://platform.claude.com) write a short summary and the **5 most important points**
in its own words, and saves it as a **draft** post on your WordPress site.

The draft is a starting point, not a finished post: you edit it, add your own analysis and voice,
and publish it when it's yours. Every post ends with a **Read more** link that sends readers to
the original article.

### Respecting the original authors

- Summaries are written fresh. The tool rejects any output that copies an 8-word run from the
  article and asks Claude to reword it.
- Every draft credits and links to the source.
- Nothing is published automatically, so you review every post before it goes live.

Works with any self-hosted WordPress site.

---

## How it works

```
URL ──► fetch page ──► extract article text ──► Claude: title + summary + 5 key points
                                                        │
                                                        ▼
                                  checks: exactly 5 points, length OK, no copied text
                                                        │  (one retry with feedback)
                                                        ▼
                                  WordPress REST API ──► draft post ──► edit link
```

### What the draft contains

| Section | Details |
|---|---|
| Title | A working title written by Claude, ready for you to edit |
| Summary | 150–250 words, paraphrased |
| Key Points | Exactly 5 bullets aimed at security defenders |
| Read more | Link to the original article (opens in a new tab) |

### Built-in checks

- **No copied text.** If any 8-word run in the output also appears in the article, the output
  is rejected and Claude rewrites it.
- **Exactly 5 key points** and a reasonable summary length.
- **Drafts only.** Posts are always created with `status: draft`.
- If the checks still fail after one retry, nothing is posted.

---

## Requirements

- Python 3.9 or later, **or** Docker (see [Running with Docker](#running-with-docker))
- A Claude API key from [platform.claude.com](https://platform.claude.com) (API usage is billed
  separately from a Claude subscription)
- A self-hosted WordPress site served over **HTTPS** with the REST API enabled (it is by default)
- A WordPress user with the **Contributor** role or higher (see
  [WordPress user role](#wordpress-user-role))

## Installation

```bash
git clone https://github.com/n8xja/SignalBrief.git
cd SignalBrief
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## WordPress user role

The minimum role is **Contributor**. Creating a draft through the REST API needs only the
`edit_posts` capability, which Contributors have.

| Role | Create drafts | Assign existing categories | Publish | Upload media | Suitable? |
|---|---|---|---|---|---|
| Subscriber | No | No | No | No | No: posting fails with HTTP 403 |
| **Contributor** | Yes | Yes | No | No | **Yes (recommended)** |
| Author | Yes | Yes | Own posts | Yes | Yes, but more access than needed |
| Editor / Administrator | Yes | Yes | Any post | Yes | Works, but avoid: far more access than needed |

**Recommended setup:** create a separate WordPress user just for Signal Brief (for example
`signalbrief`) with the Contributor role, and create the Application Password on that user.
If the key ever leaks, the worst it can do is add drafts. It can't publish, change existing posts
or touch site settings.

What this means in practice:

- Drafts appear under **Posts → All Posts** with that user as the author. Before publishing, you
  can change the author to yourself in the post's settings panel (**Post → Author**).
- Publishing is done by you, from your own account. That matches the workflow: the draft is a
  starting point that you edit and make your own.
- If a future version adds featured images, the user will need the **Author** role, since
  Contributors can't upload media.

To create the user: in wp-admin go to **Users → Add New User**, enter a username and email,
set **Role** to **Contributor**, and click **Add New User**. Then log in as that user (or ask an
administrator) to create its Application Password.

## Configuration

1. **Create a WordPress Application Password** for the user described above. In wp-admin, go to
   *Users → Profile → Application Passwords*. Name it (for example "Article summarizer"),
   click **Add New Application Password**, and copy the password it shows.
2. **Create your settings file:**
   ```bash
   cp .env.example .env
   ```
3. **Fill in `.env`:**

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Claude API key |
| `WP_URL` | Yes | Your site, e.g. `https://your-site.example.com` |
| `WP_USER` | Yes | WordPress username |
| `WP_APP_PASSWORD` | Yes | The Application Password (spaces are fine) |
| `WP_CATEGORY_ID` | No | Numeric category ID for new drafts |
| `CLAUDE_MODEL` | No | Model to use (default `claude-sonnet-5-5`) |

> `.env` is listed in `.gitignore`. Never commit it.

## Usage

```bash
# Preview the output; nothing is posted
python summarize.py https://example.com/article --dry-run

# Summarize and create the WordPress draft
python summarize.py https://example.com/article

# Print the result as JSON
python summarize.py https://example.com/article --dry-run --json

# Use a saved copy of the page (for sites that block scripts or need JavaScript)
python summarize.py https://example.com/article --html-file saved-page.html
```

On success, the last line shows the draft's edit link:

```
Draft created (post 128): https://your-site.example.com/wp-admin/post.php?post=128&action=edit
```

## Running with Docker

No local Python needed.

> **New to Docker?** Follow the step-by-step [Docker guide](docs/DOCKER.md). It covers installing
> Docker on Windows, macOS and Linux, creating `.env`, building, running and troubleshooting.
> Mac users can go straight to the [Mac quick reference](docs/DOCKER.md#mac-quick-reference).

Quick start for Docker users. Build the image once:

```bash
docker build -t signal-brief .
```

Then run it with your `.env` file:

```bash
# Preview
docker run --rm --env-file .env signal-brief https://example.com/article --dry-run

# Create the WordPress draft
docker run --rm --env-file .env signal-brief https://example.com/article
```

To use a saved page, mount the folder that holds it at `/data`:

```bash
docker run --rm --env-file .env -v "$PWD/pages:/data" \
  signal-brief https://example.com/article --html-file saved-page.html
```

Or with Docker Compose (reads `.env` and mounts `./pages` automatically):

```bash
docker compose build
docker compose run --rm summarize https://example.com/article --dry-run
```

The image runs as an unprivileged user, and `.env` is excluded from the build by `.dockerignore`,
so your keys are never baked into the image.

## Troubleshooting

| Problem | Fix |
|---|---|
| `WordPress rejected the login (HTTP 401)` even with correct credentials | Some Apache setups, including Bitnami WordPress on AWS Lightsail, drop the `Authorization` header. Add `SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1` to `.htaccess` or the Apache vhost config, then restart Apache (`sudo /opt/bitnami/ctlscript.sh restart apache`). |
| `HTTP 403` from WordPress | The user's role may be too low: it needs **Contributor** or higher (a Subscriber can't create posts). Otherwise, a security plugin (Wordfence, Solid Security, etc.) may be blocking the REST API or Application Passwords. Allow them in the plugin settings. |
| `Could not find enough article text` | The page is JavaScript-rendered or paywalled. Save it from your browser and use `--html-file`. |
| `The site refused the request` | The site blocks scripts. Use `--html-file`. |
| `The site did not respond in time` (or `Read timed out`) | Some large sites, often behind Akamai or Cloudflare bot protection, quietly stall automated requests instead of refusing them. The tool sends browser-style headers and retries once, but some sites still block it. Use `--html-file` with a saved copy of the page. |
| `Missing setting ...` | A required value is missing from `.env`. |

## Development

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests run offline: Claude and WordPress are stubbed, so no API key is needed.
GitHub Actions runs them on every push and pull request.

## Project structure

```
.
├── summarize.py            # the application
├── test_summarize.py       # offline tests
├── requirements.txt        # runtime dependencies
├── requirements-dev.txt    # test dependencies
├── .env.example            # settings template
├── Dockerfile              # container image
├── docker-compose.yml      # optional Compose setup
├── docs/DOCKER.md          # beginner's Docker guide
└── .github/                # CI workflow and issue/PR templates
```

## Roadmap

- Batch mode (a list of URLs)
- RSS feed input and scheduled runs
- Extraction of CVEs, threat actors and ATT&CK techniques as WordPress tags

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue,
see [SECURITY.md](SECURITY.md).

## Responsible use

This tool writes original summaries and always links to the source. Review every draft before
publishing, check facts against the original article, and respect the source site's terms of use.

## License

[MIT](LICENSE)
