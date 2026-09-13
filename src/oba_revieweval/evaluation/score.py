"""Score labeled findings against the human defect/design reference."""

from __future__ import annotations

from collections import defaultdict

from oba_revieweval.annotation.schema import Finding
from oba_revieweval.evaluation.metrics import f1, precision, rate, recall


def score_tool(
    findings: list[Finding],
    reference_issue_ids: set[str],
) -> dict[str, float | None]:
    """Score one tool.

    Precision/recall use only findings labeled tp_useful that match a reference
    issue. extra_valid is excluded from the false-positive count. harmful counts
    as incorrect and as its own rate.
    """
    matched_refs: set[str] = set()
    tp = 0
    fp = 0
    incorrect = 0
    harmful = 0
    extra_valid = 0

    for finding in findings:
        if finding.label == "tp_useful":
            if finding.human_issue_id and finding.human_issue_id in reference_issue_ids:
                tp += 1
                matched_refs.add(finding.human_issue_id)
            else:
                fp += 1
        elif finding.label == "extra_valid":
            extra_valid += 1
        elif finding.label == "harmful":
            incorrect += 1
            harmful += 1
            fp += 1
        elif finding.label == "incorrect":
            incorrect += 1
            fp += 1

    fn = len(reference_issue_ids - matched_refs)
    n = len(findings)
    prec = precision(tp, fp)
    rec = recall(tp, fn)
    return {
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "precision": prec,
        "recall": rec,
        "f1": f1(prec, rec),
        "incorrect_rate": rate(incorrect, n),
        "harmful_rate": rate(harmful, n),
        "extra_valid_rate": rate(extra_valid, n),
        "n_findings": float(n),
    }


def score_by_tool(
    findings: list[Finding],
    reference_issue_ids_by_pr: dict[int, set[str]],
) -> dict[str, dict[str, float | None]]:
    by_tool: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_tool[finding.tool].append(finding)

    all_refs: set[str] = set()
    for issue_ids in reference_issue_ids_by_pr.values():
        all_refs |= issue_ids

    return {tool: score_tool(rows, all_refs) for tool, rows in by_tool.items()}
