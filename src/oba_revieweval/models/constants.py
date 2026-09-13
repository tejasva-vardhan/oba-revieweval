"""Pinned LLM A identity for the Phase 6B pilot."""

from __future__ import annotations

import json
from pathlib import Path

PILOT_PRS = (1404, 702, 1428)

FINDING_FIELDS = (
    "pr_number",
    "tool",
    "tool_version",
    "commit_sha",
    "file",
    "line",
    "column",
    "rule",
    "message",
    "severity",
    "raw_finding_id",
)

MANIFEST_FIELDS = (
    "pr_number",
    "commit_sha",
    "tool",
    "tool_version",
    "prompt_id",
    "prompt_hash",
    "execution_status",
    "parse_status",
    "finding_count",
    "prompt_tokens",
    "completion_tokens",
    "retried",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_config_path() -> Path:
    return repo_root() / "configs" / "llm_a.json"


def load_llm_a_config(path: Path | None = None) -> dict:
    target = path or default_config_path()
    return json.loads(target.read_text(encoding="utf-8"))
