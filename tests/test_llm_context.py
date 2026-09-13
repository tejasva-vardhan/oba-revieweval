import json
from pathlib import Path

from oba_revieweval.models.context import excerpt_window, load_pr_bundle, parse_new_hunks
from oba_revieweval.models.prompt import assert_no_review_leak, build_user_message


def test_parse_new_hunks():
    diff = """diff --git a/old.go b/new.go
index 111..222 100644
--- a/old.go
+++ b/new.go
@@ -10,3 +12,4 @@ func F() {
+  x
"""
    hunks = parse_new_hunks(diff)
    assert hunks["new.go"] == [(12, 4)]


def test_excerpt_window_caps_at_200():
    hunks = [(1, 500)]
    window = excerpt_window(hunks, file_len=800, cap=200)
    assert window is not None
    lo, hi = window
    assert hi - lo + 1 <= 200


def test_load_pr_bundle_does_not_read_comments(tmp_path: Path):
    raw = tmp_path / "1404"
    raw.mkdir()
    (raw / "metadata.json").write_text(
        json.dumps({"pr_number": 1404, "merge_sha": "abc", "title": "title"}),
        encoding="utf-8",
    )
    (raw / "diff.patch").write_text("diff --git a/a.go b/a.go\n", encoding="utf-8")
    (raw / "files.json").write_text("[]", encoding="utf-8")
    (raw / "comments.json").write_text(
        '{"issue_comments":[{"body":"CANARY_REVIEW_TEXT_SHOULD_NOT_APPEAR"}]}',
        encoding="utf-8",
    )
    bundle = load_pr_bundle(raw)
    dumped = json.dumps(bundle)
    assert "CANARY_REVIEW_TEXT_SHOULD_NOT_APPEAR" not in dumped
    message = build_user_message(title=bundle["metadata"]["title"], diff=bundle["diff"], excerpts=[])
    assert "CANARY_REVIEW_TEXT_SHOULD_NOT_APPEAR" not in message
    assert "1. PR title" in message
    assert "2. Unified diff" in message


def test_review_leak_helper_finds_long_snippets():
    hits = assert_no_review_leak("hello UNIQUE_FORBIDDEN_SNIPPET_123456", ["UNIQUE_FORBIDDEN_SNIPPET_123456"])
    assert hits
    assert assert_no_review_leak("hello", ["UNIQUE_FORBIDDEN_SNIPPET_123456"]) == []
