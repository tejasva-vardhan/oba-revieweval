"""golangci-lint baseline adapters."""

from oba_revieweval.lint.aggregate import (
    load_lint_csv,
    summarize_findings,
    validate_lint_findings,
    validate_lint_manifest,
    write_lint_csv,
)
from oba_revieweval.lint.constants import FINDING_FIELDS, GOLANGCI_VERSION, MANIFEST_FIELDS
from oba_revieweval.lint.parse import (
    LintParseError,
    RawIssue,
    assign_stable_ids,
    findings_from_issues,
    parse_golangci_json,
    parse_golangci_text,
    parse_linter_output,
)
from oba_revieweval.lint.scope import changed_file_set, partition_issues

__all__ = [
    "FINDING_FIELDS",
    "GOLANGCI_VERSION",
    "LintParseError",
    "MANIFEST_FIELDS",
    "RawIssue",
    "assign_stable_ids",
    "changed_file_set",
    "findings_from_issues",
    "load_lint_csv",
    "parse_golangci_json",
    "parse_golangci_text",
    "parse_linter_output",
    "partition_issues",
    "summarize_findings",
    "validate_lint_findings",
    "validate_lint_manifest",
    "write_lint_csv",
]
