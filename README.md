# Signal Brief

[![Tests](https://github.com/n8xja/SignalBrief/actions/workflows/tests.yml/badge.svg)](https://github.com/n8xja/SignalBrief/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Curate the articles your readers should know about, and make the write-up your own.**

Signal Brief helps you pick out the important stories from the noise and share them
responsibly. Give it the URL of an article worth passing on. It fetches the page, has
[Claude](https://platform.claude.com) write a 2–3 sentence **BLUF (Bottom Line Up Front)** and the
**5 most important points** in its own words, and saves it as a **draft** post on your WordPress site.

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
URL ──► fetch page ──► extract article text ──► Claude: title + BLUF + 5 key points
                                                        │
                                                        ▼
                                  checks: BLUF ≤ 3 sentences, exactly 5 points, no copied text
                                                        │  (one retry with feedback)
                                                        ▼
                                  WordPress REST API ──► draft post ──► edit link
```

### What the draft contains

| Section | Details |
|---|---|
| Title | A working title written by Claude, ready for you to edit |
| **BLUF: Bottom Line Up Front** | 2 or 3 concise sentences (about 70 words at most): what happened, who is affected, and what defenders should do |
| Key Points | Exactly 5 bullets aimed at security defenders |
| Read more | Link to the original article (opens in a new tab) |

### Built-in checks

- **No copied text.** If any 8-word run in the output also appears in the article, the output
  is rejected and Claude rewrites it.
- **A short BLUF:** no more than 3 sentences and about 90 words.
- **Exactly 5 key points.**
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
| `EDITORIAL_BRIEF` | No | Your publication's mission statement, used to guide how Claude writes. See [Editorial brief](#editorial-brief). |

> `.env` is listed in `.gitignore`. Never commit it.

## Editorial brief

Signal Brief writes for **business leaders**, not security specialists. Every draft is guided by an
editorial brief. The built-in one is:

> This publication delivers hand-picked cybersecurity insights and intelligence tailored for
> business leaders. We cut through the noise to show what actually matters: why specific threats
> deserve attention, what they mean for an organization, and what defensive actions to consider.

From that brief, Claude:

- writes in plain language, leading with business meaning (risk, exposure, operations, customers,
  cost) and briefly explaining any technical term it needs
- shapes the **BLUF** around why the threat deserves attention, what it means for an organization,
  and the key action to consider
- orders the **5 key points** for a business reader: what is happening and why it matters, what it
  means for an organization, then at least two **defensive actions to consider**, each starting
  with a verb
- takes facts (who, what, when, versions) only from the article, while implications and actions
  may be general, sensible guidance

**Use your own brief.** Put your publication's statement in `.env` on one line (quotes are optional):

```ini
EDITORIAL_BRIEF="Your Publication delivers hand-picked cybersecurity insights for business leaders. We show why specific threats deserve attention, what they mean for your organization, and what defensive actions to consider."
```

Your brief replaces the built-in one, and the plain-language and key-point guidance above still
applies.

## Usage

```bash
# Preview the output; nothing is posted
python summarize.py https://example.com/article --dry-run

# Summarize and create the WordPress draft
python summarize.py https://example.com/article

# Test the WordPress login and role only (no article, no Claude key needed)
python summarize.py --check-wp

# Print the result as JSON
python summarize.py https://example.com/article --dry-run --json

# Use a saved copy of the page (for sites that block scripts or need JavaScript)
python summarize.py https://example.com/article --html-file saved-page.html

# Use the article text copied into a plain-text file (first line = headline)
python summarize.py https://example.com/article --text-file article.txt
```

Always pass the article's real URL, even with `--html-file` or `--text-file`: it's used for the
**Read more** link.

### Choosing how the article is read

| Option | When to use it |
|---|---|
| *(none)* | Normal case: the tool downloads the page itself. |
| `--html-file` | The site blocks the tool or times out. Save the page from your browser first. |
| `--text-file` | The tool finds only part of the article (it warns `Only N words of article text were found`), or a saved page doesn't work. Select the article text in your browser, copy it, and paste it into a plain-text file. Put the headline on the first line, or pass `--title "Headline"`. |

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
| `WordPress says the username or password is wrong` | `WP_APP_PASSWORD` must be an **Application Password**, not the password you use to log in to wp-admin. See [Fixing WordPress login errors](#fixing-wordpress-login-errors). |
| `WordPress did not receive the login` (HTTP 401) | The web server is dropping the login header before WordPress sees it. This is common on AWS Lightsail (Bitnami). See [Fixing WordPress login errors](#fixing-wordpress-login-errors). |
| `HTTP 403` from WordPress | The user's role may be too low: it needs **Contributor** or higher (a Subscriber can't create posts). Otherwise, a security plugin (Wordfence, Solid Security, etc.) may be blocking the REST API or Application Passwords. Allow them in the plugin settings. |
| `Could not find enough article text` | The page is JavaScript-rendered or paywalled. Copy the article text into a file and use `--text-file`. |
| `[warning] Only N words of article text were found` | Part of the article was missed, which is common on pages that load content with JavaScript. If the article is longer than that, use `--text-file`. Short articles get a shorter summary automatically. |
| `The site refused the request` | The site blocks scripts. Use `--html-file`. |
| `The site did not respond in time` (or `Read timed out`) | Some large sites, often behind Akamai or Cloudflare bot protection, quietly stall automated requests instead of refusing them. The tool sends browser-style headers and retries once, but some sites still block it. Use `--html-file` with a saved copy of the page. |
| `Missing setting ...` | A required value is missing from `.env`. |
| `The Claude API rejected the key (HTTP 401)` | `ANTHROPIC_API_KEY` is wrong or was revoked. Create a new key at platform.claude.com. |
| `Model '...' was not found` | `CLAUDE_MODEL` in `.env` has a typo or names a retired model. Remove the line to use the default. |
| `rate limit was reached, or the account is out of credit` | Wait a minute and retry, or add credit under **Billing** at platform.claude.com. |

## Fixing WordPress login errors

Start by running the built-in check. It tests only the WordPress login and needs no article or
Claude key:

```bash
python summarize.py --check-wp
```

With Docker:

```bash
docker run --rm --env-file .env signal-brief --check-wp
```

When it works, it prints something like
`Logged in to WordPress as 'signalbrief' (roles: contributor). Drafts can be created.`
Otherwise it tells you which of these problems you have.

### "The username or password is wrong"

WordPress received the login but didn't accept it.

- **Use an Application Password, not your login password.** Being able to log in to wp-admin
  doesn't mean the API will accept that password: the REST API only accepts Application Passwords.
  In wp-admin, go to **Users → Profile → Application Passwords**, create one, and paste it into
  `WP_APP_PASSWORD`. It looks like `abcd EFGH 1234 ijkl MNOP 5678`; the spaces are fine.
- **Create it on the same user as `WP_USER`.** An Application Password only works with the user it
  was created for. If you made a separate `signalbrief` user, log in as that user to create it.
- **`WP_USER` is the username** (shown under **Users**), not the display name.
- **No quotes or extra spaces** around the values in `.env`.

### "WordPress did not receive the login"

WordPress saw the request as anonymous: the web server removed the `Authorization` header before
passing the request to WordPress. Apache running PHP through PHP-FPM, which is how Bitnami
WordPress on AWS Lightsail is set up, does this by default. You fix it once on the server.

**AWS Lightsail (Bitnami)**

1. Connect to the server: in the Lightsail console, open the instance and click
   **Connect using SSH**.
2. Back up the two Apache config files:
   ```bash
   sudo cp /opt/bitnami/apache/conf/vhosts/wordpress-vhost.conf /opt/bitnami/apache/conf/vhosts/wordpress-vhost.conf.bak
   ```
   ```bash
   sudo cp /opt/bitnami/apache/conf/vhosts/wordpress-https-vhost.conf /opt/bitnami/apache/conf/vhosts/wordpress-https-vhost.conf.bak
   ```
3. Open the HTTPS config file:
   ```bash
   sudo nano /opt/bitnami/apache/conf/vhosts/wordpress-https-vhost.conf
   ```
4. Directly below the line that starts with `<VirtualHost`, add this line:
   ```apache
   SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1
   ```
   Save with **Ctrl+O**, **Enter**, then exit with **Ctrl+X**.
5. Do the same in `wordpress-vhost.conf` (the HTTP version):
   ```bash
   sudo nano /opt/bitnami/apache/conf/vhosts/wordpress-vhost.conf
   ```
6. Check the configuration, then restart Apache:
   ```bash
   sudo /opt/bitnami/apache/bin/apachectl -t
   ```
   It should say `Syntax OK`. Then:
   ```bash
   sudo /opt/bitnami/ctlscript.sh restart apache
   ```
7. Run `--check-wp` again.

If `apachectl -t` reports an error, restore the backups (`sudo cp ....bak` back over the original
files) and restart Apache.

If those files don't exist, your instance uses Bitnami's older layout. Add the same line inside the
`<Directory>` block in `/opt/bitnami/apps/wordpress/conf/httpd-app.conf`, then restart Apache.

**Other Apache servers (not Bitnami)**

Add this line near the top of the `.htaccess` file in the WordPress folder, above
`# BEGIN WordPress`:

```apache
SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1
```

### Still failing?

- A security plugin (Wordfence, Solid Security, All In One WP Security, etc.) may be blocking the
  REST API or Application Passwords. Check its settings, or briefly turn it off to test.
- A CDN or firewall in front of the site (Cloudflare, Lightsail load balancer) can also strip the
  header. Try `WP_URL` with the server's direct address to rule it out.

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
