"""Collect and sanitize pull-request review surfaces from GitHub."""

from __future__ import annotations

from typing import Any

import urllib.request

from oba_revieweval.dataset.github import (
    GitHubAPIError,
    GitHubClient,
    USER_AGENT,
    actor_from_user,
    cache_path_for,
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
                "previous_filename": item.get("previous_filename"),
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


def collect_review_surfaces(
    client: GitHubClient,
    number: int,
    *,
    owner: str = "OneBusAway",
    repo: str = "maglev",
) -> dict[str, Any]:
    """Reviews and comments only. Files/diffs come from the merge SHA."""
    base = f"/repos/{owner}/{repo}/pulls/{number}"
    pr: dict[str, Any] = {}
    try:
        pr = require_mapping(client.request_json(base), context=f"pulls/{number}")
    except GitHubAPIError:
        pr = {}

    def _optional_list(path: str) -> list[Any] | None:
        try:
            return client.paginate(path)
        except GitHubAPIError:
            return None

    reviews_raw = _optional_list(f"{base}/reviews")
    inline_raw = _optional_list(f"{base}/comments")
    issue_raw = _optional_list(f"/repos/{owner}/{repo}/issues/{number}/comments")
    if reviews_raw is None:
        raise GitHubAPIError(f"reviews missing for {number}")
    if inline_raw is None:
        raise GitHubAPIError(f"review comments missing for {number}")
    if issue_raw is None:
        raise GitHubAPIError(f"issue comments missing for {number}")

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
    user = pr.get("user") if pr else None
    author_login, author_type = actor_from_user(user) if user else (None, None)
    return {
        "title": pr.get("title"),
        "state": pr.get("state"),
        "merged": bool(pr.get("merged") or pr.get("merged_at")) if pr else True,
        "merge_sha": pr.get("merge_commit_sha"),
        "author": author_login,
        "author_type": author_type,
        "html_url": pr.get("html_url"),
        "reviews": reviews,
        "review_count": len(reviews),
        "review_bodies": review_bodies,
        "inline_comments": [
            _comment_record(require_mapping(r, context="inline[]"), source="inline", inline=True)
            for r in inline_raw
        ],
        "issue_comments": [
            _comment_record(require_mapping(r, context="issue[]"), source="issue")
            for r in issue_raw
        ],
    }


def files_from_unified_diff(diff_text: str) -> list[dict[str, Any]]:
    """Derive a changed-file list from a GitHub unified diff."""
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in (diff_text or "").splitlines():
        if line.startswith("diff --git "):
            if current:
                files.append(current)
            parts = line.split(" ")
            left = parts[2][2:] if len(parts) >= 3 and parts[2].startswith("a/") else ""
            right = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else ""
            current = {
                "filename": right or left,
                "status": "modified",
                "additions": None,
                "deletions": None,
                "previous_filename": left if left and right and left != right else None,
            }
            continue
        if current is None:
            continue
        if line.startswith("new file mode"):
            current["status"] = "added"
        elif line.startswith("deleted file mode"):
            current["status"] = "removed"
        elif line.startswith("rename from "):
            current["status"] = "renamed"
            current["previous_filename"] = line[len("rename from ") :]
        elif line.startswith("rename to "):
            current["filename"] = line[len("rename to ") :]
    if current:
        files.append(current)
    return files


def collect_github_file_metadata(
    client: GitHubClient,
    number: int,
    *,
    owner: str = "OneBusAway",
    repo: str = "maglev",
) -> list[dict[str, Any]]:
    """GitHub's PR file list. Used only to check reconstruction coverage."""
    try:
        files_raw = client.paginate(f"/repos/{owner}/{repo}/pulls/{number}/files")
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
                    "previous_filename": item.get("previous_filename"),
                    "source": "github_files_api",
                }
            )
        return files
    except GitHubAPIError:
        diff_text = fetch_public_pr_diff(client, number, owner=owner, repo=repo)
        files = files_from_unified_diff(diff_text)
        for item in files:
            item["source"] = "github_pull_diff"
        if not files:
            raise GitHubAPIError(f"github files unavailable for {number}")
        return files


def fetch_public_pr_diff(
    client: GitHubClient,
    number: int,
    *,
    owner: str = "OneBusAway",
    repo: str = "maglev",
) -> str:
    url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
    if client.cache_dir is not None:
        cached = cache_path_for(client.cache_dir, url, suffix=".diff")
        if cached.is_file():
            return cached.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - surface as API error
        raise GitHubAPIError(f"public PR diff failed for {number}") from exc
    if client.cache_dir is not None:
        client.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path_for(client.cache_dir, url, suffix=".diff").write_text(text, encoding="utf-8")
    return text


def fetch_diff(client: GitHubClient, number: int, *, owner: str = "OneBusAway", repo: str = "maglev") -> str:
    path = f"/repos/{owner}/{repo}/pulls/{number}"
    raw = client.request_json(path, accept="application/vnd.github.diff", raw=True)
    if not isinstance(raw, (bytes, bytearray)):
        raise GitHubAPIError("diff: expected bytes")
    return raw.decode("utf-8")
