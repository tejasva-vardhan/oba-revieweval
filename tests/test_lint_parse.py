import json
from pathlib import Path

import pytest

from oba_revieweval.lint.parse import (
    LintParseError,
    assign_stable_ids,
    extract_rule,
    findings_from_issues,
    normalize_repo_path,
    parse_golangci_json,
    parse_golangci_text,
    parse_linter_output,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lint"


def test_json_extracts_file_line_column_and_rule():
    issues = parse_golangci_json((FIXTURES / "sample.json").read_text(encoding="utf-8"))
    assert len(issues) == 3
    assert issues[0].file == "internal/restapi/handler.go"
    assert issues[0].line == 40
    assert issues[0].column == 2
    assert issues[0].rule == "SA5011"
    assert issues[0].from_linter == "staticcheck"
    assert issues[1].rule == "govet"
    assert issues[1].from_linter == "govet"
    assert issues[2].rule == "SA4006"
    assert issues[2].severity == "warning"


def test_text_parser_matches_json_locations():
    issues = parse_golangci_text((FIXTURES / "sample.txt").read_text(encoding="utf-8"))
    assert [(item.file, item.line, item.column, item.rule) for item in issues] == [
        ("internal/restapi/handler.go", 40, 2, "SA5011"),
        ("internal/restapi/other.go", 8, 5, "govet"),
        ("internal/restapi/handler.go", 40, 2, "SA4006"),
    ]


def test_empty_issues_array_is_zero_findings():
    assert parse_golangci_json('{"Issues":[]}') == []
    assert parse_golangci_json('{"Issues":null}') == []


def test_real_pr_702_json_is_parseable():
    path = Path(__file__).resolve().parents[1] / "data" / "raw" / "lint" / "702" / "raw.json"
    if not path.exists():
        pytest.skip("PR 702 raw lint output not generated yet")
    payload = path.read_text(encoding="utf-8")
    assert parse_golangci_json(payload) == []
    report = json.loads(payload)["Report"]["Linters"]
    enabled = {item["Name"] for item in report if item.get("Enabled")}
    assert enabled == {"govet", "staticcheck", "typecheck"}


def test_malformed_output_raises():
    with pytest.raises(LintParseError, match="empty"):
        parse_golangci_json("")
    with pytest.raises(LintParseError, match="malformed"):
        parse_golangci_json("{")
    with pytest.raises(LintParseError, match="missing Issues"):
        parse_golangci_json('{"Report":{}}')
    with pytest.raises(LintParseError, match="not a list"):
        parse_golangci_json('{"Issues":"nope"}')
    with pytest.raises(LintParseError, match="not an object"):
        parse_golangci_json('{"Issues":[1]}')


def test_duplicates_are_not_collapsed():
    issues = parse_golangci_json((FIXTURES / "sample.json").read_text(encoding="utf-8"))
    same_line = [item for item in issues if item.file.endswith("handler.go") and item.line == 40]
    assert len(same_line) == 2
    findings = findings_from_issues(
        issues,
        pr_number=702,
        commit_sha="abebfc2f9193603f67b25ac6b976623623857826",
        tool_version="2.13.2",
    )
    assert len(findings) == 3
    assert findings[0]["commit_sha"] == "abebfc2f9193603f67b25ac6b976623623857826"
    assert findings[0]["pr_number"] == "702"
    assert findings[0]["raw_finding_id"] == "L-702-1"
    assert findings[2]["raw_finding_id"] == "L-702-3"


def test_stable_ids_follow_sort_but_keep_every_row():
    issues = parse_linter_output(json_text=(FIXTURES / "sample.json").read_text(encoding="utf-8"))
    rows = findings_from_issues(issues, pr_number=1, commit_sha="abc")
    rows[0]["raw_finding_id"] = "tmp"
    ordered = assign_stable_ids(rows)
    assert [row["file"] for row in ordered] == [
        "internal/restapi/handler.go",
        "internal/restapi/handler.go",
        "internal/restapi/other.go",
    ]
    assert [row["raw_finding_id"] for row in ordered] == ["L-1-1", "L-1-2", "L-1-3"]


def test_absolute_windows_paths_are_normalized():
    path = normalize_repo_path(
        r"C:\cache\lint-worktree\internal\restapi\handler.go",
        worktree=r"C:\cache\lint-worktree",
    )
    assert path == "internal/restapi/handler.go"


def test_extract_rule_from_staticcheck_code():
    assert extract_rule("SA4006: unused", "staticcheck") == "SA4006"
    assert extract_rule("copylocks: copied", "govet") == "govet"
