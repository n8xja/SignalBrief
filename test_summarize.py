"""Offline tests: no network, Claude and WordPress are stubbed."""
import json
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
    "bluf": ("A serious bug in Acme's VPN appliance, CVE-2026-12345, lets outsiders run code on it. "
             "Intruders began abusing it around the start of October. "
             "Teams running the appliance should update to v4.2.1 right away."),
    "key_points": ["Patch Acme VPN now.", "CVE-2026-12345 is critical.", "Exploited since October.",
                   "Look for web shells.", "Watch for lateral movement."],
}


def fake_client(*results):
    responses = [SimpleNamespace(stop_reason="end_turn",
                                 content=[SimpleNamespace(type="text", text=json.dumps(r))])
                 for r in results]
    client = mock.Mock()
    client.messages.create.side_effect = responses
    return client


def test_copied_phrases_detects_verbatim_run():
    out = "They said attackers have been exploiting the vulnerability since early October to deploy things."
    assert s.copied_phrases(out, ARTICLE_TEXT)


def test_copied_phrases_allows_paraphrase():
    assert s.copied_phrases(GOOD["bluf"], ARTICLE_TEXT) == []


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
    with pytest.raises(s.BriefError):
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


def wp_resp(status, body=None):
    return SimpleNamespace(status_code=status, text=json.dumps(body or {}), json=lambda: body or {})


def test_create_wp_draft_posts_draft_and_falls_back_on_404():
    with mock.patch.object(s.requests, "request", side_effect=[wp_resp(404), wp_resp(201, {"id": 42})]) as req:
        post_id, link = s.create_wp_draft("https://site.org/", "u", "ab cd", "T", "C", "7")
    assert post_id == 42
    assert link == "https://site.org/wp-admin/post.php?post=42&action=edit"
    assert req.call_args.args[0] == "POST"
    payload = req.call_args.kwargs["json"]
    assert payload["status"] == "draft" and payload["categories"] == [7]
    assert req.call_args.kwargs["auth"] == ("u", "abcd")
    assert "rest_route" in req.call_args.args[1]


@pytest.mark.parametrize("status,code,expected", [
    (401, "incorrect_password", "not your normal login password"),
    (401, "invalid_username", "username or password is wrong"),
    (401, "rest_cannot_create", "did not receive the login"),
    (401, "", "did not receive the login"),
    (401, "application_passwords_disabled", "turned off"),
    (403, "rest_cannot_create", "Contributor role"),
])
def test_wordpress_errors_are_diagnosed(status, code, expected):
    body = {"code": code, "message": "msg"} if code else {}
    with mock.patch.object(s.requests, "request", return_value=wp_resp(status, body)):
        with pytest.raises(s.BriefError, match=expected):
            s.create_wp_draft("https://site.org", "u", "p", "T", "C")


def test_check_wp_reports_user_and_role():
    me = {"username": "signalbrief", "roles": ["contributor"]}
    with mock.patch.object(s.requests, "request", return_value=wp_resp(200, me)) as req:
        line = s.check_wp("https://site.org", "signalbrief", "a b")
    assert "signalbrief" in line and "contributor" in line and "Drafts can be created" in line
    assert req.call_args.args[0] == "GET" and "/wp/v2/users/me" in req.call_args.args[1]


def test_check_wp_flags_subscriber():
    with mock.patch.object(s.requests, "request", return_value=wp_resp(200, {"username": "x", "roles": ["subscriber"]})):
        assert "needs Contributor" in s.check_wp("https://site.org", "x", "p")


