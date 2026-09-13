from oba_revieweval.annotation.schema import Finding
from oba_revieweval.evaluation.score import score_tool


def test_extra_valid_is_not_false_positive():
    findings = [
        Finding(
            finding_id="1",
            pr_id=1,
            tool="llm_a",
            category="api_gtfs",
            text="real extra bug",
            label="extra_valid",
            rationale="valid but not in human gold",
        ),
        Finding(
            finding_id="2",
            pr_id=1,
            tool="llm_a",
            category="api_gtfs",
            text="matches gold",
            label="tp_useful",
            human_issue_id="h1",
            rationale="same issue as reviewer",
        ),
    ]
    metrics = score_tool(findings, {"h1"})
    assert metrics["tp"] == 1
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
    assert metrics["extra_valid_rate"] == 0.5


def test_harmful_counts_as_incorrect_and_fp():
    findings = [
        Finding(
            finding_id="1",
            pr_id=1,
            tool="llm_a",
            category="concurrency",
            text="drop the mutex",
            label="harmful",
            rationale="would introduce a race",
        )
    ]
    metrics = score_tool(findings, {"h1"})
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["harmful_rate"] == 1.0
    assert metrics["incorrect_rate"] == 1.0
