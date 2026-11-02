"""Offline tests: no network, Claude and WordPress are stubbed."""
from types import SimpleNamespace
from unittest import mock

import pytest

import summarize as s

ARTICLE_TEXT = (
    "Researchers disclosed a critical remote code execution flaw tracked as CVE-2026-12345 in the "
    "Acme VPN gateway. Attackers have been exploiting the vulnerability since early October to deploy "
    "a web shell and move laterally into internal networks. "
) * 10
ARTICLE = {"url": "https://example.com/a?x=1&y=2", "title": "Acme VPN <flaw>", "text": ARTICLE_TEXT}

GOOD = {
    "working_title": "Acme VPN Gateway Bug Under Active Attack",
    "summary": ("A serious bug in Acme's VPN appliance, CVE-2026-12345, lets outsiders run code on it. "
                "Intruders began abusing it around the start of October. " * 6).strip(),
    "key_points": ["Patch Acme VPN now.", "CVE-2026-12345 is critical.", "Exploited since October.",
                   "Look for web shells.", "Watch for lateral movement."],
}


def fake_client(*results):
    responses = [SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=r)]) for r in results]
    client = mock.Mock()
    client.messages.create.side_effect = responses
    return client


def test_copied_phrases_detects_verbatim_run():
    out = "They said attackers have been exploiting the vulnerability since early October to deploy things."
    assert s.copied_phrases(out, ARTICLE_TEXT)


def test_copied_phrases_allows_paraphrase():
    assert s.copied_phrases(GOOD["summary"], ARTICLE_TEXT) == []


def test_validate_good_result():
    assert s.validate(GOOD, ARTICLE) == []


def test_validate_flags_wrong_bullet_count():
    bad = {**GOOD, "key_points": GOOD["key_points"][:4]}
    assert any("exactly 5" in p for p in s.validate(bad, ARTICLE))


def test_summarize_retries_then_succeeds():
    bad = {**GOOD, "key_points": GOOD["key_points"][:3]}
    client = fake_client(bad, GOOD)
    assert s.summarize(client, "m", ARTICLE)["working_title"] == GOOD["working_title"]
    second_prompt = client.messages.create.call_args_list[1].kwargs["messages"][0]["content"]
    assert "exactly 5 key points" in second_prompt


def test_summarize_gives_up_after_retry():
    bad = {**GOOD, "key_points": []}
    with pytest.raises(s.DispatchError):
        s.summarize(fake_client(bad, bad), "m", ARTICLE)


def test_post_content_structure_and_escaping():
    html_out = s.build_post_content(GOOD, ARTICLE)
    assert html_out.count("<li>") == 5
    assert "Key Points" in html_out
    assert html_out.rstrip().endswith("<!-- /wp:paragraph -->")
    last_block = html_out.split("\n\n")[-1]
    assert "Read more:" in last_block
    assert 'href="https://example.com/a?x=1&amp;y=2"' in last_block
    assert "Acme VPN &lt;flaw&gt;" in last_block


def test_create_wp_draft_posts_draft_and_falls_back_on_404():
    not_found = SimpleNamespace(status_code=404, text="")
    created = SimpleNamespace(status_code=201, text="", json=lambda: {"id": 42})
    with mock.patch.object(s.requests, "post", side_effect=[not_found, created]) as post:
        post_id, link = s.create_wp_draft("https://site.org/", "u", "ab cd", "T", "C", "7")
    assert post_id == 42
    assert link == "https://site.org/wp-admin/post.php?post=42&action=edit"
    payload = post.call_args.kwargs["json"]
    assert payload["status"] == "draft" and payload["categories"] == [7]
    assert post.call_args.kwargs["auth"] == ("u", "abcd")
    assert "rest_route" in post.call_args.args[0]


def test_create_wp_draft_auth_error():
    with mock.patch.object(s.requests, "post", return_value=SimpleNamespace(status_code=401, text="")):
        with pytest.raises(s.DispatchError, match="rejected the login"):
            s.create_wp_draft("https://site.org", "u", "p", "T", "C")


def test_extract_article_from_html():
    page = ("<html><head><title>Test Headline</title></head><body><nav>Menu Home About</nav>"
            f"<article><h1>Test Headline</h1><p>{ARTICLE_TEXT}</p></article>"
            "<footer>Copyright footer</footer></body></html>")
    art = s.extract_article(page, "https://example.com/t")
    assert art["title"] == "Test Headline"
    assert "CVE-2026-12345" in art["text"]
    assert "Menu Home About" not in art["text"]
