"""Prove the pinned binary + research config can emit findings.

Zero corpus findings are only meaningful if the same tool reports
known govet/staticcheck defects on a synthetic module.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from oba_revieweval.lint.parse import parse_golangci_json
from oba_revieweval.lint.runner import default_config, golangci_binary, lint_environment

BAD_GO = """package example

import "fmt"

func Broken() {
	fmt.Printf("%s", 1)
	x := 1
	x = 2
	_ = x
}
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.mark.skipif(not golangci_binary().exists(), reason="pinned golangci-lint is not installed")
def test_research_config_reports_known_printf_bug(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example\n\ngo 1.24\n", encoding="utf-8")
    (tmp_path / "bad.go").write_text(BAD_GO, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "research@example.test")
    _git(tmp_path, "config", "user.name", "research")
    _git(tmp_path, "add", "go.mod", "bad.go")
    _git(tmp_path, "commit", "-m", "fixture")
    raw = tmp_path / "raw.json"
    result = subprocess.run(
        [
            str(golangci_binary()),
            "run",
            "--config",
            str(default_config()),
            f"--output.json.path={raw}",
            "--output.text.colors=false",
            "--uniq-by-line=false",
            "./.",
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
        env=lint_environment(),
    )
    assert raw.exists(), result.stderr
    issues = parse_golangci_json(raw.read_text(encoding="utf-8"))
    assert result.returncode == 1
    assert issues, result.stderr or raw.read_text(encoding="utf-8")
    rules = {issue.rule for issue in issues}
    linters = {issue.from_linter for issue in issues}
    assert "govet" in linters or any("printf" in issue.message.lower() for issue in issues)
    payload = json.loads(raw.read_text(encoding="utf-8"))
    enabled = {item["Name"] for item in payload["Report"]["Linters"] if item.get("Enabled")}
    assert {"govet", "staticcheck"}.issubset(enabled)
    assert rules  # at least one atomic rule was produced
