"""Merge-SHA-anchored title, diff, and bounded file excerpts.

Never reads comments.json, reviews.json, human labels, or linter findings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from oba_revieweval.lint.parse import normalize_repo_path
from oba_revieweval.lint.runner import default_maglev, default_worktree, ensure_worktree, worktree_head
from oba_revieweval.models.prompt import build_user_message

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
DIFF_GIT = re.compile(r"^diff --git a/(.+?) b/(.+)$")


class ContextError(ValueError):
    """Raised when the merge-anchored review context cannot be built."""


def load_pr_bundle(raw_pr_dir: Path) -> dict[str, Any]:
    metadata_path = raw_pr_dir / "metadata.json"
    diff_path = raw_pr_dir / "diff.patch"
    files_path = raw_pr_dir / "files.json"
    if not metadata_path.exists() or not diff_path.exists():
        raise ContextError(f"missing merge-anchored export in {raw_pr_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    files = json.loads(files_path.read_text(encoding="utf-8")) if files_path.exists() else []
    return {
        "metadata": metadata,
        "diff": diff_path.read_text(encoding="utf-8", errors="replace"),
        "files": files,
    }


def parse_new_hunks(diff: str) -> dict[str, list[tuple[int, int]]]:
    current = ""
    hunks: dict[str, list[tuple[int, int]]] = {}
    for line in (diff or "").splitlines():
        header = DIFF_GIT.match(line)
        if header:
            current = normalize_repo_path(header.group(2))
            hunks.setdefault(current, [])
            continue
        match = HUNK.match(line)
        if match and current:
            start = int(match.group(3))
            count = int(match.group(4) or "1")
            hunks.setdefault(current, []).append((start, count))
    return hunks


def excerpt_window(hunks: list[tuple[int, int]], file_len: int, cap: int) -> tuple[int, int] | None:
    lines: list[int] = []
    for start, count in hunks:
        if start <= 0:
            continue
        end = start + max(count, 1) - 1
        lines.extend(range(start, end + 1))
    if not lines or file_len <= 0:
        return None
    lo = max(1, min(lines) - 20)
    hi = min(file_len, max(lines) + 20)
    if hi - lo + 1 <= cap:
        return lo, hi
    mid = (min(lines) + max(lines)) // 2
    lo = max(1, mid - cap // 2)
    hi = min(file_len, lo + cap - 1)
    lo = max(1, hi - cap + 1)
    return lo, hi


def collect_excerpts(
    *,
    worktree: Path,
    diff: str,
    cap: int,
) -> list[dict[str, Any]]:
    hunks_by_file = parse_new_hunks(diff)
    excerpts: list[dict[str, Any]] = []
    for path, hunks in hunks_by_file.items():
        if not path.endswith(".go"):
            continue
        file_path = worktree / path
        if not file_path.is_file():
            continue
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        window = excerpt_window(hunks, len(lines), cap)
        if window is None:
            continue
        lo, hi = window
        body = "\n".join(lines[lo - 1 : hi])
        excerpts.append(
            {
                "path": path,
                "start_line": lo,
                "end_line": hi,
                "text": body,
            }
        )
    return excerpts


def build_review_context(
    *,
    pr_number: int,
    merge_sha: str,
    raw_pr_dir: Path,
    repo: Path | None = None,
    worktree: Path | None = None,
    surrounding_lines: int = 200,
) -> dict[str, Any]:
    bundle = load_pr_bundle(raw_pr_dir)
    metadata = bundle["metadata"]
    recorded = (metadata.get("merge_sha") or "").strip()
    if recorded and recorded.lower() != merge_sha.lower():
        raise ContextError(f"#{pr_number}: metadata merge_sha {recorded} != {merge_sha}")
    title = str(metadata.get("title") or "")
    diff = bundle["diff"]
    repo = repo or default_maglev()
    worktree = worktree or default_worktree()
    ensure_worktree(repo, worktree, merge_sha)
    head = worktree_head(worktree)
    if head.lower() != merge_sha.lower():
        raise ContextError(f"#{pr_number}: worktree {head} != {merge_sha}")
    excerpts = collect_excerpts(worktree=worktree, diff=diff, cap=surrounding_lines)
    user_message = build_user_message(
        title=title,
        diff=diff,
        excerpts=[(item["path"], item["text"]) for item in excerpts],
    )
    changed = [str(item.get("filename") or "") for item in bundle["files"]]
    return {
        "pr_number": pr_number,
        "title": title,
        "commit_sha": merge_sha,
        "diff": diff,
        "changed_files": changed,
        "excerpts": excerpts,
        "user_message": user_message,
        "user_message_chars": len(user_message),
        "surrounding_lines_per_file": surrounding_lines,
    }