def test_check_wp_cli_needs_no_url_or_claude_key(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for k, v in {"WP_URL": "https://site.org", "WP_USER": "u", "WP_APP_PASSWORD": "p"}.items():
        monkeypatch.setenv(k, v)
    with mock.patch.object(s.requests, "request", return_value=wp_resp(200, {"username": "u", "roles": ["author"]})):
        assert s.main(["--check-wp"]) == 0
    assert "Logged in to WordPress as 'u'" in capsys.readouterr().out


def test_missing_html_file_gives_clear_error(monkeypatch, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    code = s.main(["https://example.com/a", "--dry-run", "--html-file", "/nonexistent/page.html"])
    assert code == 1
    assert "Could not read --html-file" in capsys.readouterr().err


def test_extract_article_from_html():
    page = ("<html><head><title>Test Headline</title></head><body><nav>Menu Home About</nav>"
            f"<article><h1>Test Headline</h1><p>{ARTICLE_TEXT}</p></article>"
            "<footer>Copyright footer</footer></body></html>")
    art = s.extract_article(page, "https://example.com/t")
    assert art["title"] == "Test Headline"
    assert "CVE-2026-12345" in art["text"]
    assert "Menu Home About" not in art["text"]


def test_fetch_sends_browser_headers():
    ok = SimpleNamespace(status_code=200, text="<html></html>")
    with mock.patch.object(s.requests, "get", return_value=ok) as get:
        s.fetch_html("https://example.com/a")
    headers = get.call_args.kwargs["headers"]
    assert "Accept-Language" in headers and "Accept" in headers
    assert "Chrome/" in headers["User-Agent"]


def test_fetch_retries_timeout_then_succeeds():
    ok = SimpleNamespace(status_code=200, text="<html>ok</html>")
    with mock.patch.object(s.requests, "get", side_effect=[s.requests.Timeout("slow"), ok]) as get:
        assert s.fetch_html("https://example.com/a") == "<html>ok</html>"
    assert get.call_count == 2


def test_fetch_timeout_gives_html_file_hint():
    with mock.patch.object(s.requests, "get", side_effect=s.requests.Timeout("slow")):
        with pytest.raises(s.BriefError, match="--html-file"):
            s.fetch_html("https://example.com/a")


def test_request_uses_json_outputs_not_forced_tool():
    client = fake_client(GOOD)
    s.summarize(client, "m", ARTICLE)
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "tool_choice" not in kwargs and "tools" not in kwargs


def test_api_error_becomes_clean_message():
    import anthropic
    err = anthropic.NotFoundError("not found", body=None,
                                  response=mock.Mock(status_code=404, headers={}))
    client = mock.Mock()
    client.messages.create.side_effect = err
    with pytest.raises(s.BriefError, match="was not found"):
        s.summarize(client, "bad-model", ARTICLE)


def test_jsonld_article_body_used_when_longer():
    body = "Defenders should patch the gateway now. " * 80
    page = ("<html><head><title>T</title><script type='application/ld+json'>"
            + json.dumps({"@type": "BlogPosting", "articleBody": body})
            + "</script></head><body><article><p>Short teaser paragraph only.</p></article></body></html>")
    art = s.extract_article(page, "https://example.com/t")
    assert len(art["text"].split()) > 400


def test_text_file_first_line_is_title():
    art = s.article_from_text("My Headline\n\n" + ARTICLE_TEXT, "https://example.com/a")
    assert art["title"] == "My Headline"
    assert "CVE-2026-12345" in art["text"]


def test_text_file_title_override():
    art = s.article_from_text(ARTICLE_TEXT, "https://example.com/a", title="Given")
    assert art["title"] == "Given" and art["text"].startswith("Researchers")


def test_short_article_warns(capsys):
    s.article_from_text("T\n" + "word " * 200, "https://e.com")
    assert "Only 200 words" in capsys.readouterr().err


def test_bluf_with_four_sentences_is_rejected():
    bad = {**GOOD, "bluf": GOOD["bluf"] + " A fourth sentence adds more."}
    assert any("2 or 3 concise sentences" in p for p in s.validate(bad, ARTICLE))


def test_bluf_too_long_is_rejected():
    bad = {**GOOD, "bluf": "Defenders " + "really " * 100 + "should patch."}
    assert any("2 or 3 concise sentences" in p for p in s.validate(bad, ARTICLE))


def test_sentence_count_ignores_identifiers():
    assert s.count_sentences("Node.js patched c/dec/decode.c in v22.1.4. Patch now.") == 2


def test_post_has_bluf_heading_first():
    out = s.build_post_content(GOOD, ARTICLE)
    first, second = out.split("\n\n")[:2]
    assert "BLUF: Bottom Line Up Front" in first and "wp:heading" in first
    assert GOOD["bluf"].split(",")[0].replace("'", "&#x27;") in second


def test_default_brief_targets_business_leaders():
    prompt = s.build_system_prompt()
    assert "business leaders" in prompt and "defensive actions" in prompt


def test_custom_brief_is_used(monkeypatch):
    client = fake_client(GOOD)
    s.summarize(client, "m", ARTICLE, brief="Acme Weekly writes for hospital CIOs.")
    system = client.messages.create.call_args.kwargs["system"]
    assert "Acme Weekly writes for hospital CIOs." in system
    assert s.DEFAULT_EDITORIAL_BRIEF not in system


def test_blank_brief_falls_back_to_default():
    assert s.DEFAULT_EDITORIAL_BRIEF in s.build_system_prompt("   ")


def test_quoted_brief_from_docker_env_file_is_unquoted():
    prompt = s.build_system_prompt('"Acme writes for CFOs."')
    assert "Acme writes for CFOs." in prompt and '"Acme writes for CFOs."' not in prompt
