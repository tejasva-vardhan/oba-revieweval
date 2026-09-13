"""Load OPENAI_API_KEY without logging or persisting it."""

from __future__ import annotations

import os
from pathlib import Path


class MissingAPIKey(RuntimeError):
    """Raised when OPENAI_API_KEY is absent."""


def _parse_dotenv(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() != key:
            continue
        raw = value.strip().strip('"').strip("'")
        return raw or None
    return None


def load_openai_api_key(
    env: dict[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> str:
    source = env if env is not None else os.environ
    value = (source.get("OPENAI_API_KEY") or "").strip()
    if value:
        return value
    path = dotenv_path
    if path is None:
        path = Path(__file__).resolve().parents[3] / ".env"
    found = _parse_dotenv(path, "OPENAI_API_KEY")
    if found:
        return found
    raise MissingAPIKey("OPENAI_API_KEY is not set")


def redact_secret(text: str, secret: str | None) -> str:
    if not text or not secret:
        return text
    return text.replace(secret, "***REDACTED***")


def contains_secret(text: str, secret: str | None) -> bool:
    return bool(secret) and secret in (text or "")


def redact_obj(value: object, secret: str | None) -> object:
    if not secret:
        return value
    if isinstance(value, str):
        return redact_secret(value, secret)
    if isinstance(value, list):
        return [redact_obj(item, secret) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_obj(item, secret) for key, item in value.items()}
    return value
