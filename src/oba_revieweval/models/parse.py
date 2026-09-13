"""Parse frozen llm_review_v1 JSON into atomic findings.

Raw model text is never rewritten. Malformed output is recorded, not repaired.
Multiple findings are never collapsed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from oba_revieweval.lint.parse import normalize_repo_path
from oba_revieweval.models.constants import FINDING_FIELDS

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
COMPLIMENT = re.compile(
    r"^(lgtm|looks good|no issues?|nice work|thanks)\.?$",
    re.IGNORECASE,
)


class ModelParseError(ValueError):
    """Raised when the model response is not usable JSON findings."""


@dataclass(frozen=True)
class ModelIssue:
    file: str
    line: int
    title: str
    description: str
    severity: str
    reasoning: str
    category: str
    recommendation: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ModelParseError("empty model output")
    fenced = FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    return text


def parse_model_json(raw: str) -> list[ModelIssue]:
    text = extract_json_text(raw)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelParseError(f"malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ModelParseError("top-level JSON must be an object")
    if "findings" not in payload:
        raise ModelParseError("JSON object missing findings")
    items = payload.get("findings")
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ModelParseError("findings is not a list")
    issues: list[ModelIssue] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ModelParseError(f"finding {index} is not an object")
        issue = _issue_from_obj(item)
        if _is_empty_or_complimentary(issue):
            continue
        issues.append(issue)
    return issues


def _issue_from_obj(item: dict[str, Any]) -> ModelIssue:
    path = item.get("path") or item.get("file") or ""
    line_raw = item.get("line") if item.get("line") is not None else item.get("Line")
    try:
        line = int(line_raw) if line_raw not in (None, "") else 0
    except (TypeError, ValueError):
        line = 0
    title = str(item.get("title") or "").strip()
    rationale = str(item.get("rationale") or item.get("reasoning") or "").strip()
    recommendation = str(item.get("recommendation") or item.get("description") or "").strip()
    description = recommendation or rationale
    return ModelIssue(
        file=normalize_repo_path(str(path)),
        line=line,
        title=title,
        description=description,
        severity=str(item.get("severity") or "").strip(),
        reasoning=rationale,
        category=str(item.get("category") or "").strip(),
        recommendation=recommendation,
    )


def _is_empty_or_complimentary(issue: ModelIssue) -> bool:
    blob = " ".join([issue.title, issue.reasoning, issue.description]).strip()
    if not blob:
        return True
    return bool(COMPLIMENT.match(blob))


def findings_from_issues(
    issues: list[ModelIssue],
    *,
    pr_number: int,
    commit_sha: str,
    tool: str,
    tool_version: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, issue in enumerate(issues, start=1):
        message = issue.title
        if issue.reasoning:
            message = f"{issue.title}: {issue.reasoning}" if issue.title else issue.reasoning
        rows.append(
            {
                "pr_number": str(pr_number),
                "tool": tool,
                "tool_version": tool_version,
                "commit_sha": commit_sha,
                "file": issue.file,
                "line": str(issue.line),
                "column": "0",
                "rule": issue.category or "other",
                "message": message,
                "severity": issue.severity,
                "raw_finding_id": f"A-{pr_number}-{index}",
                "title": issue.title,
                "description": issue.description,
                "reasoning": issue.reasoning,
                "recommendation": issue.recommendation,
            }
        )
    return rows


def finding_sort_key(row: dict[str, str]) -> tuple[str, int, str, str]:
    return (
        row.get("file") or "",
        int(row.get("line") or 0),
        row.get("rule") or "",
        row.get("message") or "",
    )


def assign_stable_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(rows, key=finding_sort_key)
    out: list[dict[str, str]] = []
    for index, row in enumerate(ordered, start=1):
        copied = dict(row)
        copied["raw_finding_id"] = f"A-{copied['pr_number']}-{index}"
        slim = {field: copied.get(field, "") for field in FINDING_FIELDS}
        slim["title"] = copied.get("title", "")
        slim["description"] = copied.get("description", "")
        slim["reasoning"] = copied.get("reasoning", "")
        slim["recommendation"] = copied.get("recommendation", "")
        out.append(slim)
    return out
