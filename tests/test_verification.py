import csv
from pathlib import Path

from oba_revieweval.dataset.actors import is_forbidden_gold_author
from oba_revieweval.dataset.extract import extract_rows

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "candidates" / "pr_candidates.csv"
VERIFICATION = ROOT / "data" / "candidates" / "pr_verification.csv"
ADDITIONAL = ROOT / "data" / "candidates" / "additional_considered.csv"
RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def test_verification_covers_original_thirty_only():
    candidates = [int(row["pr_id"]) for row in _rows(CANDIDATES)]
    verified = [int(row["pr_number"]) for row in _rows(VERIFICATION)]
    assert candidates == verified
    assert len(verified) == 30
    assert len(set(verified)) == 30
    assert 457 not in verified


def test_original_exclusions_are_documented():
    by_id = {int(row["pr_number"]): row for row in _rows(VERIFICATION)}
    assert _truthy(by_id[1374]["eligible_for_primary_gold"]) is False
    assert "not_meaningful" in by_id[1374]["exclusion_reason"]
    assert _truthy(by_id[1365]["eligible_for_primary_gold"]) is False
    assert _truthy(by_id[1284]["eligible_for_primary_gold"]) is False
    assert "not_meaningful" in by_id[1284]["exclusion_reason"]
    assert _truthy(by_id[1378]["eligible_for_primary_gold"]) is False
    assert _truthy(by_id[702]["eligible_for_primary_gold"]) is True
    assert "aaronbrethorst" in by_id[702]["independent_human_logins"]


def test_additional_accepts_are_not_forced_into_candidates():
    candidates = {int(row["pr_id"]) for row in _rows(CANDIDATES)}
    accepted = [
        int(row["pr_number"])
        for row in _rows(ADDITIONAL)
        if row["decision"] == "accepted_additional"
    ]
    assert accepted
    assert 457 in accepted
    assert candidates.isdisjoint(accepted)


def test_recommended_corpus_matches_eligible_plus_additional():
    original_eligible = {
        int(row["pr_number"])
        for row in _rows(VERIFICATION)
        if _truthy(row["eligible_for_primary_gold"])
    }
    additional = {
        int(row["pr_number"])
        for row in _rows(ADDITIONAL)
        if row["decision"] == "accepted_additional"
    }
    recommended = {int(row["pr_number"]) for row in _rows(RECOMMENDED)}
    assert recommended == original_eligible | additional
    assert len(recommended) == len(original_eligible) + len(additional)


def test_exported_pr_702_has_sanitized_files_and_partitions():
    export_dir = ROOT / "data" / "raw" / "prs" / "702"
    extract_dir = ROOT / "data" / "extracted" / "prs" / "702"
    if not export_dir.is_dir():
        return
    for name in ("metadata.json", "diff.patch", "files.json", "reviews.json", "comments.json"):
        assert (export_dir / name).is_file(), name
    metadata = (export_dir / "metadata.json").read_text(encoding="utf-8")
    assert "Bearer" not in metadata
    assert "@" not in metadata
    human = _rows(extract_dir / "human_independent_unlabeled.csv")
    author = _rows(extract_dir / "author_comments.csv")
    assert human
    assert all(row["author_login"] != "tejasva-vardhan" for row in human)
    assert all(row["eligible_as_independent_gold_candidate"] == "true" for row in human)
    assert any(row["author_login"] == "tejasva-vardhan" for row in author)
    assert all(row["class"] == "" for row in human)
    assert all(row["in_reference_set"] == "false" for row in human)


def test_study_author_never_independent_gold_in_extraction():
    assert is_forbidden_gold_author("tejasva-vardhan")
    collected = {
        "pr_number": 702,
        "author": "tejasva-vardhan",
        "issue_comments": [
            {
                "login": "tejasva-vardhan",
                "user_type": "User",
                "body": "I noticed the OpenAPI conformance failures.",
            }
        ],
        "review_bodies": [
            {
                "login": "aaronbrethorst",
                "user_type": "User",
                "body": "Wrap BeginTx errors.",
            }
        ],
    }
    rows = extract_rows(collected)
    author_rows = [row for row in rows if row["author_login"] == "tejasva-vardhan"]
    assert author_rows
    assert all(row["eligible_as_independent_gold_candidate"] == "false" for row in author_rows)
    human = [row for row in rows if row["author_login"] == "aaronbrethorst"]
    assert human[0]["eligible_as_independent_gold_candidate"] == "true"
