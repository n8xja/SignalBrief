#!/usr/bin/env python3
"""Signal Brief: summarize one article URL and save it as a WordPress draft.

Usage:
    python summarize.py https://example.com/article            # summarize + create draft
    python summarize.py https://example.com/article --dry-run  # summarize only, print result
    python summarize.py https://example.com/article --html-file saved.html --dry-run
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

import requests
import trafilatura
from dotenv import load_dotenv

# Many sites (especially behind Akamai or Cloudflare) silently stall requests that don't look
# like a normal browser, which shows up as a read timeout. Send the usual browser headers.
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
FETCH_TIMEOUT = (10, 45)     # seconds: (connect, read)
FETCH_ATTEMPTS = 2
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_ARTICLE_CHARS = 60_000   # keeps very long pages within a sensible token budget
MIN_ARTICLE_WORDS = 100      # below this, extraction probably failed (paywall, JS-only page)
SHORT_ARTICLE_WORDS = 400    # below this, warn and ask for a shorter summary
COPY_NGRAM = 8               # any 8-word run shared with the source counts as copied text
MAX_ATTEMPTS = 2             # first try + one retry with feedback

SYSTEM_PROMPT = """You are an analyst helping a cybersecurity threat-intelligence writer curate articles worth sharing.
You will receive the text of one article. Produce:
- working_title: a short, neutral working title in your own words (do not reuse the headline).
- summary: in your own words, 1-3 paragraphs separated by blank lines, at the length given in the request.
- key_points: exactly 5 bullets with the most important takeaways for security defenders.
  Each is one sentence of at most about 30 words.

Rules:
- Write everything in your own words. Do not copy sentences or distinctive phrases from the
  article, and do not quote it.
- Keep technical identifiers exact: CVE IDs, product names, versions, threat actor and malware names.
- Only state what the article supports; do not add outside facts.
Respond with the JSON object only."""

# JSON outputs (output_config.format) guarantee the response matches this schema.
# The exact bullet count is enforced by validate(), not the schema.
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "working_title": {"type": "string"},
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["working_title", "summary", "key_points"],
    "additionalProperties": False,
}


class BriefError(Exception):
    """An expected failure with a message meant for the user."""


# ---------------------------------------------------------------- fetch + extract

SAVE_PAGE_HINT = ("Save the page from your browser (Ctrl+S / Cmd+S, 'Webpage, HTML only') and run "
                  "again with --html-file. See README troubleshooting.")


def fetch_html(url: str) -> str:
    resp = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=FETCH_TIMEOUT)
            break
        except requests.Timeout as exc:
            if attempt < FETCH_ATTEMPTS:
                print(f"[fetch] timed out, retrying ({attempt}/{FETCH_ATTEMPTS - 1})...", file=sys.stderr)
                continue
            raise BriefError(f"The site did not respond in time ({url}). It is probably blocking "
                             f"automated requests. {SAVE_PAGE_HINT}") from exc
        except requests.ConnectionError as exc:
            raise BriefError(f"Could not connect to the site ({url}). Check the URL and your internet "
                             f"connection. Details: {exc}") from exc
        except requests.RequestException as exc:
            raise BriefError(f"Could not fetch {url}: {exc}") from exc
    if resp.status_code == 429 or resp.status_code in (401, 402, 403):
        raise BriefError(f"The site refused the request (HTTP {resp.status_code}); it may be paywalled "
                         f"or blocking automated requests. {SAVE_PAGE_HINT}")
    if resp.status_code >= 400:
        raise BriefError(f"Fetching {url} failed with HTTP {resp.status_code}.")
    return resp.text


def _jsonld_article_body(raw_html: str) -> str:
    """Return the longest articleBody found in the page's JSON-LD metadata, if any."""
    best = ""

    def walk(node):
        nonlocal best
        if isinstance(node, dict):
            body = node.get("articleBody")
            if isinstance(body, str) and len(body) > len(best):
                best = body
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw_html,
                            flags=re.S | re.I):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return html.unescape(re.sub(r"<[^>]+>", " ", best)).strip()


def _check_length(article: dict) -> dict:
    words = len(article["text"].split())
    if words < MIN_ARTICLE_WORDS:
        raise BriefError("Could not find enough article text (it may need JavaScript or be behind a "
                         "paywall). Copy the article text into a file and use --text-file instead.")
    if words < SHORT_ARTICLE_WORDS:
        print(f"[warning] Only {words} words of article text were found. If the article is longer, "
              "part of it was missed: copy the text into a file and use --text-file.", file=sys.stderr)
    article["text"] = article["text"][:MAX_ARTICLE_CHARS]
    return article


