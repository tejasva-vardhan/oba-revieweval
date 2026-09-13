"""Parse golangci-lint JSON/text into atomic findings.

Raw linter output is never rewritten. This module only reads it.
Multiple issues are never collapsed, even when file/line/rule match.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from oba_revieweval.lint.constants import FINDING_FIELDS, GOLANGCI_VERSION, TOOL_NAME

TEXT_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*(?P<body>.+)$"
)
RULE_IN_TEXT = re.compile(r"\b(?P<rule>(?:SA|ST|S|QF|U)\d{3,4})\b")
LINTER_SUFFIX = re.compile(r"\s+\((?P<linter>[a-zA-Z0-9_-]+)\)$")


class LintParseError(ValueError):
    """Raised when linter output cannot be parsed into atomic issues."""


@dataclass(frozen=True)
class RawIssue:
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str
    from_linter: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_repo_path(path: str, *, worktree: str | None = None) -> str:
    """Turn an absolute or mixed-separator path into a repo-relative POSIX path."""
    text = (path or "").strip().replace("\\", "/")
    if worktree:
        root = worktree.replace("\\", "/").rstrip("/")
        if text.lower().startswith(root.lower() + "/"):
            text = text[len(root) + 1 :]
        elif text.lower() == root.lower():
            text = ""
    if text.startswith("./"):
        text = text[2:]
    return text


def extract_rule(text: str, from_linter: str) -> str:
    match = RULE_IN_TEXT.search(text or "")
    if match:
        return match.group("rule")
    return (from_linter or "").strip()


def _issue_from_json_obj(item: dict[str, Any], *, worktree: str | None = None) -> RawIssue:
    pos = item.get("Pos") or item.get("pos") or {}
    filename = pos.get("Filename") or pos.get("filename") or item.get("Pos.Filename") or ""
    line = pos.get("Line") or pos.get("line") or 0
    column = pos.get("Column") or pos.get("column") or 0
    from_linter = str(item.get("FromLinter") or item.get("fromLinter") or "")
    message = str(item.get("Text") or item.get("text") or "")
    severity = str(item.get("Severity") or item.get("severity") or "")
    return RawIssue(
        file=normalize_repo_path(str(filename), worktree=worktree),
        line=int(line or 0),
        column=int(column or 0),
        rule=extract_rule(message, from_linter),
        message=message,
        severity=severity,
        from_linter=from_linter,
    )


def parse_golangci_json(text: str, *, worktree: str | None = None) -> list[RawIssue]:
    """Parse golangci-lint JSON. Empty Issues is valid (zero findings)."""
    stripped = (text or "").strip()
    if not stripped:
        raise LintParseError("empty JSON output")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LintParseError(f"malformed JSON: {exc}") from exc
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if "Issues" not in payload and "issues" not in payload:
            raise LintParseError("JSON object missing Issues")
        items = payload.get("Issues")
        if items is None:
            items = payload.get("issues")
        if items is None:
            items = []
    else:
        raise LintParseError(f"unexpected JSON type: {type(payload).__name__}")
    if not isinstance(items, list):
        raise LintParseError("Issues is not a list")
    issues: list[RawIssue] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise LintParseError(f"issue {index} is not an object")
        issues.append(_issue_from_json_obj(item, worktree=worktree))
    return issues


def parse_golangci_text(text: str, *, worktree: str | None = None) -> list[RawIssue]:
    """Parse colored-off text output. Used as a fallback and in tests."""
    issues: list[RawIssue] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("0 issues") or line.startswith("level="):
            continue
        match = TEXT_LINE.match(line)
        if not match:
            continue
        body = match.group("body")
        linter = ""
        suffix = LINTER_SUFFIX.search(body)
        if suffix:
            linter = suffix.group("linter")
            body = body[: suffix.start()]
        issues.append(
            RawIssue(
                file=normalize_repo_path(match.group("file"), worktree=worktree),
                line=int(match.group("line")),
                column=int(match.group("column") or 0),
                rule=extract_rule(body, linter),
                message=body,
                severity="",
                from_linter=linter,
            )
        )
    return issues


def parse_linter_output(
    *,
    json_text: str | None,
    text_output: str | None = None,
    worktree: str | None = None,
) -> list[RawIssue]:
    if json_text is not None and json_text.strip():
        return parse_golangci_json(json_text, worktree=worktree)
    if text_output is not None:
        return parse_golangci_text(text_output, worktree=worktree)
    raise LintParseError("no linter output to parse")


def findings_from_issues(
    issues: list[RawIssue],
    *,
    pr_number: int,
    commit_sha: str,
    tool_version: str = GOLANGCI_VERSION,
) -> list[dict[str, str]]:
    """Convert raw issues to atomic finding rows. Does not drop or merge."""
    rows: list[dict[str, str]] = []
    for index, issue in enumerate(issues, start=1):
        rows.append(
            {
                "pr_number": str(pr_number),
                "tool": TOOL_NAME,
                "tool_version": tool_version,
                "commit_sha": commit_sha,
                "file": issue.file,
                "line": str(issue.line),
                "column": str(issue.column),
                "rule": issue.rule,
                "message": issue.message,
                "severity": issue.severity,
                "raw_finding_id": f"L-{pr_number}-{index}",
            }
        )
    return rows


def finding_sort_key(row: dict[str, str]) -> tuple[str, int, int, str, str]:
    return (
        row.get("file") or "",
        int(row.get("line") or 0),
        int(row.get("column") or 0),
        row.get("rule") or "",
        row.get("message") or "",
    )


def assign_stable_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Re-number raw_finding_id after a deterministic sort. Does not drop rows."""
    ordered = sorted(rows, key=finding_sort_key)
    out: list[dict[str, str]] = []
    for index, row in enumerate(ordered, start=1):
        copied = {field: row.get(field, "") for field in FINDING_FIELDS}
        copied["raw_finding_id"] = f"L-{copied['pr_number']}-{index}"
        out.append(copied)
    return out
