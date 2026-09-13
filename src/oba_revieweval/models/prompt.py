"""Load the frozen prompt and build the protocol §11 user message."""

from __future__ import annotations

import hashlib
from pathlib import Path

from oba_revieweval.models.constants import repo_root

PROMPT_ID = "llm_review_v1"


def prompt_path() -> Path:
    return repo_root() / "prompts" / "llm_review_v1.md"


def load_system_prompt(path: Path | None = None) -> str:
    target = path or prompt_path()
    return target.read_text(encoding="utf-8")


def prompt_hash(text: str | None = None) -> str:
    payload = text if text is not None else load_system_prompt()
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_user_message(*, title: str, diff: str, excerpts: list[tuple[str, str]]) -> str:
    parts = [
        "1. PR title",
        title.strip() or "(untitled)",
        "",
        "2. Unified diff",
        diff.rstrip() or "(empty diff)",
        "",
        "3. Optional extra file excerpts",
    ]
    if excerpts:
        for path, body in excerpts:
            parts.append(f"### {path}")
            parts.append(body.rstrip())
            parts.append("")
    else:
        parts.append("(none)")
    return "\n".join(parts).rstrip() + "\n"


def assert_no_review_leak(text: str, forbidden: list[str]) -> list[str]:
    """Return forbidden snippets that appear in the model-facing text."""
    hits: list[str] = []
    blob = text or ""
    for item in forbidden:
        snippet = (item or "").strip()
        if len(snippet) < 24:
            continue
        if snippet in blob:
            hits.append(snippet[:80])
    return hits
