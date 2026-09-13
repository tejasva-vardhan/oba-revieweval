from pathlib import Path

from oba_revieweval.annotation.human_review import (
    HUMAN_REVIEW_FIELDS,
    annotation_summary,
    build_human_review_rows,
    load_human_review_csv,
    validate_human_review,
)
from oba_revieweval.annotation.schema import HumanComment, in_reference_set
from oba_revieweval.dataset.corpus import load_recommended

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "human_review.csv"


def test_review_body_is_a_valid_comment_source():
    comment = HumanComment(
        pr_id=271,
        comment_id=3736623463,
        source="review_body",
        author_login="aaronbrethorst",
        is_pr_author=False,
        text="Approved.",
        class_="process_other",
        atomic_issue_id="H-271-3736623463-1",
        in_reference_set=False,
    )
    assert comment.source == "review_body"


def test_pr_author_is_never_reference_even_if_not_study_author():
    assert in_reference_set("defect", "aaronbrethorst", is_pr_author=True) is False


def test_out_of_scope_observation_is_not_reference():
    assert (
        in_reference_set(
            "design",
            "aaronbrethorst",
            is_pr_author=False,
            about_the_change=False,
        )
        is False
    )


def test_human_review_csv_covers_the_recommended_corpus():
    rows = load_human_review_csv(CSV_PATH)
    recommended = load_recommended(ROOT / "data" / "candidates" / "recommended_corpus.csv")
    assert list(rows[0].keys()) == list(HUMAN_REVIEW_FIELDS)
    assert {row["pr_number"] for row in rows} == {row["pr_number"] for row in recommended}
    assert not validate_human_review(rows)
    summary = annotation_summary(rows)
    assert summary["pr_count"] == 33
    assert summary["independent_comment_count"] == 198
    assert summary["ambiguous_count"] == 2
    assert summary["class_counts"]["process_other"] >= 1
    assert "question" not in summary["class_counts"]
    assert summary["primary_reference_set_count"] == 75
    gold = [row for row in rows if row["in_reference_set"] == "true"]
    assert all(row["class"] in {"defect", "design"} for row in gold)
    assert all(row["annotation_status"] != "ambiguous" for row in gold)
    assert all(row["reviewer"].lower() != "tejasva-vardhan" for row in rows)
    assert all(row["is_pr_author"] == "false" for row in rows)


def test_rebuild_matches_committed_table():
    rebuilt = build_human_review_rows()
    committed = load_human_review_csv(CSV_PATH)
    assert [(row["atomic_issue_id"], row["class"], row["in_reference_set"]) for row in rebuilt] == [
        (row["atomic_issue_id"], row["class"], row["in_reference_set"]) for row in committed
    ]


def test_extract_csvs_remain_unlabeled():
    for path in (ROOT / "data" / "extracted" / "prs").glob("*/human_independent_unlabeled.csv"):
        text = path.read_text(encoding="utf-8")
        header = text.splitlines()[0]
        assert header.endswith("class,atomic_issue_id,in_reference_set")
    rows = load_human_review_csv(CSV_PATH)
    assert all(row["original_comment"] is not None for row in rows)
    assert any(row["normalized_issue"] != row["original_comment"] for row in rows)
