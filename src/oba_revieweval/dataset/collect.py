"""Collect and sanitize pull-request review surfaces from GitHub."""

from __future__ import annotations

from typing import Any

from oba_revieweval.dataset.github import (
    GitHubAPIError,
    GitHubClient,
    actor_from_user,
    require_list,
    require_mapping,
    sanitize_user,
)

DOC_SUFFIXES = (".md", ".txt", ".rst")
LOCKFILE_NAMES = frozenset({"go.mod", "go.sum", "package-lock.json", "yarn.lock"})


def _comment_record(
    payload: dict[str, Any],
    *,
    source: str,
    inline: bool = False,
) -> dict[str, Any]:
    login, user_type = actor_from_user(payload.get("user"))
    body = payload.get("body")
    if body is not None and not isinstance(body, str):
        raise GitHubAPIError(f"{source} comment body: expected string")
    rec: dict[str, Any] = {
        "id": payload.get("id"),
        "source": source,
        "login": login,
        "user_type": user_type,
        "body": body or "",
        "inline": inline,
        "path": payload.get("path") if inline else None,
        "line": payload.get("line") if inline else None,
        "created_at": payload.get("created_at") or payload.get("submitted_at"),
    }
    return rec


def _is_docs_or_openapi(path: str) -> bool:
    low = path.lower()
    if low.endswith(DOC_SUFFIXES):
        return True
    return low.endswith((".yml", ".yaml")) and "openapi" in low


def classify_change_kind(filenames: list[str]) -> str:
    if not filenames:
        return "empty"
    names = [f.replace("\\", "/") for f in filenames]
    bases = [n.split("/")[-1] for n in names]
    if all(_is_docs_or_openapi(n) for n in names):
        return "docs_or_openapi"
    if all(base in LOCKFILE_NAMES for base in bases):
        return "dependency_only"
    if not any(n.endswith(".go") or n.endswith(".sql") for n in names):
        return "no_go_or_sql"
    return "code"


def collect_pull_request(
    client: GitHubClient,
    number: int,
    *,
    owner: str = "OneBusAway",
    repo: str = "maglev",
) -> dict[str, Any]:
    base = f"/repos/{owner}/{repo}/pulls/{number}"
    pr = require_mapping(client.request_json(base), context=f"pulls/{number}")
    files_raw = client.paginate(f"{base}/files")
    reviews_raw = client.paginate(f"{base}/reviews")
    inline_raw = client.paginate(f"{base}/comments")
    issue_raw = client.paginate(f"/repos/{owner}/{repo}/issues/{number}/comments")

    files = []
    for row in files_raw:
        item = require_mapping(row, context="files[]")
        filename = item.get("filename")
        if not isinstance(filename, str):
            raise GitHubAPIError("files[].filename missing")
        files.append(
            {
                "filename": filename,
                "status": item.get("status"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
            }
        )

    reviews = []
    review_bodies = []
    for row in reviews_raw:
        item = require_mapping(row, context="reviews[]")
        login, user_type = actor_from_user(item.get("user"))
        body = item.get("body") or ""
        if not isinstance(body, str):
            raise GitHubAPIError("reviews[].body expected string")
        reviews.append(
            {
                "id": item.get("id"),
                "login": login,
                "user_type": user_type,
                "state": item.get("state"),
                "body": body,
                "submitted_at": item.get("submitted_at"),
            }
        )
        review_bodies.append(
            {
                "id": item.get("id"),
                "source": "review_body",
                "login": login,
                "user_type": user_type,
                "body": body,
                "inline": False,
                "path": None,
                "line": None,
                "created_at": item.get("submitted_at"),
            }
        )

    comments = [_comment_record(require_mapping(r, context="inline[]"), source="inline", inline=True) for r in inline_raw]
    issue_comments = [_comment_record(require_mapping(r, context="issue[]"), source="issue") for r in issue_raw]

    user = pr.get("user")
    author_login, author_type = actor_from_user(user)
    filenames = [f["filename"] for f in files]
    return {
        "repo": f"{owner}/{repo}",
        "pr_number": pr.get("number", number),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": bool(pr.get("merged")) or bool(pr.get("merged_at")),
        "merge_sha": pr.get("merge_commit_sha"),
        "author": author_login,
        "author_type": author_type,
        "html_url": pr.get("html_url"),
        "changed_files": filenames,
        "changed_file_count": len(filenames),
        "change_kind": classify_change_kind(filenames),
        "files": files,
        "reviews": reviews,
        "review_count": len(reviews),
        "review_bodies": review_bodies,
        "inline_comments": comments,
        "issue_comments": issue_comments,
        "user": sanitize_user(user),
    }


def fetch_diff(client: GitHubClient, number: int, *, owner: str = "OneBusAway", repo: str = "maglev") -> str:
    path = f"/repos/{owner}/{repo}/pulls/{number}"
    raw = client.request_json(path, accept="application/vnd.github.diff", raw=True)
    if not isinstance(raw, (bytes, bytearray)):
        raise GitHubAPIError("diff: expected bytes")
    return raw.decode("utf-8")
