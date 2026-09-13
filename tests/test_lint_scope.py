from oba_revieweval.lint.parse import RawIssue
from oba_revieweval.lint.scope import changed_file_set, lint_targets, package_dirs, partition_issues


def _issue(path: str, line: int = 1, rule: str = "SA4006") -> RawIssue:
    return RawIssue(
        file=path,
        line=line,
        column=1,
        rule=rule,
        message=f"{rule}: example",
        severity="",
        from_linter="staticcheck",
    )


def test_findings_on_unchanged_files_are_dropped():
    changed = changed_file_set(
        [{"filename": "internal/restapi/routes_for_agency_handler.go", "previous_filename": None}]
    )
    kept, dropped = partition_issues(
        [
            _issue("internal/restapi/routes_for_agency_handler.go", 20),
            _issue("internal/restapi/other_handler.go", 3),
        ],
        changed,
    )
    assert [item.file for item in kept] == ["internal/restapi/routes_for_agency_handler.go"]
    assert [item.file for item in dropped] == ["internal/restapi/other_handler.go"]


def test_unchanged_line_on_changed_file_is_kept():
    # Protocol §9 is file-scoped. Hunk-line dropping is not applied.
    changed = {"internal/webui/debug_index_handler.go"}
    kept, dropped = partition_issues(
        [_issue("internal/webui/debug_index_handler.go", 999)],
        changed,
    )
    assert len(kept) == 1
    assert dropped == []


def test_pr_457_file_stays_in_scope_when_first_parent_is_empty():
    changed = changed_file_set(
        [{"filename": "internal/restapi/routes_for_agency_handler.go", "status": "modified"}]
    )
    assert "internal/restapi/routes_for_agency_handler.go" in changed
    kept, dropped = partition_issues(
        [_issue("internal/restapi/routes_for_agency_handler.go")],
        changed,
    )
    assert dropped == []
    assert len(kept) == 1


def test_deleted_go_file_is_not_a_lint_target():
    targets = lint_targets(
        [
            {"filename": "old.go", "status": "removed"},
            {"filename": "kept.go", "status": "modified"},
            {"filename": "notes.md", "status": "modified"},
        ],
        existing={"kept.go", "notes.md"},
    )
    assert targets == ["kept.go"]


def test_package_dirs_are_unique_and_relative():
    assert package_dirs(
        [
            "gtfsdb/helpers.go",
            "gtfsdb/import.go",
            "internal/restapi/handler.go",
        ]
    ) == ["./gtfsdb", "./internal/restapi"]
