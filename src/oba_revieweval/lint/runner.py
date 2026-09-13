"""Run pinned golangci-lint on a merge-SHA worktree."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from oba_revieweval.dataset.git_anchor import (
    GitAnchorError,
    first_parent_paths,
    list_changed_files,
    resolve_merge_commit,
)
from oba_revieweval.lint.constants import (
    DEFAULT_BUILD_TAGS,
    GOLANGCI_VERSION,
    TOOL_NAME,
)
from oba_revieweval.lint.parse import (
    LintParseError,
    assign_stable_ids,
    findings_from_issues,
    parse_linter_output,
)
from oba_revieweval.lint.scope import changed_file_set, lint_targets, package_dirs, partition_issues

BUILD_TAGS_LINE = re.compile(r"^BUILD_TAGS\s*:?=\s*(.+)$", re.MULTILINE)
LINT_TAGS_LINE = re.compile(r"golangci-lint run --build-tags\s+\"([^\"]+)\"")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_maglev() -> Path:
    return repo_root() / "data" / "raw" / "cache" / "maglev"


def default_worktree() -> Path:
    return repo_root() / "data" / "raw" / "cache" / "lint-worktree"


def default_config() -> Path:
    return repo_root() / "configs" / "golangci-research.yml"


def default_tools_bin() -> Path:
    return repo_root() / "tools" / "bin"


def config_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def golangci_binary(tools_bin: Path | None = None) -> Path:
    tools_bin = tools_bin or default_tools_bin()
    name = "golangci-lint.exe" if os.name == "nt" else "golangci-lint"
    return tools_bin / name


def read_golangci_version(binary: Path) -> str:
    result = subprocess.run(
        [str(binary), "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    text = (result.stdout or result.stderr or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    if not match:
        raise RuntimeError(f"could not parse golangci-lint version from: {text!r}")
    return match.group(1)


def discover_cc() -> str | None:
    explicit = os.environ.get("CC")
    if explicit and Path(explicit).exists() and Path(explicit).name.lower().startswith("gcc"):
        return explicit
    msys = Path(r"C:\msys64\mingw64\bin\gcc.exe")
    if msys.exists():
        return str(msys)
    found = shutil.which("gcc")
    return found


def discover_go() -> Path | None:
    """Prefer the official Go toolchain, never MSYS2's trimmed go.exe."""
    candidates: list[Path] = []
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Go" / "bin"
    candidates.append(program_files / ("go.exe" if os.name == "nt" else "go"))
    which = shutil.which("go")
    if which:
        candidates.append(Path(which))
    for candidate in candidates:
        if not candidate.exists():
            continue
        lowered = str(candidate).replace("\\", "/").lower()
        if "msys64" in lowered or "mingw" in lowered:
            continue
        return candidate
    return None


def lint_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["CGO_ENABLED"] = "1"
    env["CGO_CFLAGS"] = "-DSQLITE_ENABLE_FTS5"
    env["GOTOOLCHAIN"] = env.get("GOTOOLCHAIN") or "auto"
    prefixes: list[str] = []
    go_bin = discover_go()
    if go_bin:
        prefixes.append(str(go_bin.parent))
        goroot = go_bin.parent.parent
        if (goroot / "src").exists() or (goroot / "lib").exists():
            env["GOROOT"] = str(goroot)
    cc = discover_cc()
    if cc:
        env["CC"] = cc
        prefixes.append(str(Path(cc).parent))
    if prefixes:
        env["PATH"] = os.pathsep.join([*prefixes, env.get("PATH", "")])
    return env


def build_tags_for_tree(worktree: Path) -> tuple[str, ...]:
    makefile = worktree / "Makefile"
    if not makefile.exists():
        return DEFAULT_BUILD_TAGS
    text = makefile.read_text(encoding="utf-8", errors="replace")
    match = BUILD_TAGS_LINE.search(text)
    if match:
        tags = tuple(part for part in match.group(1).split() if part)
        if tags:
            return tags
    lint = LINT_TAGS_LINE.search(text)
    if lint:
        tags = tuple(part for part in lint.group(1).split() if part)
        if tags:
            return tags
    return DEFAULT_BUILD_TAGS


