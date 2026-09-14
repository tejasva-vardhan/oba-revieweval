import csv
import json
from pathlib import Path

from oba_revieweval.dataset.corpus import (
    MANIFEST_FIELDS,
    corpus_is_complete,
    validate_pr_export,
    validate_recommended_corpus,
)
from oba_revieweval.dataset.extract import extract_rows, partition_rows


def test_process_only_is_partitioned_from_meaningful():
    collected = {
        "pr_number": 1,
        "author": "other",
        "review_bodies": [
            {"id": 1, "login": "reviewer", "user_type": "User", "body": "LGTM", "inline": False},
            {
                "id": 2,
                "login": "reviewer",
                "user_type": "User",
                "body": "This will drop agency-scoped stops after midnight.",
                "inline": False,
            },
        ],
    }
    groups = partition_rows(extract_rows(collected))
    assert [row["comment_id"] for row in groups["process_only"]] == ["1"]
    assert [row["comment_id"] for row in groups["human_meaningful"]] == ["2"]
    assert {row["comment_id"] for row in groups["human"]} == {"1", "2"}


def test_validate_pr_export_fails_when_incomplete(tmp_path: Path):
    dest = tmp_path / "raw" / "1"
    extract = tmp_path / "extract" / "1"
    dest.mkdir(parents=True)
    extract.mkdir(parents=True)
    errors = validate_pr_export(dest, extract, expected_sha="abc", author="someone")
    assert any(item.startswith("missing_raw:") for item in errors)


def test_validate_pr_export_catches_author_in_gold(tmp_path: Path):
    dest = tmp_path / "9"
    extract = tmp_path / "e9"
    dest.mkdir(parents=True)
    extract.mkdir(parents=True)
    (dest / "metadata.json").write_text(
        json.dumps(
            {
                "merge_sha": "abc",
                "changed_file_count": 1,
                "diff_anchored_to_merge_sha": True,
            }
        ),
        encoding="utf-8",
    )
    (dest / "files.json").write_text(
        json.dumps([{"filename": "a.go", "status": "modified", "binary": False}]),
        encoding="utf-8",
    )
    (dest / "github_files.json").write_text(
        json.dumps([{"filename": "a.go", "status": "modified"}]),
        encoding="utf-8",
    )
    (dest / "reviews.json").write_text("[]\n", encoding="utf-8")
    (dest / "comments.json").write_text(
        json.dumps({"issue_comments": [], "inline_comments": [], "review_bodies": []}),
        encoding="utf-8",
    )
    (dest / "diff.patch").write_text("diff --git a/a.go b/a.go\n", encoding="utf-8")
    header = (
        "pr_id,comment_id,source,author_login,actor_class,is_pr_author,"
        "is_study_author,eligible_as_independent_gold_candidate,is_process_only,"
        "text,path,class,atomic_issue_id,in_reference_set\n"
    )
    (extract / "all_comments_unlabeled.csv").write_text(header, encoding="utf-8")
    (extract / "human_independent_unlabeled.csv").write_text(
        header + "9,1,issue,someone,human,false,false,true,false,hi,, ,9-001,false\n",
        encoding="utf-8",
    )
    for name in (
        "human_meaningful_unlabeled.csv",
        "process_only.csv",
        "bot_comments.csv",
        "author_comments.csv",
    ):
        (extract / name).write_text(header, encoding="utf-8")
    (extract / "partition_summary.json").write_text("{}\n", encoding="utf-8")
    errors = validate_pr_export(dest, extract, expected_sha="abc", author="someone")
    assert "pr_author_in_human_gold" in errors


def test_corpus_is_complete_requires_thirty_three():
    assert corpus_is_complete([]) is False
    rows = [{"complete": True} for _ in range(32)]
    assert corpus_is_complete(rows) is False
    rows.append({"complete": True})
    assert corpus_is_complete(rows) is True
    rows[-1] = {"complete": False}
    assert corpus_is_complete(rows) is False


def test_recommended_export_is_complete():
    root = Path(__file__).resolve().parents[1]
    recommended_path = root / "data" / "candidates" / "recommended_corpus.csv"
    with recommended_path.open(encoding="utf-8", newline="") as handle:
        recommended = list(csv.DictReader(handle))
    results = validate_recommended_corpus(
        recommended,
        root / "data" / "raw" / "prs",
        root / "data" / "extracted" / "prs",
    )
    failed = [row for row in results if not row["complete"]]
    assert len(results) == 33
    assert failed == []
    assert corpus_is_complete(results)
    manifest = root / "data" / "raw" / "manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [field.strip() for field in rows[0].keys()] == MANIFEST_FIELDS or list(rows[0].keys()) == MANIFEST_FIELDS
    assert len(rows) == 33
    assert all(row["export_complete"].lower() == "true" for row in rows)
    assert all(row["diff_available"].lower() == "true" for row in rows)
