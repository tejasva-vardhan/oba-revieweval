import json
from pathlib import Path

from oba_revieweval.dataset.corpus import load_recommended
from oba_revieweval.lint.aggregate import (
    load_lint_csv,
    summarize_findings,
    validate_lint_findings,
    validate_lint_manifest,
)
from oba_revieweval.lint.constants import FINDING_FIELDS, GOLANGCI_VERSION, MANIFEST_FIELDS
from oba_revieweval.lint.runner import config_sha256, default_config

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "lint_manifest.csv"
FINDINGS = ROOT / "data" / "lint_findings.csv"
RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"
LINT_ROOT = ROOT / "data" / "raw" / "lint"


def _synthetic_manifest(recommended: list[dict[str, str]], config_hash: str) -> list[dict[str, str]]:
    rows = []
    for item in recommended:
        rows.append(
            {
                "pr_number": item["pr_number"],
                "commit_sha": item["merge_sha"],
                "tool_version": GOLANGCI_VERSION,
                "config_hash": config_hash,
                "exit_code": "0",
                "finding_count": "0",
                "execution_status": "ok",
                "diff_mode": "merge_parents_three_dot",
                "first_parent_empty": "false",
                "build_tags": "sqlite_fts5",
                "raw_issue_count": "0",
                "dropped_outside_diff": "0",
                "analyzed_go_file_count": "1",
            }
        )
    return rows


def test_manifest_validator_requires_all_33_merge_shas():
    recommended = load_recommended(RECOMMENDED)
    assert len(recommended) == 33
    config_hash = config_sha256(default_config())
    rows = _synthetic_manifest(recommended, config_hash)
    assert validate_lint_manifest(
        rows,
        recommended=recommended,
        expected_version=GOLANGCI_VERSION,
        expected_config_hash=config_hash,
    ) == []
    broken = [dict(row) for row in rows]
    broken[0]["commit_sha"] = "0" * 40
    errors = validate_lint_manifest(
        broken,
        recommended=recommended,
        expected_version=GOLANGCI_VERSION,
        expected_config_hash=config_hash,
    )
    assert any(item.startswith("commit_not_merge_sha:271") for item in errors)
    missing = rows[1:]
    errors = validate_lint_manifest(
        missing,
        recommended=recommended,
        expected_version=GOLANGCI_VERSION,
        expected_config_hash=config_hash,
    )
    assert any(item.startswith("manifest_pr_set_mismatch") for item in errors)


def test_finding_counts_must_match_manifest():
    findings = [
        {
            "pr_number": "271",
            "tool": "golangci-lint",
            "tool_version": GOLANGCI_VERSION,
            "commit_sha": "c718a713adabe64fdc201533ea079717aaf15299",
            "file": "a.go",
            "line": "1",
            "column": "1",
            "rule": "SA4006",
            "message": "unused",
            "severity": "",
            "raw_finding_id": "L-271-1",
        }
    ]
    manifest = [
        {
            "pr_number": "271",
            "finding_count": "1",
        },
        {
            "pr_number": "354",
            "finding_count": "0",
        },
    ]
    assert validate_lint_findings(findings, manifest) == []
    dup = findings + [dict(findings[0])]
    assert any(item.startswith("duplicate_raw_finding_id") for item in validate_lint_findings(dup, manifest))


def test_committed_baseline_covers_recommended_corpus():
    recommended = load_recommended(RECOMMENDED)
    assert MANIFEST.exists(), "run scripts/run_linter.py to produce data/lint_manifest.csv"
    assert FINDINGS.exists(), "run scripts/run_linter.py to produce data/lint_findings.csv"
    manifest = load_lint_csv(MANIFEST)
    findings = load_lint_csv(FINDINGS)
    config_hash = config_sha256(default_config())
    assert list(manifest[0].keys())[:7] == list(MANIFEST_FIELDS[:7])
    if findings:
        assert list(findings[0].keys()) == list(FINDING_FIELDS)
    errors = validate_lint_manifest(
        manifest,
        recommended=recommended,
        expected_version=GOLANGCI_VERSION,
        expected_config_hash=config_hash,
    )
    errors.extend(validate_lint_findings(findings, manifest))
    assert errors == []
    summary = summarize_findings(findings, manifest)
    assert summary["pr_count"] == 33
    for item in recommended:
        pr_dir = LINT_ROOT / item["pr_number"]
        assert (pr_dir / "run.json").exists(), f"missing run.json for #{item['pr_number']}"
        assert (pr_dir / "findings.json").exists(), f"missing findings.json for #{item['pr_number']}"
        run_text = (pr_dir / "run.json").read_text(encoding="utf-8")
        assert item["merge_sha"] in run_text
        row = next(row for row in manifest if row["pr_number"] == item["pr_number"])
        assert row["commit_sha"] == item["merge_sha"]
        raw = pr_dir / "raw.json"
        if raw.exists():
            payload = json.loads(raw.read_text(encoding="utf-8"))
            assert "Issues" in payload
            enabled = {item["Name"] for item in payload["Report"]["Linters"] if item.get("Enabled")}
            assert {"govet", "staticcheck"}.issubset(enabled)


def test_pr_457_uses_three_dot_file_when_first_parent_empty():
    run = json.loads((LINT_ROOT / "457" / "run.json").read_text(encoding="utf-8"))
    assert run["first_parent_empty"] is True
    assert run["first_parent_paths"] == []
    assert run["changed_files"] == ["internal/restapi/routes_for_agency_handler.go"]
    assert run["commit_sha"] == "e1044a52bfdca7b1297140514df56eb4b1724cf8"
    assert run["commit_sha"] != run.get("cwd")
