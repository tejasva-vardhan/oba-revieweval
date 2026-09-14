from pathlib import Path

from oba_revieweval.dataset.collect import files_from_unified_diff
from oba_revieweval.dataset.export import write_pr_export
from oba_revieweval.dataset.extract import extract_rows, partition_rows, write_extracted_csv


def test_files_from_unified_diff_handles_add_delete_rename():
    diff = """diff --git a/old.go b/new.go
similarity index 90%
rename from old.go
rename to new.go
diff --git a/gone.go b/gone.go
deleted file mode 100644
--- a/gone.go
+++ /dev/null
diff --git a/added.go b/added.go
new file mode 100644
--- /dev/null
+++ b/added.go
"""
    files = {item["filename"]: item for item in files_from_unified_diff(diff)}
    assert files["new.go"]["status"] == "renamed"
    assert files["new.go"]["previous_filename"] == "old.go"
    assert files["gone.go"]["status"] == "removed"
    assert files["added.go"]["status"] == "added"


def test_extract_partitions_human_bot_and_author(tmp_path: Path):
    collected = {
        "pr_number": 702,
        "author": "tejasva-vardhan",
        "issue_comments": [
            {
                "id": 1,
                "source": "issue",
                "login": "tejasva-vardhan",
                "user_type": "User",
                "body": "author note",
                "inline": False,
                "path": None,
            }
        ],
        "inline_comments": [
            {
                "id": 2,
                "source": "inline",
                "login": "aaronbrethorst",
                "user_type": "User",
                "body": "rollback path?",
                "inline": True,
                "path": "tx.go",
            }
        ],
        "review_bodies": [
            {
                "id": 3,
                "source": "review_body",
                "login": "coderabbitai[bot]",
                "user_type": "Bot",
                "body": "walkthrough",
                "inline": False,
                "path": None,
            }
        ],
    }
    rows = extract_rows(collected)
    groups = partition_rows(rows)
    assert [r["author_login"] for r in groups["human"]] == ["aaronbrethorst"]
    assert [r["author_login"] for r in groups["bot"]] == ["coderabbitai[bot]"]
    assert [r["author_login"] for r in groups["study_author"]] == ["tejasva-vardhan"]
    assert all(r["class"] == "" for r in rows)
    assert all(r["in_reference_set"] == "false" for r in rows)
    assert groups["human"][0]["eligible_as_independent_gold_candidate"] == "true"
    assert groups["study_author"][0]["eligible_as_independent_gold_candidate"] == "false"

    out = tmp_path / "human_review_unlabeled.csv"
    write_extracted_csv(out, rows)
    text = out.read_text(encoding="utf-8")
    assert "aaronbrethorst" in text
    assert "tejasva-vardhan" in text


def test_write_pr_export_omits_email_and_token(tmp_path: Path):
    collected = {
        "repo": "OneBusAway/maglev",
        "pr_number": 702,
        "title": "tx helper",
        "state": "closed",
        "merged": True,
        "merge_sha": "abc",
        "author": "tejasva-vardhan",
        "author_type": "User",
        "html_url": "https://github.com/OneBusAway/maglev/pull/702",
        "changed_files": ["a.go"],
        "changed_file_count": 1,
        "change_kind": "code",
        "review_count": 1,
        "files": [{"filename": "a.go", "status": "modified", "additions": 1, "deletions": 0}],
        "reviews": [{"id": 1, "login": "aaronbrethorst", "user_type": "User", "state": "COMMENTED", "body": "q", "submitted_at": "t"}],
        "issue_comments": [],
        "inline_comments": [],
        "review_bodies": [],
        "email": "should-not-be-copied@example.com",
    }
    dest = write_pr_export(tmp_path / "702", collected, diff_text="diff --git\n", collected_at="2026-09-14")
    metadata = (dest / "metadata.json").read_text(encoding="utf-8")
    assert "example.com" not in metadata
    assert "Bearer" not in metadata
    assert (dest / "diff.patch").read_text(encoding="utf-8").startswith("diff")
    assert (dest / "files.json").exists()
    assert (dest / "reviews.json").exists()
    assert (dest / "comments.json").exists()
