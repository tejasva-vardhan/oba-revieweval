"""Run LLM A on merge-SHA-anchored PR context."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from oba_revieweval.dataset.corpus import load_recommended
from oba_revieweval.lint.aggregate import write_lint_csv
from oba_revieweval.models.artifacts import artifact_has_secret, write_json, write_text
from oba_revieweval.models.client import OpenAIChatClient
from oba_revieweval.models.constants import (
    FINDING_FIELDS,
    MANIFEST_FIELDS,
    PILOT_PRS,
    load_llm_a_config,
    repo_root,
)
from oba_revieweval.models.context import build_review_context
from oba_revieweval.models.parse import (
    ModelParseError,
    assign_stable_ids,
    findings_from_issues,
    parse_model_json,
)
from oba_revieweval.models.prompt import PROMPT_ID, load_system_prompt, prompt_hash
from oba_revieweval.models.secrets import load_openai_api_key


def estimate_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    *,
    input_usd_per_million: float,
    output_usd_per_million: float,
) -> float:
    return (
        prompt_tokens / 1_000_000 * input_usd_per_million
        + completion_tokens / 1_000_000 * output_usd_per_million
    )


def analyze_pr(
    *,
    pr_number: int,
    merge_sha: str,
    client: OpenAIChatClient,
    config: dict[str, Any],
    secret: str,
    dest_dir: Path,
    raw_pr_dir: Path,
    system_prompt: str,
    prompt_digest: str,
) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    context = build_review_context(
        pr_number=pr_number,
        merge_sha=merge_sha,
        raw_pr_dir=raw_pr_dir,
        surrounding_lines=int(config.get("surrounding_lines_per_file") or 200),
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context["user_message"]},
    ]
    request_meta = {
        "pr_number": pr_number,
        "commit_sha": merge_sha,
        "endpoint": config["endpoint"],
        "requested_model": config["model"],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "response_format": config.get("response_format"),
        "prompt_id": PROMPT_ID,
        "prompt_hash": prompt_digest,
        "surrounding_lines_per_file": context["surrounding_lines_per_file"],
        "excerpt_files": [
            {
                "path": item["path"],
                "start_line": item["start_line"],
                "end_line": item["end_line"],
            }
            for item in context["excerpts"]
        ],
        "user_message_chars": context["user_message_chars"],
        "changed_files": context["changed_files"],
        "messages": messages,
        "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    write_json(dest_dir / "request.json", request_meta, secret)

    result = client.complete(messages)
    write_json(dest_dir / "raw_response.json", result.raw, secret)
    write_text(dest_dir / "raw.txt", result.text, secret)

    parse_error = ""
    parse_status = "ok"
    issues = []
    if result.error:
        parse_status = "api_error"
        parse_error = result.error
    elif not result.text.strip():
        parse_status = "empty"
        parse_error = "empty model output"
    else:
        try:
            issues = parse_model_json(result.text)
        except ModelParseError as exc:
            parse_status = "malformed"
            parse_error = str(exc)

    findings = assign_stable_ids(
        findings_from_issues(
            issues,
            pr_number=pr_number,
            commit_sha=merge_sha,
            tool=str(config.get("tool") or "llm_a"),
            tool_version=result.model or config["model"],
        )
    )
    changed = {path.replace("\\", "/") for path in context["changed_files"] if path}
    for row in findings:
        row["path_in_changed_files"] = "true" if row["file"] in changed else "false"

    if result.error:
        status = "failed"
    elif parse_status == "malformed":
        status = "parse_error"
    else:
        status = "ok"

    cost = estimate_cost_usd(
        result.prompt_tokens,
        result.completion_tokens,
        input_usd_per_million=float(config.get("input_usd_per_million") or 0),
        output_usd_per_million=float(config.get("output_usd_per_million") or 0),
    )
    run = {
        "pr_number": pr_number,
        "commit_sha": merge_sha,
        "tool": config.get("tool") or "llm_a",
        "requested_model": config["model"],
        "tool_version": result.model or config["model"],
        "prompt_id": PROMPT_ID,
        "prompt_hash": prompt_digest,
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "date_utc": request_meta["date_utc"],
        "execution_status": status,
        "parse_status": parse_status,
        "parse_error": parse_error,
        "finding_count": len(findings),
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "estimated_cost_usd": round(cost, 6),
        "retried": result.retried,
        "attempts": result.attempts,
        "request_id": result.request_id,
        "user_message_chars": context["user_message_chars"],
        "excerpt_file_count": len(context["excerpts"]),
    }
    write_json(dest_dir / "run.json", run, secret)
    write_json(dest_dir / "findings.json", findings, secret)
    if parse_error:
        write_text(dest_dir / "parse_error.txt", parse_error, secret)
    leaked = artifact_has_secret(dest_dir, secret)
    if leaked:
        raise RuntimeError(f"#{pr_number}: secret leaked into {leaked}")

    manifest = {field: str(run.get(field, "")) for field in MANIFEST_FIELDS}
    manifest["retried"] = "true" if result.retried else "false"
    return {"run": run, "findings": findings, "manifest": manifest}


def run_pilot(
    *,
    prs: tuple[int, ...] = PILOT_PRS,
    dest_root: Path | None = None,
    raw_root: Path | None = None,
    client: OpenAIChatClient | None = None,
    secret: str | None = None,
) -> dict[str, Any]:
    root = repo_root()
    dest_root = dest_root or root / "data" / "raw" / "models" / "llm_a"
    raw_root = raw_root or root / "data" / "raw" / "prs"
    config = load_llm_a_config()
    system_prompt = load_system_prompt()
    digest = prompt_hash(system_prompt)
    recommended = {int(row["pr_number"]): row for row in load_recommended(root / "data" / "candidates" / "recommended_corpus.csv")}
    key = secret if secret is not None else load_openai_api_key()
    if client is None:
        client = OpenAIChatClient(
            key,
            endpoint=config["endpoint"],
            model=config["model"],
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            timeout_seconds=int(config["timeout_seconds"]),
            response_format=config.get("response_format"),
            transport_retries=int(config.get("transport_retries") or 1),
        )
    findings: list[dict[str, str]] = []
    manifest: list[dict[str, str]] = []
    for pr_number in prs:
        row = recommended.get(pr_number)
        if row is None:
            raise ValueError(f"PR #{pr_number} is not in the recommended corpus")
        print(f"llm_a #{pr_number} at {row['merge_sha']}", flush=True)
        result = analyze_pr(
            pr_number=pr_number,
            merge_sha=row["merge_sha"],
            client=client,
            config=config,
            secret=key,
            dest_dir=dest_root / str(pr_number),
            raw_pr_dir=raw_root / str(pr_number),
            system_prompt=system_prompt,
            prompt_digest=digest,
        )
        run = result["run"]
        print(
            f"  status={run['execution_status']} parse={run['parse_status']} "
            f"findings={run['finding_count']} tokens={run['total_tokens']}",
            flush=True,
        )
        findings.extend(result["findings"])
        manifest.append(result["manifest"])
    write_lint_csv(root / "data" / "llm_a_pilot_findings.csv", findings, FINDING_FIELDS)
    write_lint_csv(root / "data" / "llm_a_pilot_manifest.csv", manifest, MANIFEST_FIELDS)
    return {"findings": findings, "manifest": manifest}
