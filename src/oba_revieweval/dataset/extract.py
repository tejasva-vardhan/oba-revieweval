"""Turn sanitized GitHub comments into unlabeled annotation rows.

Phase 4 does not assign defect/design/style labels or TP/harmful labels.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from oba_revieweval.dataset.actors import classify_actor, is_forbidden_gold_author

EXTRACT_FIELDS = (
    "pr_id",
    "comment_id",
    "source",
    "author_login",
    "actor_class",
    "is_pr_author",
    "is_study_author",
    "eligible_as_independent_gold_candidate",
    "text",
    "path",
    "class",
    "atomic_issue_id",
    "in_reference_set",
)


def extract_rows(collected: dict[str, Any]) -> list[dict[str, str]]:
    pr_id = str(collected.get("pr_number") or "")
    pr_author = (collected.get("author") or "").lower()
    rows: list[dict[str, str]] = []
    surfaces = (
        list(collected.get("issue_comments") or [])
        + list(collected.get("inline_comments") or [])
        + list(collected.get("review_bodies") or [])
    )
    for index, item in enumerate(surfaces, start=1):
        login = item.get("login") or ""
        actor = classify_actor(login, item.get("user_type"))
        is_pr_author = login.lower() == pr_author and bool(login)
        is_study = is_forbidden_gold_author(login)
        independent = actor == "human" and not is_pr_author and not is_study
        source = item.get("source") or ("inline" if item.get("inline") else "issue")
        comment_id = item.get("id")
        rows.append(
            {
                "pr_id": pr_id,
                "comment_id": "" if comment_id is None else str(comment_id),
                "source": str(source),
                "author_login": login,
                "actor_class": actor,
                "is_pr_author": "true" if is_pr_author else "false",
                "is_study_author": "true" if is_study else "false",
                "eligible_as_independent_gold_candidate": "true" if independent else "false",
                "text": item.get("body") or "",
                "path": item.get("path") or "",
                "class": "",
                "atomic_issue_id": f"{pr_id}-{index:03d}",
                "in_reference_set": "false",
            }
        )
    return rows


def partition_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups = {"human": [], "bot": [], "author": [], "study_author": [], "unclassified": []}
    for row in rows:
        if row["is_study_author"] == "true":
            groups["study_author"].append(row)
            groups["author"].append(row)
            continue
        if row["is_pr_author"] == "true":
            groups["author"].append(row)
            continue
        actor = row["actor_class"]
        if actor == "bot":
            groups["bot"].append(row)
        elif actor == "human":
            groups["human"].append(row)
        else:
            groups["unclassified"].append(row)
    return groups


def write_extracted_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXTRACT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
