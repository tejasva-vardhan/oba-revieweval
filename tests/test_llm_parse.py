from pathlib import Path

import pytest

from oba_revieweval.models.parse import (
    ModelParseError,
    assign_stable_ids,
    findings_from_issues,
    parse_model_json,
)

FIXTURE = Path(__file__).parent / "fixtures" / "llm" / "valid.json"


def test_valid_structured_output_is_atomic():
    issues = parse_model_json(FIXTURE.read_text(encoding="utf-8"))
    assert len(issues) == 2
    assert issues[0].file == "internal/restapi/block_handler.go"
    assert issues[0].line == 40
    assert issues[0].title == "Missing unlock"
    assert issues[0].reasoning.startswith("RLock")
    assert issues[0].description == "Unlock in a defer."
    assert issues[0].severity == "high"


def test_duplicates_are_not_collapsed():
    issues = parse_model_json(FIXTURE.read_text(encoding="utf-8"))
    rows = findings_from_issues(
        issues,
        pr_number=1428,
        commit_sha="abc",
        tool="llm_a",
        tool_version="gpt-4o-2024-11-20",
    )
    assert len(rows) == 2
    assert rows[0]["raw_finding_id"] == "A-1428-1"
    assert rows[1]["raw_finding_id"] == "A-1428-2"


def test_empty_findings_array():
    assert parse_model_json('{"findings":[]}') == []
    assert parse_model_json('{"findings":null}') == []


def test_empty_output_raises():
    with pytest.raises(ModelParseError, match="empty"):
        parse_model_json("")
    with pytest.raises(ModelParseError, match="empty"):
        parse_model_json("   ")


def test_malformed_output_raises():
    with pytest.raises(ModelParseError, match="malformed"):
        parse_model_json("{")
    with pytest.raises(ModelParseError, match="missing findings"):
        parse_model_json('{"issue":[]}')
    with pytest.raises(ModelParseError, match="not a list"):
        parse_model_json('{"findings":{}}')
    with pytest.raises(ModelParseError, match="not an object"):
        parse_model_json('{"findings":["x"]}')


def test_missing_fields_do_not_crash():
    issues = parse_model_json('{"findings":[{"title":"x"}]}')
    assert issues[0].file == ""
    assert issues[0].line == 0
    assert issues[0].title == "x"
    assert issues[0].severity == ""


def test_invalid_line_becomes_zero():
    issues = parse_model_json('{"findings":[{"title":"x","path":"a.go","line":"nope"}]}')
    assert issues[0].line == 0
    assert issues[0].file == "a.go"


def test_fenced_json_is_accepted():
    issues = parse_model_json('```json\n{"findings":[{"title":"only"}]}\n```')
    assert issues[0].title == "only"


def test_complimentary_rows_are_discarded():
    issues = parse_model_json('{"findings":[{"title":"LGTM"},{"title":"real","rationale":"bug"}]}')
    assert [item.title for item in issues] == ["real"]


def test_stable_ids_keep_every_row():
    issues = parse_model_json(FIXTURE.read_text(encoding="utf-8"))
    rows = assign_stable_ids(
        findings_from_issues(issues, pr_number=1, commit_sha="c", tool="llm_a", tool_version="m")
    )
    assert [row["raw_finding_id"] for row in rows] == ["A-1-1", "A-1-2"]
