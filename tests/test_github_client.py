import json

import pytest

from oba_revieweval.dataset.collect import collect_pull_request, fetch_diff
from oba_revieweval.dataset.github import GitHubAPIError, GitHubClient, load_token, parse_json_body
from tests.fixtures.github.pr_sample import FakeOpener, ROUTES


def test_load_token_from_env_only():
    assert load_token(env={"GITHUB_TOKEN": "secret-value"}) == "secret-value"
    assert load_token(env={}) is None


def test_parse_json_rejects_empty_and_malformed():
    with pytest.raises(GitHubAPIError, match="empty"):
        parse_json_body("  ", context="x")
    with pytest.raises(GitHubAPIError, match="malformed"):
        parse_json_body("{not-json", context="x")


def test_collect_pull_request_extracts_author_and_reviews():
    client = GitHubClient(token=None, opener=FakeOpener())
    collected = collect_pull_request(client, 702)
    assert collected["author"] == "tejasva-vardhan"
    assert collected["merged"] is True
    assert collected["merge_sha"] == "abc123def456"
    assert collected["changed_files"] == ["internal/gtfs/import.go"]
    assert collected["reviews"][0]["login"] == "aaronbrethorst"
    assert collected["issue_comments"][0]["login"] == "tejasva-vardhan"


def test_missing_review_surface_is_empty_list():
    routes = dict(ROUTES)
    routes["/repos/OneBusAway/maglev/pulls/702/reviews"] = []
    routes["/repos/OneBusAway/maglev/pulls/702/comments"] = []
    routes["/repos/OneBusAway/maglev/issues/702/comments"] = []
    client = GitHubClient(token=None, opener=FakeOpener(routes))
    collected = collect_pull_request(client, 702)
    assert collected["reviews"] == []
    assert collected["inline_comments"] == []
    assert collected["issue_comments"] == []


def test_malformed_pr_payload_raises():
    routes = dict(ROUTES)
    routes["/repos/OneBusAway/maglev/pulls/702"] = ["not", "an", "object"]
    client = GitHubClient(token=None, opener=FakeOpener(routes))
    with pytest.raises(GitHubAPIError, match="expected object"):
        collect_pull_request(client, 702)


def test_malformed_user_type_raises():
    routes = dict(ROUTES)
    pr = json.loads(json.dumps(ROUTES["/repos/OneBusAway/maglev/pulls/702"]))
    pr["user"] = {"login": "x", "type": 1}
    routes["/repos/OneBusAway/maglev/pulls/702"] = pr
    client = GitHubClient(token=None, opener=FakeOpener(routes))
    with pytest.raises(GitHubAPIError, match="user.type"):
        collect_pull_request(client, 702)


def test_cache_only_falls_back_between_paginated_and_plain_keys(tmp_path):
    from oba_revieweval.dataset.github import cache_path_for

    url = "https://api.github.com/repos/OneBusAway/maglev/pulls/702/reviews"
    paginated = cache_path_for(tmp_path, url + "?per_page=100&page=1")
    paginated.parent.mkdir(parents=True, exist_ok=True)
    paginated.write_text('[{"id": 1, "user": {"login": "aaronbrethorst"}}]', encoding="utf-8")
    client = GitHubClient(token=None, cache_dir=tmp_path, cache_only=True)
    payload = client.request_json(url)
    assert payload[0]["id"] == 1


def test_fetch_diff_uses_diff_accept():
    opener = FakeOpener()
    client = GitHubClient(token=None, opener=opener)
    text = fetch_diff(client, 702)
    assert text.startswith("diff --git")
