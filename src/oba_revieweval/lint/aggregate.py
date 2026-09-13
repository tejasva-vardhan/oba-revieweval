"""Aggregate per-PR lint outputs into CSV tables."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from oba_revieweval.lint.constants import FINDING_FIELDS, MANIFEST_FIELDS


def write_lint_csv(path: Path, rows: list[dict[str, str]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_lint_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_lint_manifest(
    rows: list[dict[str, str]],
    *,
    recommended: list[dict[str, str]],
    expected_version: str,
    expected_config_hash: str,
) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["manifest_empty"]
    if list(rows[0].keys())[:7] != list(MANIFEST_FIELDS[:7]):
        errors.append("manifest_missing_required_columns")
    numbers = [int(row["pr_number"]) for row in rows]
    expected = [int(row["pr_number"]) for row in recommended]
    if sorted(numbers) != sorted(expected):
        errors.append(f"manifest_pr_set_mismatch:{sorted(numbers)}!={sorted(expected)}")
    if len(numbers) != len(set(numbers)):
        errors.append("manifest_duplicate_pr")
    for row in rows:
        if row.get("tool_version") != expected_version:
            errors.append(f"tool_version_mismatch:{row.get('pr_number')}")
        if row.get("config_hash") != expected_config_hash:
            errors.append(f"config_hash_mismatch:{row.get('pr_number')}")
        if not row.get("commit_sha"):
            errors.append(f"missing_commit:{row.get('pr_number')}")
        recommended_sha = next(
            (item["merge_sha"] for item in recommended if int(item["pr_number"]) == int(row["pr_number"])),
            "",
        )
        if recommended_sha and row.get("commit_sha", "").lower() != recommended_sha.lower():
            errors.append(f"commit_not_merge_sha:{row.get('pr_number')}")
        if row.get("execution_status") not in {"ok", "no_go_targets"}:
            errors.append(f"execution_not_ok:{row.get('pr_number')}:{row.get('execution_status')}")
        try:
            int(row.get("finding_count") or "")
            int(row.get("exit_code") or "")
        except ValueError:
            errors.append(f"non_integer_counts:{row.get('pr_number')}")
    return errors


def validate_lint_findings(
    findings: list[dict[str, str]],
    manifest: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    if findings and list(findings[0].keys()) != list(FINDING_FIELDS):
        errors.append("findings_field_mismatch")
    seen_ids: set[str] = set()
    by_pr: Counter[str] = Counter()
    for row in findings:
        fid = row.get("raw_finding_id") or ""
        if not fid:
            errors.append("missing_raw_finding_id")
            continue
        if fid in seen_ids:
            errors.append(f"duplicate_raw_finding_id:{fid}")
        seen_ids.add(fid)
        by_pr[row["pr_number"]] += 1
        if row.get("tool") != "golangci-lint":
            errors.append(f"unexpected_tool:{fid}")
    counts = {row["pr_number"]: int(row["finding_count"]) for row in manifest}
    for pr_number, count in counts.items():
        if by_pr.get(pr_number, 0) != count:
            errors.append(f"finding_count_mismatch:{pr_number}:{by_pr.get(pr_number, 0)}!={count}")
    extra = set(by_pr) - set(counts)
    if extra:
        errors.append(f"findings_for_unknown_pr:{sorted(extra)}")
    return errors


def summarize_findings(findings: list[dict[str, str]], manifest: list[dict[str, str]]) -> dict[str, Any]:
    by_rule = Counter(row["rule"] or "(empty)" for row in findings)
    zero = [row["pr_number"] for row in manifest if int(row["finding_count"]) == 0]
    failed = [row for row in manifest if row["execution_status"] not in {"ok", "no_go_targets"}]
    return {
        "pr_count": len(manifest),
        "finding_count": len(findings),
        "findings_by_rule": dict(by_rule),
        "zero_finding_prs": zero,
        "failed_prs": failed,
        "ok_prs": sum(1 for row in manifest if row["execution_status"] == "ok"),
    }
