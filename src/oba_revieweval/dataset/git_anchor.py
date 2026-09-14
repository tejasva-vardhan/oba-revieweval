"""SHA-anchored diffs from a local Maglev checkout.

The merge commit is the reproducibility pin. We never walk HEAD or a
later main snapshot. Two-parent merges use the three-dot range between
that commit's recorded parents (the PR branch vs the merge-base with
main). One-parent squash commits use first-parent.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DIFF_GIT = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)
RENAME_FROM = re.compile(r"^rename from (.+)$", re.MULTILINE)
BINARY_LINE = re.compile(r"^Binary files (.+) and (.+) differ$", re.MULTILINE)


class GitAnchorError(ValueError):
    """Raised when a merge SHA cannot be resolved in the local checkout."""


@dataclass(frozen=True)
class MergeCommit:
    merge_sha: str
    parents: tuple[str, ...]
    diff_mode: str
    base_sha: str
    head_sha: str


@dataclass
class FileChange:
    filename: str
    status: str
    additions: int | None
    deletions: int | None
    previous_filename: str | None = None
    binary: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
            "previous_filename": self.previous_filename,
            "binary": self.binary,
        }


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise GitAnchorError(f"git {' '.join(args)}: {err}")
    return result.stdout


def resolve_merge_commit(repo: Path, merge_sha: str) -> MergeCommit:
    full = run_git(repo, "rev-parse", "--verify", f"{merge_sha}^{{commit}}").strip()
    parents = tuple(run_git(repo, "log", "-1", "--format=%P", full).split())
    if not parents:
        raise GitAnchorError(f"{merge_sha}: no parents")
    if len(parents) == 1:
        return MergeCommit(
            merge_sha=full,
            parents=parents,
            diff_mode="squash_first_parent",
            base_sha=parents[0],
            head_sha=full,
        )
    return MergeCommit(
        merge_sha=full,
        parents=parents,
        diff_mode="merge_parents_three_dot",
        base_sha=parents[0],
        head_sha=parents[1],
    )


def first_parent_paths(repo: Path, merge: MergeCommit) -> list[str]:
    text = run_git(repo, "diff", "--name-only", f"{merge.merge_sha}^1", merge.merge_sha)
    return [line for line in text.splitlines() if line.strip()]


def _status_name(code: str) -> str:
    if code.startswith("A"):
        return "added"
    if code.startswith("D"):
        return "removed"
    if code.startswith("M"):
        return "modified"
    if code.startswith("R"):
        return "renamed"
    if code.startswith("C"):
        return "copied"
    if code.startswith("T"):
        return "changed"
    return code


def list_changed_files(repo: Path, merge: MergeCommit) -> list[FileChange]:
    spec = f"{merge.base_sha}...{merge.head_sha}"
    raw_status = run_git(repo, "diff", "-z", "--name-status", "--find-renames", spec)
    raw_num = run_git(repo, "diff", "--numstat", "--find-renames", spec)
    num: dict[str, tuple[int | None, int | None, bool]] = {}
    for line in raw_num.splitlines():
        if not line.strip():
            continue
        adds, dels, path = line.split("\t", 2)
        if "\t" in path:
            _old, path = path.split("\t", 1)
        binary = adds == "-" and dels == "-"
        num[path] = (
            None if binary else int(adds),
            None if binary else int(dels),
            binary,
        )

    files: list[FileChange] = []
    parts = [part for part in raw_status.split("\0") if part]
    i = 0
    while i < len(parts):
        code = parts[i]
        i += 1
        if code.startswith(("R", "C")):
            old = parts[i]
            new = parts[i + 1]
            i += 2
            stats = num.get(new) or num.get(f"{old}\t{new}") or (None, None, False)
            files.append(
                FileChange(
                    filename=new,
                    status=_status_name(code),
                    additions=stats[0],
                    deletions=stats[1],
                    previous_filename=old,
                    binary=stats[2],
                )
            )
            continue
        path = parts[i]
        i += 1
        stats = num.get(path) or (None, None, False)
        files.append(
            FileChange(
                filename=path,
                status=_status_name(code),
                additions=stats[0],
                deletions=stats[1],
                binary=stats[2],
            )
        )
    return files


def merge_diff(repo: Path, merge: MergeCommit) -> str:
    spec = f"{merge.base_sha}...{merge.head_sha}"
    return run_git(repo, "diff", "--binary", "--find-renames", spec)


def paths_mentioned_in_diff(diff_text: str) -> set[str]:
    paths: set[str] = set()
    for match in DIFF_GIT.finditer(diff_text or ""):
        left, right = match.group(1), match.group(2)
        if left != "/dev/null":
            paths.add(left)
        if right != "/dev/null":
            paths.add(right)
    for match in RENAME_FROM.finditer(diff_text or ""):
        paths.add(match.group(1))
    for match in BINARY_LINE.finditer(diff_text or ""):
        for side in match.groups():
            cleaned = side.replace("a/", "", 1).replace("b/", "", 1)
            if cleaned != "/dev/null":
                paths.add(cleaned)
    return paths
