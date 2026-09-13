"""In-memory GitHub payloads for collector tests. Not live API data."""

from __future__ import annotations

from typing import Any


def pr_payload(
    number: int = 702,
    *,
    title: str = "extract withTransaction",
    merged: bool = True,
    merge_sha: str = "abc123def456",
    author: str = "tejasva-vardhan",
    author_type: str = "User",
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "state": "closed",
        "merged": merged,
        "merge_commit_sha": merge_sha,
        "html_url": f"https://github.com/OneBusAway/maglev/pull/{number}",
        "user": {"login": author, "type": author_type},
    }


def file_payload(filename: str = "internal/gtfs/import.go") -> dict[str, Any]:
    return {
        "filename": filename,
        "status": "modified",
        "additions": 12,
        "deletions": 4,
    }


ROUTES = {
    "/repos/OneBusAway/maglev/pulls/702": pr_payload(),
    "/repos/OneBusAway/maglev/pulls/702/files": [file_payload()],
    "/repos/OneBusAway/maglev/pulls/702/reviews": [
        {
            "id": 11,
            "user": {"login": "aaronbrethorst", "type": "User"},
            "state": "COMMENTED",
            "body": "Can the helper roll back if the callback returns an error?",
            "submitted_at": "2025-01-01T00:00:00Z",
        }
    ],
    "/repos/OneBusAway/maglev/pulls/702/comments": [],
    "/repos/OneBusAway/maglev/issues/702/comments": [
        {
            "id": 21,
            "user": {"login": "tejasva-vardhan", "type": "User"},
            "body": "I will extract the helper in a follow-up if this looks right.",
            "created_at": "2025-01-01T00:01:00Z",
        }
    ],
    "/repos/OneBusAway/maglev/pulls/900": pr_payload(
        900, title="docs only", author="someone", merge_sha="ddd"
    ),
    "/repos/OneBusAway/maglev/pulls/900/files": [file_payload("README.md")],
    "/repos/OneBusAway/maglev/pulls/900/reviews": [],
    "/repos/OneBusAway/maglev/pulls/900/comments": [],
    "/repos/OneBusAway/maglev/issues/900/comments": [
        {
            "id": 31,
            "user": {"login": "coderabbitai[bot]", "type": "Bot"},
            "body": "Walkthrough",
            "created_at": "2025-01-01T00:00:00Z",
        }
    ],
}


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeOpener:
    def __init__(self, routes: dict[str, object] | None = None) -> None:
        self.routes = routes if routes is not None else dict(ROUTES)
        self.urls: list[str] = []

    def open(self, req: object) -> FakeResponse:
        import json
        from urllib.parse import urlparse, parse_qs

        full = getattr(req, "full_url", "")
        self.urls.append(full)
        parsed = urlparse(full)
        path = parsed.path
        if parsed.query:
            qs = parse_qs(parsed.query)
            # collector paginate appends per_page/page; strip for lookup
            if "per_page" in qs:
                path = parsed.path
        accept = ""
        if hasattr(req, "headers"):
            accept = req.headers.get("Accept") or req.headers.get("accept") or ""
        if "diff" in accept:
            return FakeResponse(b"diff --git a/a.go b/a.go\n", "text/plain")
        if path not in self.routes:
            raise AssertionError(f"unexpected path {path}")
        payload = self.routes[path]
        return FakeResponse(json.dumps(payload).encode("utf-8"))
