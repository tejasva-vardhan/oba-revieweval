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


def in_reference_set(human_label: str, author_login: str) -> bool:
    if author_login.lower() == SELF_LOGIN.lower():
        return False
    return human_label in REFERENCE_HUMAN_LABELS


class HumanComment(BaseModel):
    pr_id: int
    comment_id: int
    source: Literal["issue", "inline"]
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
