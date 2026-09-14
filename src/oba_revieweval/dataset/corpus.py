"""Complete n=33 raw-export construction and validation.

Does not change the frozen protocol. Phase 5 labels are not assigned.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from oba_revieweval.dataset.actors import is_forbidden_gold_author
from oba_revieweval.dataset.collect import collect_github_file_metadata, collect_review_surfaces
from oba_revieweval.dataset.eligibility import evaluate_eligibility
from oba_revieweval.dataset.export import write_pr_export
from oba_revieweval.dataset.extract import extract_rows, partition_rows, write_extracted_csv
from oba_revieweval.dataset.git_anchor import (
    GitAnchorError,
    first_parent_paths,
    list_changed_files,
    merge_diff,
    paths_mentioned_in_diff,
    resolve_merge_commit,
)
from oba_revieweval.dataset.github import GitHubAPIError, GitHubClient

MANIFEST_FIELDS = [
    "pr_number",
    "merge_sha",
    "stratum",
    "author",
    "changed_file_count",
    "diff_available",
    "reviews_available",
    "issue_comments_available",
    "independent_human_review",
    "export_complete",
    "export_error",
]

REQUIRED_RAW_FILES = (
    "metadata.json",
    "diff.patch",
    "files.json",
    "github_files.json",
    "reviews.json",
    "comments.json",
)

REQUIRED_EXTRACT_FILES = (
    "all_comments_unlabeled.csv",
    "human_independent_unlabeled.csv",
    "human_meaningful_unlabeled.csv",
    "process_only.csv",
    "bot_comments.csv",
    "author_comments.csv",
    "partition_summary.json",
)


def load_recommended(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 33:
        raise ValueError(f"recommended corpus must have 33 rows, found {len(rows)}")
    return rows


def _write_extract(extract_dir: Path, collected: dict[str, Any]) -> dict[str, int]:
    rows = extract_rows(collected)
    groups = partition_rows(rows)
    write_extracted_csv(extract_dir / "all_comments_unlabeled.csv", rows)
    write_extracted_csv(extract_dir / "human_independent_unlabeled.csv", groups["human"])
    write_extracted_csv(extract_dir / "human_meaningful_unlabeled.csv", groups["human_meaningful"])
    write_extracted_csv(extract_dir / "process_only.csv", groups["process_only"])
    write_extracted_csv(extract_dir / "bot_comments.csv", groups["bot"])
    write_extracted_csv(extract_dir / "author_comments.csv", groups["author"])
    summary = {
        "pr_number": collected.get("pr_number"),
        "n_all": len(rows),
        "n_independent_human": len(groups["human"]),
        "n_human_meaningful": len(groups["human_meaningful"]),
        "n_process_only": len(groups["process_only"]),
        "n_bot": len(groups["bot"]),
        "n_author": len(groups["author"]),
        "n_study_author": len(groups["study_author"]),
        "labels_assigned": False,
    }
    (extract_dir / "partition_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def export_recommended_pr(
    row: dict[str, str],
    *,
    repo: Path,
    client: GitHubClient,
    dest_root: Path,
    extract_root: Path,
    collected_at: str | None = None,
) -> dict[str, Any]:
    number = int(row["pr_number"])
    expected_sha = (row.get("merge_sha") or "").strip()
    errors: list[str] = []
    collected_at = collected_at or date.today().isoformat()

    try:
        merge = resolve_merge_commit(repo, expected_sha)
    except GitAnchorError as exc:
        merge = None
        errors.append(f"merge_sha_unresolved:{exc}")

    files: list[dict[str, Any]] = []
    diff_text = ""
    if merge is not None:
        if merge.merge_sha.lower() != expected_sha.lower():
            errors.append("merge_sha_resolved_alias")
        files = [item.as_dict() for item in list_changed_files(repo, merge)]
        diff_text = merge_diff(repo, merge)
        if not files:
            errors.append("empty_changed_file_list")
        if not diff_text.strip().startswith("diff --git"):
            errors.append("diff_missing_or_not_unified")
        mentioned = paths_mentioned_in_diff(diff_text)
        for item in files:
            name = item["filename"]
            prev = item.get("previous_filename")
            if name not in mentioned and prev not in mentioned:
                if item.get("binary"):
                    continue
                errors.append(f"file_missing_from_diff:{name}")
        landed = set(first_parent_paths(repo, merge)) if merge.parents else set()
        if merge.diff_mode == "merge_parents_three_dot" and not landed:
            # Merge brought no first-parent delta (already on main). The
            # three-dot range of this merge commit's parents is still used.
            pass

    github: dict[str, Any] | None = None
    reviews_available = False
    issue_comments_available = False
    try:
        github = collect_review_surfaces(client, number)
        reviews_available = True
        issue_comments_available = True
        if github.get("merge_sha") and expected_sha and github["merge_sha"] != expected_sha:
            errors.append(f"github_merge_sha_mismatch:{github['merge_sha']}")
    except GitHubAPIError as exc:
        errors.append(f"github_surface_incomplete:{exc}")

    github_files: list[dict[str, Any]] = []
    try:
        github_files = collect_github_file_metadata(client, number)
        reconstructed_names = {item["filename"] for item in files}
        reconstructed_names.update(
            item["previous_filename"] for item in files if item.get("previous_filename")
        )
        for item in github_files:
            name = item.get("filename")
            prev = item.get("previous_filename")
            if name not in reconstructed_names and prev not in reconstructed_names:
                errors.append(f"github_file_missing_from_reconstructed:{name}")
    except GitHubAPIError as exc:
        errors.append(f"github_files_unavailable:{exc}")

    author = row.get("author") or (github or {}).get("author")
    collected = {
        "repo": "OneBusAway/maglev",
        "pr_number": number,
        "title": (github or {}).get("title") or row.get("title"),
        "state": (github or {}).get("state") or "closed",
        "merged": True,
        "merge_sha": expected_sha,
        "author": author,
        "author_type": (github or {}).get("author_type") or "User",
        "html_url": f"https://github.com/OneBusAway/maglev/pull/{number}",
        "changed_files": [item["filename"] for item in files],
        "changed_file_count": len(files),
        "change_kind": "code",
        "review_count": (github or {}).get("review_count") or 0,
        "files": files,
        "reviews": (github or {}).get("reviews") or [],
        "review_bodies": (github or {}).get("review_bodies") or [],
        "inline_comments": (github or {}).get("inline_comments") or [],
        "issue_comments": (github or {}).get("issue_comments") or [],
    }
    if merge is not None:
        collected["diff_mode"] = merge.diff_mode
        collected["diff_base_sha"] = merge.base_sha
        collected["diff_head_sha"] = merge.head_sha
        collected["merge_parents"] = list(merge.parents)

    dest = dest_root / str(number)
    write_pr_export(dest, collected, diff_text=diff_text, collected_at=collected_at)
    (dest / "github_files.json").write_text(
        json.dumps(github_files, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata_path = dest / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["diff_mode"] = collected.get("diff_mode")
    metadata["diff_base_sha"] = collected.get("diff_base_sha")
    metadata["diff_head_sha"] = collected.get("diff_head_sha")
    metadata["merge_parents"] = collected.get("merge_parents")
    metadata["stratum"] = row.get("stratum")
    metadata["diff_anchored_to_merge_sha"] = True
    metadata["github_file_count"] = len(github_files)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    extract_summary = _write_extract(extract_root / str(number), collected)
    decision = evaluate_eligibility(collected, stratum=row.get("stratum") or "")
    independent = bool(decision.get("independent_human_review_present"))
    if not independent:
        errors.append("independent_human_review_missing")
    if is_forbidden_gold_author(author) and not independent:
        errors.append("author_pr_without_independent_human")

    complete = (
        not errors
        and bool(files)
        and bool(diff_text.strip())
        and reviews_available
        and issue_comments_available
        and independent
    )
    return {
        "pr_number": number,
        "merge_sha": expected_sha,
        "stratum": row.get("stratum"),
        "author": author,
        "changed_file_count": len(files),
        "diff_available": bool(diff_text.strip()),
        "reviews_available": reviews_available,
        "issue_comments_available": issue_comments_available,
        "independent_human_review": independent,
        "export_complete": complete,
        "export_error": ";".join(errors),
        "n_independent_human": extract_summary.get("n_independent_human"),
    }


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_pr_export(
    dest: Path,
    extract_dir: Path,
    *,
    expected_sha: str,
    author: str,
) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_RAW_FILES:
        if not (dest / name).is_file():
            errors.append(f"missing_raw:{name}")
    for name in REQUIRED_EXTRACT_FILES:
        if not (extract_dir / name).is_file():
            errors.append(f"missing_extract:{name}")
    if errors:
        return errors

    metadata = json.loads((dest / "metadata.json").read_text(encoding="utf-8"))
    files = json.loads((dest / "files.json").read_text(encoding="utf-8"))
    reviews = json.loads((dest / "reviews.json").read_text(encoding="utf-8"))
    comments = json.loads((dest / "comments.json").read_text(encoding="utf-8"))
    diff_text = (dest / "diff.patch").read_text(encoding="utf-8")

    if metadata.get("merge_sha") != expected_sha:
        errors.append("metadata_merge_sha_mismatch")
    if not metadata.get("diff_anchored_to_merge_sha"):
        errors.append("diff_not_anchored")
    if not files:
        errors.append("files_json_empty")
    if metadata.get("changed_file_count") != len(files):
        errors.append("changed_file_count_mismatch")
    if not diff_text.startswith("diff --git"):
        errors.append("diff_not_unified")
    mentioned = paths_mentioned_in_diff(diff_text)
    for item in files:
        name = item.get("filename")
        prev = item.get("previous_filename")
        if item.get("binary"):
            continue
        if name not in mentioned and prev not in mentioned:
            errors.append(f"file_not_in_diff:{name}")
    if not isinstance(reviews, list):
        errors.append("reviews_not_list")
    if not {"issue_comments", "inline_comments", "review_bodies"} <= set(comments):
        errors.append("comments_missing_keys")
    github_files = json.loads((dest / "github_files.json").read_text(encoding="utf-8"))
    reconstructed_names = {item.get("filename") for item in files}
    reconstructed_names.update(
        item.get("previous_filename") for item in files if item.get("previous_filename")
    )
    for item in github_files:
        name = item.get("filename")
        prev = item.get("previous_filename")
        if name not in reconstructed_names and prev not in reconstructed_names:
            errors.append(f"github_file_not_reconstructed:{name}")
    inline = comments.get("inline_comments") or []
    if not isinstance(inline, list):
        errors.append("inline_comments_not_list")
    if not isinstance(comments.get("issue_comments"), list):
        errors.append("issue_comments_not_list")
    for item in inline:
        if item.get("id") is None:
            errors.append("inline_comment_missing_id")
            break

    with (extract_dir / "human_independent_unlabeled.csv").open(encoding="utf-8", newline="") as handle:
        human_rows = list(csv.DictReader(handle))
    if not human_rows:
        errors.append("no_independent_human_partition")
    if any(is_forbidden_gold_author(row.get("author_login")) for row in human_rows):
        errors.append("study_author_in_human_gold")
    if any((row.get("author_login") or "").lower() == author.lower() for row in human_rows):
        errors.append("pr_author_in_human_gold")
    if any(row.get("class") for row in human_rows):
        errors.append("labels_assigned_too_early")
    if any(row.get("in_reference_set") == "true" for row in human_rows):
        errors.append("reference_set_assigned_too_early")

    with (extract_dir / "process_only.csv").open(encoding="utf-8", newline="") as handle:
        process_rows = list(csv.DictReader(handle))
    with (extract_dir / "human_meaningful_unlabeled.csv").open(encoding="utf-8", newline="") as handle:
        meaningful = list(csv.DictReader(handle))
    process_ids = {row.get("comment_id") for row in process_rows}
    if process_ids & {row.get("comment_id") for row in meaningful}:
        errors.append("process_only_mixed_into_meaningful")
    return errors


def validate_recommended_corpus(
    recommended: list[dict[str, str]],
    dest_root: Path,
    extract_root: Path,
) -> list[dict[str, Any]]:
    rows = []
    for item in recommended:
        number = int(item["pr_number"])
        errors = validate_pr_export(
            dest_root / str(number),
            extract_root / str(number),
            expected_sha=item["merge_sha"],
            author=item["author"],
        )
        rows.append(
            {
                "pr_number": number,
                "merge_sha": item["merge_sha"],
                "complete": not errors,
                "errors": errors,
            }
        )
    return rows


def corpus_is_complete(results: list[dict[str, Any]]) -> bool:
    return bool(results) and all(row["complete"] for row in results) and len(results) == 33
