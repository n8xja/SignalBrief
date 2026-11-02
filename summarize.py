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

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 SignalBrief/1.0"
)
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_ARTICLE_CHARS = 60_000   # keeps very long pages within a sensible token budget
MIN_ARTICLE_WORDS = 100      # below this, extraction probably failed (paywall, JS-only page)
COPY_NGRAM = 8               # any 8-word run shared with the source counts as copied text
MAX_ATTEMPTS = 2             # first try + one retry with feedback

SYSTEM_PROMPT = """You are an analyst helping a cybersecurity threat-intelligence writer curate articles worth sharing.
You will receive the text of one article. Produce:
- working_title: a short, neutral working title in your own words (do not reuse the headline).
- summary: 150-250 words in 1-3 paragraphs, in your own words.
- key_points: exactly 5 bullets with the most important takeaways for security defenders.
  Each is one sentence of at most about 30 words.

Rules:
- Write everything in your own words. Do not copy sentences or distinctive phrases from the
  article, and do not quote it.
- Keep technical identifiers exact: CVE IDs, product names, versions, threat actor and malware names.
- Only state what the article supports; do not add outside facts.
Return the result by calling the save_summary tool."""

SUMMARY_TOOL = {
    "name": "save_summary",
    "description": "Save the working title, summary and five key points for the article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "working_title": {"type": "string"},
            "summary": {"type": "string", "description": "150-250 words, paragraphs separated by blank lines"},
            "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 5, "maxItems": 5},
        },
        "required": ["working_title", "summary", "key_points"],
    },
}


class BriefError(Exception):
    """An expected failure with a message meant for the user."""


# ---------------------------------------------------------------- fetch + extract

def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    except requests.RequestException as exc:
        raise BriefError(f"Could not fetch {url}: {exc}") from exc
    if resp.status_code in (401, 402, 403):
        raise BriefError(f"The site refused the request (HTTP {resp.status_code}); it may be paywalled "
                            "or blocking scripts. Save the page from your browser and use --html-file.")
    if resp.status_code >= 400:
        raise BriefError(f"Fetching {url} failed with HTTP {resp.status_code}.")
    return resp.text


def extract_article(raw_html: str, url: str) -> dict:
    text = trafilatura.extract(raw_html, url=url, include_comments=False,
                               include_tables=True, favor_precision=True)
    meta = trafilatura.extract_metadata(raw_html, default_url=url)
    if not text or len(text.split()) < MIN_ARTICLE_WORDS:
        raise BriefError("Could not find enough article text on the page (it may need JavaScript "
                            "or be behind a paywall). Save the page and use --html-file.")
    return {
        "url": url,
        "title": (meta.title if meta and meta.title else url).strip(),
        "text": text[:MAX_ARTICLE_CHARS],
    }


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
    if not 100 <= word_count <= 300:
        problems.append(f"Summary should be 150-250 words (got {word_count}).")
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
    prompt = (f"Article title: {article['title']}\nURL: {article['url']}\n\n"
              f"<article>\n{article['text']}\n</article>")
    if feedback:
        prompt += ("\n\nYour previous attempt had these problems. Fix all of them:\n- "
                   + "\n- ".join(feedback))
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[SUMMARY_TOOL],
        tool_choice={"type": "tool", "name": "save_summary"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise BriefError("Claude did not return a structured summary.")


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
    parser.add_argument("--html-file", help="use a saved copy of the page instead of fetching it")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)

    try:
        from anthropic import Anthropic
        api_key = require_env("ANTHROPIC_API_KEY")
        if not args.dry_run:  # fail fast before spending an API call
            wp = {k: require_env(k) for k in ("WP_URL", "WP_USER", "WP_APP_PASSWORD")}

        if args.html_file:
            try:
                with open(args.html_file, encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
            except OSError as exc:
                raise BriefError(f"Could not read --html-file {args.html_file}: {exc.strerror}. "
                                    "Check the file name and, with Docker, that its folder is "
                                    "mounted at /data.") from exc
        else:
            raw = fetch_html(args.url)
        article = extract_article(raw, args.url)
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