def extract_article(raw_html: str, url: str) -> dict:
    """Extract the article text, trying several methods and keeping the longest result."""
    candidates = [
        trafilatura.extract(raw_html, url=url, include_comments=False, include_tables=True,
                            favor_precision=True),
        trafilatura.extract(raw_html, url=url, include_comments=False, include_tables=True,
                            favor_recall=True),
        _jsonld_article_body(raw_html),
    ]
    text = max((c for c in candidates if c), key=lambda c: len(c.split()), default="")
    meta = trafilatura.extract_metadata(raw_html, default_url=url)
    return _check_length({
        "url": url,
        "title": (meta.title if meta and meta.title else url).strip(),
        "text": text,
    })


def article_from_text(raw_text: str, url: str, title: str | None = None) -> dict:
    """Build an article from pasted plain text. The first line is the headline unless --title is given."""
    lines = [line.strip() for line in raw_text.strip().splitlines()]
    if not title and lines:
        title, lines = lines[0], lines[1:]
    return _check_length({"url": url, "title": title or url, "text": "\n".join(lines).strip()})


def summary_range(article: dict) -> tuple[int, int]:
    """Target summary length in words: shorter for short articles."""
    return (50, 150) if len(article["text"].split()) < SHORT_ARTICLE_WORDS else (150, 250)


# ---------------------------------------------------------------- validation

def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", s.lower())


def copied_phrases(output_text: str, source_text: str, n: int = COPY_NGRAM) -> list[str]:
    """Return word runs of length n that appear in both the output and the source."""
    src = _words(source_text)
    source_grams = {tuple(src[i:i + n]) for i in range(len(src) - n + 1)}
    out = _words(output_text)
    hits: list[str] = []
    for i in range(len(out) - n + 1):
        gram = tuple(out[i:i + n])
        if gram in source_grams:
            phrase = " ".join(gram)
            if phrase not in hits:
                hits.append(phrase)
    return hits


def validate(result: dict, article: dict) -> list[str]:
    problems = []
    points = [p.strip() for p in result.get("key_points", []) if p and p.strip()]
    if len(points) != 5:
        problems.append(f"Provide exactly 5 key points (got {len(points)}).")
    summary = result.get("summary", "").strip()
    word_count = len(summary.split())
    lo, hi = summary_range(article)
    if not int(lo * 0.7) <= word_count <= int(hi * 1.2):
        problems.append(f"Summary should be {lo}-{hi} words (got {word_count}).")
    if not result.get("working_title", "").strip():
        problems.append("Provide a working title.")
    all_text = " ".join([result.get("working_title", ""), summary, *points])
    copied = copied_phrases(all_text, article["text"])
    if copied:
        sample = "; ".join(f'"{c}"' for c in copied[:5])
        problems.append(f"These phrases are copied from the article; reword them: {sample}")
    return problems


# ---------------------------------------------------------------- Claude

