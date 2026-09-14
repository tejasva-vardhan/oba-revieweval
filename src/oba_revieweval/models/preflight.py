"""Local context-size preflight. Does not call any model API."""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

from oba_revieweval.models.constants import PILOT_PRS, load_llm_a_config, repo_root
from oba_revieweval.models.context import build_review_context
from oba_revieweval.models.prompt import load_system_prompt

# Provisional tokenizer stand-in. Not tiktoken. Not an API measurement.
CHARS_PER_TOKEN = 4
CHAT_FRAMING_CHARS = 80
MIN_LEAK_SNIPPET = 40


def approx_tokens(char_count: int) -> int:
    return max(0, math.ceil((char_count + CHAT_FRAMING_CHARS) / CHARS_PER_TOKEN))


def _bodies_from_json(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        body = value.get("body")
        if isinstance(body, str) and body.strip():
            found.append(body)
        for item in value.values():
            found.extend(_bodies_from_json(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_bodies_from_json(item))
    return found


def review_bodies(raw_pr_dir: Path) -> list[str]:
    bodies: list[str] = []
    for name in ("comments.json", "reviews.json"):
        path = raw_pr_dir / name
        if not path.is_file():
            continue
        bodies.extend(_bodies_from_json(json.loads(path.read_text(encoding="utf-8"))))
    return bodies


def csv_column_values(path: Path, column: str, pr_number: int | None = None) -> list[str]:
    if not path.is_file():
        return []
    values: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if pr_number is not None and str(row.get("pr_number") or "") != str(pr_number):
                continue
            text = (row.get(column) or "").strip()
            if text:
                values.append(text)
    return values


def leak_snippets(candidates: list[str], allowed: str) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()
    for text in candidates:
        for line in (text or "").splitlines():
            snippet = line.strip()
            if len(snippet) < MIN_LEAK_SNIPPET or snippet in allowed or snippet in seen:
                continue
            seen.add(snippet)
            snippets.append(snippet)
    return snippets


def prompt_leaks(prompt: str, snippets: list[str]) -> list[str]:
    return [snippet for snippet in snippets if snippet in prompt]


def env_secret_in_prompt(prompt: str, *names: str) -> list[str]:
    leaked: list[str] = []
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value and value in prompt:
            leaked.append(name)
    return leaked


def measure_pr(
    *,
    pr_number: int,
    merge_sha: str,
    raw_pr_dir,
    system_prompt: str,
    surrounding_lines: int,
    max_output_tokens: int,
) -> dict[str, Any]:
    context = build_review_context(
        pr_number=pr_number,
        merge_sha=merge_sha,
        raw_pr_dir=raw_pr_dir,
        surrounding_lines=surrounding_lines,
    )
    changed_go = [path for path in context["changed_files"] if str(path).endswith(".go")]
    excerpt_lines = sum(
        int(item["end_line"]) - int(item["start_line"]) + 1 for item in context["excerpts"]
    )
    input_chars = len(system_prompt) + int(context["user_message_chars"])
    input_tokens = approx_tokens(input_chars)
    prompt = system_prompt + "\n" + context["user_message"]
    allowed = context["title"] + "\n" + context["diff"] + "\n" + "\n".join(
        item["text"] for item in context["excerpts"]
    )
    root = repo_root()
    review_snips = leak_snippets(review_bodies(raw_pr_dir), allowed)
    gold_snips = leak_snippets(
        csv_column_values(root / "data" / "human_review.csv", "original_comment", pr_number)
        + csv_column_values(root / "data" / "human_review.csv", "normalized_issue", pr_number)
        + csv_column_values(root / "data" / "human_review.csv", "class", pr_number),
        allowed,
    )
    lint_snips = leak_snippets(
        csv_column_values(root / "data" / "lint_findings.csv", "message", pr_number)
        + csv_column_values(root / "data" / "lint_findings.csv", "raw_finding_id", pr_number),
        allowed,
    )
    leaks = {
        "review_comments": prompt_leaks(prompt, review_snips),
        "human_gold": prompt_leaks(prompt, gold_snips),
        "linter_findings": prompt_leaks(prompt, lint_snips),
        "env_secrets": env_secret_in_prompt(prompt, "GITHUB_TOKEN", "OPENAI_API_KEY"),
    }
    return {
        "pr_number": pr_number,
        "commit_sha": merge_sha,
        "pilot": pr_number in PILOT_PRS,
        "diff_bytes": len(context["diff"].encode("utf-8")),
        "diff_chars": len(context["diff"]),
        "changed_go_files": len(changed_go),
        "excerpt_files": len(context["excerpts"]),
        "post_merge_context_lines": excerpt_lines,
        "system_chars": len(system_prompt),
        "user_message_chars": context["user_message_chars"],
        "approx_input_tokens": input_tokens,
        "max_output_tokens": max_output_tokens,
        "estimated_max_token_usage": input_tokens + max_output_tokens,
        "leaks": leaks,
    }


def measure_corpus(recommended: list[dict[str, str]], raw_root) -> list[dict[str, Any]]:
    config = load_llm_a_config()
    system_prompt = load_system_prompt()
    rows: list[dict[str, Any]] = []
    for item in recommended:
        rows.append(
            measure_pr(
                pr_number=int(item["pr_number"]),
                merge_sha=item["merge_sha"],
                raw_pr_dir=raw_root / item["pr_number"],
                system_prompt=system_prompt,
                surrounding_lines=int(config.get("surrounding_lines_per_file") or 200),
                max_output_tokens=int(config.get("max_tokens") or 0),
            )
        )
    return rows


def provisional_cost_usd(input_tokens: int, output_tokens: int, config: dict[str, Any]) -> float:
    return (
        input_tokens / 1_000_000 * float(config.get("input_usd_per_million") or 0)
        + output_tokens / 1_000_000 * float(config.get("output_usd_per_million") or 0)
    )
