"""Change-scope filter for linter issues (protocol §9).

Protocol: run golangci-lint on the post-merge tree for files touched by
the PR; drop findings outside the PR diff.

Operationalization used here (file-scoped, not hunk-scoped):

* Changed files are the merge-parent three-dot list from
  `list_changed_files` — the same reconstruction as Phase 4.
* A finding is in-scope iff its file path is in that list (or is the
  pre-rename path of a renamed file).
* Findings on other files in the same package are dropped.
* Findings on unchanged lines of a changed file are kept. Protocol §9
  names files touched by the PR as the analysis unit and does not
  specify hunk-line matching. Hunk-level dropping is not applied.

#457: first-parent `git diff SHA^1 SHA` is empty because the same
RLock already landed via #456. The three-dot parent range of that
merge commit still includes `internal/restapi/routes_for_agency_handler.go`.
That file remains in-scope. HEAD is never substituted.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from oba_revieweval.lint.parse import RawIssue, normalize_repo_path


def changed_file_set(files: Iterable[dict[str, object] | object]) -> set[str]:
    names: set[str] = set()
    for item in files:
        if hasattr(item, "filename"):
            filename = getattr(item, "filename")
            previous = getattr(item, "previous_filename", None)
        else:
            filename = item.get("filename")  # type: ignore[union-attr]
            previous = item.get("previous_filename")  # type: ignore[union-attr]
        if filename:
            names.add(normalize_repo_path(str(filename)))
        if previous:
            names.add(normalize_repo_path(str(previous)))
    return names


def is_in_pr_diff(path: str, changed: set[str]) -> bool:
    return normalize_repo_path(path) in changed


def partition_issues(
    issues: list[RawIssue],
    changed: set[str],
) -> tuple[list[RawIssue], list[RawIssue]]:
    kept: list[RawIssue] = []
    dropped: list[RawIssue] = []
    for issue in issues:
        if is_in_pr_diff(issue.file, changed):
            kept.append(issue)
        else:
            dropped.append(issue)
    return kept, dropped


def lint_targets(changed_files: Iterable[dict[str, object] | object], existing: set[str]) -> list[str]:
    """Go files that exist on the post-merge tree and were touched by the PR."""
    targets: list[str] = []
    seen: set[str] = set()
    for item in changed_files:
        if hasattr(item, "filename"):
            filename = str(getattr(item, "filename"))
            status = str(getattr(item, "status", "") or "")
        else:
            filename = str(item.get("filename") or "")  # type: ignore[union-attr]
            status = str(item.get("status") or "")  # type: ignore[union-attr]
        path = normalize_repo_path(filename)
        if not path.endswith(".go"):
            continue
        if status in {"removed", "deleted"}:
            continue
        if path not in existing:
            continue
        if path in seen:
            continue
        seen.add(path)
        targets.append(path)
    return targets


def package_dirs(targets: Iterable[str]) -> list[str]:
    """golangci-lint / go/packages cannot mix files from different directories."""
    dirs: list[str] = []
    seen: set[str] = set()
    for path in targets:
        parent = normalize_repo_path(str(Path(path).parent))
        spec = "./." if parent in {"", "."} else f"./{parent}"
        if spec not in seen:
            seen.add(spec)
            dirs.append(spec)
    return dirs
