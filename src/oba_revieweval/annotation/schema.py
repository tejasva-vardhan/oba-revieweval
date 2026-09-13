"""Closed label sets. Keep in sync with protocol.md and docs/annotation_schema.md."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HUMAN_LABELS = ("defect", "design", "style", "question", "process_other")
FINDING_LABELS = ("tp_useful", "incorrect", "harmful", "extra_valid")
REFERENCE_HUMAN_LABELS = frozenset({"defect", "design"})
SELF_LOGIN = "tejasva-vardhan"

HumanClass = Literal["defect", "design", "style", "question", "process_other"]
FindingLabel = Literal["tp_useful", "incorrect", "harmful", "extra_valid"]
ToolName = Literal["golangci-lint", "llm_a", "llm_b"]
Stratum = Literal["concurrency", "api_gtfs", "database", "test_refactor", "other"]


def in_reference_set(
    human_label: str,
    author_login: str,
    *,
    is_pr_author: bool = False,
    about_the_change: bool = True,
) -> bool:
    """Protocol §7 / annotation schema: defect+design, never author, never study author.

    `about_the_change=False` is a documented Phase 5 clarification: observations
    the reviewer marks as pre-existing, follow-up, or out of this PR's diff
    are not primary gold for scoring this change.
    """
    if is_pr_author:
        return False
    if author_login.lower() == SELF_LOGIN.lower():
        return False
    if not about_the_change:
        return False
    return human_label in REFERENCE_HUMAN_LABELS


class HumanComment(BaseModel):
    pr_id: int
    comment_id: int
    source: Literal["issue", "inline", "review_body"]
    author_login: str
    is_pr_author: bool
    text: str
    path: str | None = None
    class_: HumanClass = Field(alias="class")
    atomic_issue_id: str
    in_reference_set: bool

    model_config = {"populate_by_name": True}


class Finding(BaseModel):
    finding_id: str
    pr_id: int
    tool: ToolName
    category: Stratum
    text: str
    location: str | None = None
    label: FindingLabel
    human_issue_id: str | None = None
    rationale: str