def ensure_worktree(repo: Path, worktree: Path, merge_sha: str) -> None:
    git_dir = worktree / ".git"
    if git_dir.exists() or worktree.exists() and (worktree / "go.mod").exists():
        subprocess.run(
            ["git", "-C", str(worktree), "checkout", "--force", "--detach", merge_sha],
            check=True,
            capture_output=True,
            text=True,
        )
        return
    worktree.parent.mkdir(parents=True, exist_ok=True)
    if worktree.exists():
        shutil.rmtree(worktree)
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), merge_sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitAnchorError(
            f"worktree add {merge_sha}: {(result.stderr or result.stdout).strip()}"
        )


def worktree_head(worktree: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def download_modules(worktree: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        ["go", "mod", "download"],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "go mod download failed: " + (result.stderr or result.stdout or "").strip()
        )


def load_pr_metadata(raw_pr_dir: Path) -> dict[str, Any] | None:
    path = raw_pr_dir / "metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_pr(
    *,
    pr_number: int,
    merge_sha: str,
    repo: Path | None = None,
    worktree: Path | None = None,
    dest_dir: Path | None = None,
    config_path: Path | None = None,
    binary: Path | None = None,
    raw_pr_dir: Path | None = None,
) -> dict[str, Any]:
    repo = repo or default_maglev()
    worktree = worktree or default_worktree()
    dest_dir = dest_dir or repo_root() / "data" / "raw" / "lint" / str(pr_number)
    config_path = config_path or default_config()
    binary = binary or golangci_binary()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not binary.exists():
        raise FileNotFoundError(
            f"pinned golangci-lint missing at {binary}; run scripts/install_golangci_lint.py"
        )
    tool_version = read_golangci_version(binary)
    if tool_version != GOLANGCI_VERSION:
        raise RuntimeError(
            f"golangci-lint {tool_version} != pinned {GOLANGCI_VERSION}"
        )

    merge = resolve_merge_commit(repo, merge_sha)
    if merge.merge_sha.lower() != merge_sha.lower():
        raise GitAnchorError(
            f"#{pr_number}: resolved {merge.merge_sha} != requested {merge_sha}"
        )

    metadata = load_pr_metadata(raw_pr_dir) if raw_pr_dir else None
    if metadata:
        recorded = (metadata.get("merge_sha") or "").strip()
        if recorded and recorded.lower() != merge.merge_sha.lower():
            raise GitAnchorError(
                f"#{pr_number}: metadata merge_sha {recorded} != {merge.merge_sha}"
            )

    files = [item.as_dict() for item in list_changed_files(repo, merge)]
    first_parent = first_parent_paths(repo, merge) if merge.parents else []
    changed = changed_file_set(files)

    ensure_worktree(repo, worktree, merge.merge_sha)
    analyzed = worktree_head(worktree)
    if analyzed.lower() != merge.merge_sha.lower():
        raise GitAnchorError(
            f"#{pr_number}: worktree HEAD {analyzed} != merge {merge.merge_sha}"
        )
    main_head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if main_head.lower() == merge.merge_sha.lower() and pr_number != 0:
        # Allowed only if HEAD happens to equal the merge SHA. Still record it.
        pass

    existing = {
        path.replace("\\", "/")
        for path in _list_worktree_files(worktree)
    }
    targets = lint_targets(files, existing)
    packages = package_dirs(targets)
    tags = build_tags_for_tree(worktree)
    cfg_hash = config_sha256(config_path)
    env = lint_environment()
    if not env.get("CC"):
        raise RuntimeError(
            "CGO compiler not found. Maglev uses go-sqlite3; install gcc "
            "or set CC. On this research machine MSYS2 MinGW64 is expected."
        )

    raw_json_path = dest_dir / "raw.json"
    raw_txt_path = dest_dir / "raw.txt"
    for path in (raw_json_path, raw_txt_path):
        if path.exists():
            path.unlink()

    command = [
        str(binary),
        "run",
        "--config",
        str(config_path),
        "--build-tags",
        " ".join(tags),
        f"--output.json.path={raw_json_path}",
        f"--output.text.path={raw_txt_path}",
        "--output.text.colors=false",
        "--output.text.print-issued-lines=false",
        "--uniq-by-line=false",
    ]
    if packages:
        command.extend(packages)

    download_modules(worktree, env)
    if not targets:
        raw_txt_path.write_text("", encoding="utf-8")
        proc = subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    else:
        proc = subprocess.run(
            command,
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    json_text = raw_json_path.read_text(encoding="utf-8") if raw_json_path.exists() else ""
    text_output = raw_txt_path.read_text(encoding="utf-8") if raw_txt_path.exists() else ""
    # Preserve the process streams without rewriting the formatter files.
    (dest_dir / "process.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (dest_dir / "process.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

    parse_error = ""
    raw_issues = []
    try:
        if json_text.strip():
            raw_issues = parse_linter_output(json_text=json_text, worktree=str(worktree))
        elif text_output.strip():
            raw_issues = parse_linter_output(json_text=None, text_output=text_output, worktree=str(worktree))
        elif proc.returncode in {0, 1} and not targets:
            raw_issues = []
        elif proc.returncode == 0:
            raw_issues = []
        else:
            raise LintParseError("linter produced no parseable output")
    except LintParseError as exc:
        parse_error = str(exc)

    kept, dropped = partition_issues(raw_issues, changed) if not parse_error else ([], [])
    findings = assign_stable_ids(
        findings_from_issues(
            kept,
            pr_number=pr_number,
            commit_sha=merge.merge_sha,
            tool_version=tool_version,
        )
    )
    typecheck = any(issue.from_linter == "typecheck" or issue.rule == "typecheck" for issue in raw_issues)
    if parse_error or proc.returncode not in {0, 1}:
        status = "failed"
    elif typecheck:
        status = "typecheck_error"
    elif not targets:
        status = "no_go_targets"
    else:
        status = "ok"

    run = {
        "pr_number": pr_number,
        "tool": TOOL_NAME,
        "tool_version": tool_version,
        "install_source": (
            "https://github.com/golangci/golangci-lint/releases/download/"
            f"v{tool_version}/"
        ),
        "config": "configs/golangci-research.yml",
        "config_hash": cfg_hash,
        "commit_sha": merge.merge_sha,
        "analyzed_tree": "post-merge merge commit",
        "diff_mode": merge.diff_mode,
        "diff_base_sha": merge.base_sha,
        "diff_head_sha": merge.head_sha,
        "merge_parents": list(merge.parents),
        "first_parent_paths": first_parent,
        "first_parent_empty": len(first_parent) == 0,
        "changed_files": [item["filename"] for item in files],
        "lint_targets": targets,
        "lint_packages": packages,
        "build_tags": list(tags),
        "command": command,
        "cwd": str(worktree),
        "go_version_host": platform.platform(),
        "exit_code": proc.returncode,
        "execution_status": status,
        "parse_error": parse_error,
        "raw_issue_count": len(raw_issues),
        "finding_count": len(findings),
        "dropped_outside_diff": len(dropped),
        "typecheck_issue_count": sum(
            1 for issue in raw_issues if issue.from_linter == "typecheck" or issue.rule == "typecheck"
        ),
        "scope_rule": "keep findings whose file is in the merge-parent three-dot changed-file list",
        "special_case_457": pr_number == 457,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }
    (dest_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (dest_dir / "findings.json").write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    (dest_dir / "dropped_outside_diff.json").write_text(
        json.dumps([issue.as_dict() for issue in dropped], indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "run": run,
        "findings": findings,
        "manifest": {
            "pr_number": str(pr_number),
            "commit_sha": merge.merge_sha,
            "tool_version": tool_version,
            "config_hash": cfg_hash,
            "exit_code": str(proc.returncode),
            "finding_count": str(len(findings)),
            "execution_status": status,
            "diff_mode": merge.diff_mode,
            "first_parent_empty": "true" if not first_parent else "false",
            "build_tags": " ".join(tags),
            "raw_issue_count": str(len(raw_issues)),
            "dropped_outside_diff": str(len(dropped)),
            "analyzed_go_file_count": str(len(targets)),
        },
    }


def _list_worktree_files(worktree: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(worktree), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]
