"""GitHub REST client for public Maglev pull-request export.

Never logs or returns the token. Malformed payloads raise GitHubAPIError.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_OWNER = "OneBusAway"
DEFAULT_REPO = "maglev"
API_VERSION = "2022-11-28"
USER_AGENT = "oba-revieweval-phase4 (research-export; no-token-logging)"


class GitHubAPIError(ValueError):
    """Raised for missing fields, bad JSON, or HTTP errors."""


def load_token(env: dict[str, str] | None = None, dotenv_path: Path | None = None) -> str | None:
    source = env if env is not None else os.environ
    token = source.get("GITHUB_TOKEN") or source.get("GH_TOKEN")
    if token:
        return token.strip() or None
    path = dotenv_path
    if path is None:
        path = Path(__file__).resolve().parents[3] / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() in {"GITHUB_TOKEN", "GH_TOKEN"}:
                raw = value.strip().strip('"').strip("'")
                return raw or None
    return None


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_json_body(raw: bytes | str, *, context: str) -> Any:
    if raw is None:
        raise GitHubAPIError(f"{context}: empty body")
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if not text.strip():
        raise GitHubAPIError(f"{context}: empty body")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GitHubAPIError(f"{context}: malformed JSON") from exc


def require_mapping(payload: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GitHubAPIError(f"{context}: expected object")
    return payload


def require_list(payload: Any, *, context: str) -> list[Any]:
    if not isinstance(payload, list):
        raise GitHubAPIError(f"{context}: expected array")
    return payload


def cache_path_for(cache_dir: Path, path: str, *, suffix: str = ".json") -> Path:
    safe = urllib.parse.quote(path, safe="")
    return cache_dir / f"{safe}{suffix}"


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        opener: Any = None,
        api_root: str = "https://api.github.com",
        cache_dir: Path | None = None,
        cache_only: bool = False,
    ) -> None:
        self._token = token
        self._opener = opener
        self.api_root = api_root.rstrip("/")
        self.cache_dir = cache_dir
        self.cache_only = cache_only

    def request_json(
        self,
        path: str,
        *,
        accept: str | None = None,
        raw: bool = False,
    ) -> Any:
        url = path if path.startswith("http") else f"{self.api_root}{path}"
        cached_payload = self._read_cache(url, raw=raw)
        if cached_payload is not None:
            return cached_payload
        if self.cache_only:
            raise GitHubAPIError(f"cache miss for {path}")
        headers = _headers(self._token)
        if accept:
            headers["Accept"] = accept
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            if self._opener is not None:
                with self._opener.open(req) as resp:
                    body = resp.read()
                    content_type = resp.headers.get("Content-Type", "")
            else:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                    content_type = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise GitHubAPIError(f"HTTP {exc.code} for {path}") from exc
        except urllib.error.URLError as exc:
            raise GitHubAPIError(f"network error for {path}") from exc
        if raw:
            if self.cache_dir is not None:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path_for(self.cache_dir, url, suffix=".bin").write_bytes(body)
            return body
        if "json" not in content_type and not body.strip().startswith((b"{", b"[")):
            raise GitHubAPIError(f"{path}: non-JSON response")
        payload = parse_json_body(body, context=path)
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path_for(self.cache_dir, url).write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
        return payload

    def _cache_keys(self, url: str) -> list[str]:
        keys = [url]
        if "?" in url:
            keys.append(url.split("?", 1)[0])
        else:
            keys.append(f"{url}?per_page=100&page=1")
        # Preserve order while dropping duplicates.
        seen: set[str] = set()
        out: list[str] = []
        for key in keys:
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out

    def _read_cache(self, url: str, *, raw: bool) -> Any | None:
        if self.cache_dir is None:
            return None
        suffix = ".bin" if raw else ".json"
        for key in self._cache_keys(url):
            cached = cache_path_for(self.cache_dir, key, suffix=suffix)
            if not cached.is_file():
                continue
            if raw:
                return cached.read_bytes()
            return parse_json_body(cached.read_text(encoding="utf-8"), context=url)
        return None

    def paginate(self, path: str, *, per_page: int = 100) -> list[Any]:
        items: list[Any] = []
        page = 1
        while True:
            sep = "&" if "?" in path else "?"
            chunk = self.request_json(f"{path}{sep}per_page={per_page}&page={page}")
            rows = require_list(chunk, context=path)
            items.extend(rows)
            if len(rows) < per_page:
                break
            page += 1
            if page > 50:
                raise GitHubAPIError(f"{path}: pagination exceeded safety cap")
        return items


def actor_from_user(user: Any) -> tuple[str | None, str | None]:
    if user is None:
        return None, None
    if not isinstance(user, dict):
        raise GitHubAPIError("user: expected object or null")
    login = user.get("login")
    user_type = user.get("type")
    if login is not None and not isinstance(login, str):
        raise GitHubAPIError("user.login: expected string")
    if user_type is not None and not isinstance(user_type, str):
        raise GitHubAPIError("user.type: expected string")
    return login, user_type


def sanitize_user(user: Any) -> dict[str, str] | None:
    login, user_type = actor_from_user(user)
    if login is None and user_type is None:
        return None
    out: dict[str, str] = {}
    if login is not None:
        out["login"] = login
    if user_type is not None:
        out["type"] = user_type
    return out