def call_claude(client, model: str, article: dict, feedback: list[str] | None = None) -> dict:
    import anthropic

    lo, hi = summary_range(article)
    prompt = (f"Write the summary in {lo}-{hi} words.\n\n"
              f"Article title: {article['title']}\nURL: {article['url']}\n\n"
              f"<article>\n{article['text']}\n</article>")
    if feedback:
        prompt += ("\n\nYour previous attempt had these problems. Fix all of them:\n- "
                   + "\n- ".join(feedback))
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": SUMMARY_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError as exc:
        raise BriefError("The Claude API rejected the key (HTTP 401). Check ANTHROPIC_API_KEY.") from exc
    except anthropic.NotFoundError as exc:
        raise BriefError(f"Model '{model}' was not found. Check CLAUDE_MODEL in .env, or remove it to "
                         f"use the default ({DEFAULT_MODEL}).") from exc
    except anthropic.RateLimitError as exc:
        raise BriefError("The Claude API rate limit was reached, or the account is out of credit. "
                         "Wait a minute and try again, or check billing at platform.claude.com.") from exc
    except anthropic.APIStatusError as exc:
        raise BriefError(f"The Claude API returned an error (HTTP {exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise BriefError(f"Could not reach the Claude API. Check your internet connection. ({exc})") from exc

    if resp.stop_reason == "refusal":
        raise BriefError("Claude declined to summarize this article.")
    if resp.stop_reason == "max_tokens":
        raise BriefError("Claude's response was cut off before it finished. Try again.")
    text = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return json.loads(text)
    except ValueError as exc:
        raise BriefError("Claude did not return a valid structured summary.") from exc


def summarize(client, model: str, article: dict) -> dict:
    feedback = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = call_claude(client, model, article, feedback)
        feedback = validate(result, article)
        if not feedback:
            result["key_points"] = [p.strip() for p in result["key_points"]]
            return result
        print(f"[attempt {attempt}] output needs fixing: {feedback}", file=sys.stderr)
    raise BriefError("Summary still failed checks after a retry: " + " | ".join(feedback))


# ---------------------------------------------------------------- WordPress

def build_post_content(result: dict, article: dict) -> str:
    """Gutenberg block markup: summary paragraphs, Key Points list, Read more link."""
    esc = html.escape
    blocks = []
    for para in re.split(r"\n\s*\n", result["summary"].strip()):
        para = " ".join(para.split())
        if para:
            blocks.append(f"<!-- wp:paragraph -->\n<p>{esc(para)}</p>\n<!-- /wp:paragraph -->")
    blocks.append('<!-- wp:heading -->\n<h2 class="wp-block-heading">Key Points</h2>\n<!-- /wp:heading -->')
    items = "\n".join(f"<!-- wp:list-item -->\n<li>{esc(p)}</li>\n<!-- /wp:list-item -->"
                      for p in result["key_points"])
    blocks.append(f'<!-- wp:list -->\n<ul class="wp-block-list">\n{items}\n</ul>\n<!-- /wp:list -->')
    link = (f'<a href="{esc(article["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{esc(article["title"])}</a>')
    blocks.append(f"<!-- wp:paragraph -->\n<p><strong>Read more:</strong> {link}</p>\n<!-- /wp:paragraph -->")
    return "\n\n".join(blocks)


def create_wp_draft(wp_url: str, user: str, app_password: str, title: str, content: str,
                    category_id: str | None = None) -> tuple[int, str]:
    base = wp_url.rstrip("/")
    payload = {"title": title, "content": content, "status": "draft"}
    if category_id:
        payload["categories"] = [int(category_id)]
    auth = (user, app_password.replace(" ", ""))
    endpoints = [f"{base}/wp-json/wp/v2/posts", f"{base}/?rest_route=/wp/v2/posts"]
    resp = None
    for endpoint in endpoints:  # second form works when pretty permalinks are off
        try:
            resp = requests.post(endpoint, auth=auth, json=payload, timeout=30)
        except requests.RequestException as exc:
            raise BriefError(f"Could not reach WordPress at {base}: {exc}") from exc
        if resp.status_code != 404:
            break
    if resp.status_code == 401:
        raise BriefError("WordPress rejected the login (HTTP 401). Check WP_USER and WP_APP_PASSWORD; "
                         "see README troubleshooting if the credentials are correct.")
    if resp.status_code == 403:
        raise BriefError("WordPress refused to create the post (HTTP 403). Make sure WP_USER has at "
                         "least the Contributor role, and that no security plugin is blocking the REST API.")
    if resp.status_code >= 400:
        raise BriefError(f"WordPress returned HTTP {resp.status_code}: {resp.text[:300]}")
    post_id = resp.json()["id"]
    return post_id, f"{base}/wp-admin/post.php?post={post_id}&action=edit"


# ---------------------------------------------------------------- CLI

def read_local_file(path: str, option: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        raise BriefError(f"Could not read {option} {path}: {exc.strerror}. Check the file name and, "
                         "with Docker, that its folder is mounted at /data.") from exc


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise BriefError(f"Missing setting {name}. Add it to your .env file (see .env.example).")
    return value


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Summarize an article and save it as a WordPress draft.")
    parser.add_argument("url", help="URL of the article")
    parser.add_argument("--dry-run", action="store_true", help="print the summary; do not post to WordPress")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--html-file", help="use a saved copy of the page instead of fetching it")
    source.add_argument("--text-file", help="use the article text copied into a plain-text file "
                        "(first line = headline)")
    parser.add_argument("--title", help="headline to use with --text-file")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)

    try:
        from anthropic import Anthropic
        api_key = require_env("ANTHROPIC_API_KEY")
        if not args.dry_run:  # fail fast before spending an API call
            wp = {k: require_env(k) for k in ("WP_URL", "WP_USER", "WP_APP_PASSWORD")}

        if args.text_file:
            article = article_from_text(read_local_file(args.text_file, "--text-file"), args.url, args.title)
        elif args.html_file:
            article = extract_article(read_local_file(args.html_file, "--html-file"), args.url)
        else:
            article = extract_article(fetch_html(args.url), args.url)
        print(f"Fetched: {article['title']} ({len(article['text'].split())} words)", file=sys.stderr)

        model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        result = summarize(Anthropic(api_key=api_key), model, article)

        if args.json:
            print(json.dumps({"source": {"url": article["url"], "title": article["title"]}, **result}, indent=2))
        else:
            print(f"\n{result['working_title']}\n\n{result['summary']}\n\nKey Points")
            for p in result["key_points"]:
                print(f"  • {p}")
            print(f"\nRead more: {article['title']} <{article['url']}>")

        if not args.dry_run:
            content = build_post_content(result, article)
            post_id, edit_link = create_wp_draft(wp["WP_URL"], wp["WP_USER"], wp["WP_APP_PASSWORD"],
                                                 result["working_title"], content,
                                                 os.getenv("WP_CATEGORY_ID") or None)
            print(f"\nDraft created (post {post_id}): {edit_link}")
        return 0
    except BriefError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
