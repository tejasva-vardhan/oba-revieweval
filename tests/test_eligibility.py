from oba_revieweval.dataset.actors import classify_actor, is_forbidden_gold_author, is_meaningful_review_text
from oba_revieweval.dataset.collect import classify_change_kind
from oba_revieweval.dataset.eligibility import evaluate_eligibility


def _base(**overrides):
    data = {
        "repo": "OneBusAway/maglev",
        "pr_number": 1,
        "title": "example",
        "merged": True,
        "merge_sha": "sha",
        "author": "other-dev",
        "author_type": "User",
        "changed_files": ["api/handler.go"],
        "changed_file_count": 1,
        "change_kind": "code",
        "review_count": 1,
        "issue_comments": [],
        "inline_comments": [],
        "review_bodies": [],
    }
    data.update(overrides)
    return data


def test_study_author_never_independent_gold():
    assert is_forbidden_gold_author("tejasva-vardhan")
    collected = _base(
        author="tejasva-vardhan",
        issue_comments=[
            {
                "login": "tejasva-vardhan",
                "user_type": "User",
                "body": "This transaction helper looks correct to me.",
                "inline": False,
            }
        ],
    )
    result = evaluate_eligibility(collected, stratum="database")
    assert result["author_comments_present"] is True
    assert result["independent_human_review_present"] is False
    assert result["eligible_for_primary_gold"] is False


def test_study_author_comment_on_other_pr_is_not_gold():
    collected = _base(
        author="someone-else",
        issue_comments=[
            {
                "login": "tejasva-vardhan",
                "user_type": "User",
                "body": "I would not merge this as-is because the query can double-count stops.",
                "inline": False,
            }
        ],
    )
    result = evaluate_eligibility(collected)
    assert result["independent_human_review_present"] is False
    assert result["eligible_for_primary_gold"] is False


def test_coderabbit_only_is_excluded():
    collected = _base(
        issue_comments=[
            {
                "login": "coderabbitai[bot]",
                "user_type": "Bot",
                "body": "Actionable comments",
                "inline": False,
            }
        ]
    )
    result = evaluate_eligibility(collected)
    assert result["bot_review_present"] is True
    assert result["eligible_for_primary_gold"] is False
    assert "bot_only" in result["exclusion_reason"]


def test_independent_human_plus_bot_is_eligible():
    collected = _base(
        issue_comments=[
            {
                "login": "coderabbitai[bot]",
                "user_type": "Bot",
                "body": "Walkthrough",
                "inline": False,
            }
        ],
        inline_comments=[
            {
                "login": "aaronbrethorst",
                "user_type": "User",
                "body": "This will drop agency-scoped stops after midnight.",
                "inline": True,
                "path": "api/stops.go",
            }
        ],
    )
    result = evaluate_eligibility(collected, stratum="api_gtfs")
    assert result["eligible_for_primary_gold"] is True
    assert result["independent_human_review_present"] is True
    assert result["bot_review_present"] is True


def test_empty_approval_is_not_meaningful():
    collected = _base(
        review_bodies=[
            {
                "login": "reviewer",
                "user_type": "User",
                "body": "",
                "inline": False,
            }
        ]
    )
    result = evaluate_eligibility(collected)
    assert result["independent_human_review_present"] is False
    assert result["eligible_for_primary_gold"] is False


def test_merge_conflicts_only_is_not_meaningful():
    collected = _base(
        review_bodies=[
            {
                "login": "reviewer",
                "user_type": "User",
                "body": "merge conflicts",
                "inline": False,
            }
        ]
    )
    result = evaluate_eligibility(collected)
    assert result["eligible_for_primary_gold"] is False
    assert "not_meaningful" in result["exclusion_reason"]


def test_lgtm_only_is_not_meaningful():
    assert is_meaningful_review_text("LGTM") is False
    collected = _base(
        issue_comments=[
            {"login": "reviewer", "user_type": "User", "body": "LGTM", "inline": False}
        ]
    )
    result = evaluate_eligibility(collected)
    assert result["eligible_for_primary_gold"] is False
    assert "not_meaningful" in result["exclusion_reason"]


def test_docs_only_excluded_even_with_human():
    collected = _base(
        changed_files=["README.md"],
        change_kind=classify_change_kind(["README.md"]),
        issue_comments=[
            {
                "login": "reviewer",
                "user_type": "User",
                "body": "Please mention the new endpoint.",
                "inline": False,
            }
        ],
    )
    result = evaluate_eligibility(collected)
    assert result["eligible_for_primary_gold"] is False
    assert "docs_or_openapi" in result["exclusion_reason"]


def test_unclassified_login_is_not_gold():
    assert classify_actor("mystery-account", None) == "unclassified"
    collected = _base(
        issue_comments=[
            {
                "login": "mystery-account",
                "user_type": None,
                "body": "Looks like a race on the cache map.",
                "inline": False,
            }
        ]
    )
    result = evaluate_eligibility(collected)
    assert result["eligible_for_primary_gold"] is False


def test_missing_review_means_ineligible():
    result = evaluate_eligibility(_base())
    assert result["human_review_present"] is False
    assert result["eligible_for_primary_gold"] is False
    assert "no_independent_human" in result["exclusion_reason"]
