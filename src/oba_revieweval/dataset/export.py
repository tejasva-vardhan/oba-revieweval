"""Write a sanitized one-PR export. No tokens, emails, or profile URLs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oba_revieweval.dataset.collect import collect_pull_request, fetch_diff
from oba_revieweval.dataset.github import GitHubClient

EXPORT_VERSION = 1


def sanitize_collected(collected: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "repo",
        "pr_number",
        "title",
        "state",
        "merged",
        "merge_sha",
        "author",
        "author_type",
        "html_url",
        "changed_files",
        "changed_file_count",
        "change_kind",
        "review_count",
    }
    return {k: collected[k] for k in keep if k in collected}


def sanitize_comment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "source": row.get("source"),
        "login": row.get("login"),
        "user_type": row.get("user_type"),
        "body": row.get("body"),
        "inline": row.get("inline"),
        "path": row.get("path"),
        "line": row.get("line"),
        "created_at": row.get("created_at"),
    }


def write_pr_export(
    dest: Path,
    collected: dict[str, Any],
    *,
    diff_text: str,
    collected_at: str,
) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    metadata = sanitize_collected(collected)
    metadata["export_version"] = EXPORT_VERSION
    metadata["collected_at"] = collected_at
    metadata["source"] = "GitHub REST API"
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (dest / "files.json").write_text(
        json.dumps(collected.get("files") or [], indent=2) + "\n",
        encoding="utf-8",
    )
    (dest / "reviews.json").write_text(
        json.dumps(collected.get("reviews") or [], indent=2) + "\n",
        encoding="utf-8",
    )
    comments = {
        "issue_comments": [sanitize_comment(r) for r in collected.get("issue_comments") or []],
        "inline_comments": [sanitize_comment(r) for r in collected.get("inline_comments") or []],
        "review_bodies": [sanitize_comment(r) for r in collected.get("review_bodies") or []],
    }
    (dest / "comments.json").write_text(json.dumps(comments, indent=2) + "\n", encoding="utf-8")
    (dest / "diff.patch").write_text(diff_text, encoding="utf-8")
    return dest


def export_pr(
    client: GitHubClient,
    number: int,
    dest_root: Path,
    *,
    collected_at: str,
    owner: str = "OneBusAway",
    repo: str = "maglev",
) -> Path:
    collected = collect_pull_request(client, number, owner=owner, repo=repo)
    diff_text = fetch_diff(client, number, owner=owner, repo=repo)
    dest = dest_root / str(number)
    write_pr_export(dest, collected, diff_text=diff_text, collected_at=collected_at)
    return dest
