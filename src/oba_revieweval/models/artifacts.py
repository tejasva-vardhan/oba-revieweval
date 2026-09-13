"""Write model-run artifacts after redacting secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oba_revieweval.models.secrets import contains_secret, redact_obj, redact_secret


class SecretLeakError(RuntimeError):
    """Raised if an artifact would contain the API key."""


def write_json(path: Path, payload: object, secret: str | None) -> None:
    cleaned = redact_obj(payload, secret)
    text = json.dumps(cleaned, indent=2) + "\n"
    _assert_clean(text, secret, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str, secret: str | None) -> None:
    cleaned = redact_secret(text or "", secret)
    _assert_clean(cleaned, secret, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned, encoding="utf-8")


def _assert_clean(text: str, secret: str | None, path: Path) -> None:
    if contains_secret(text, secret):
        raise SecretLeakError(f"refusing to write API key into {path}")


def artifact_has_secret(root: Path, secret: str | None) -> list[str]:
    if not secret or not root.exists():
        return []
    leaked: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            data = path.read_bytes()
            if secret.encode("utf-8") in data:
                leaked.append(str(path))
            continue
        if contains_secret(text, secret):
            leaked.append(str(path))
    return leaked
