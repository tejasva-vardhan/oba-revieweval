"""Search Maglev history for additional review-bearing PRs.

Title keywords are only a retrieval filter. Acceptance still requires
independent human review on the actual thread.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from oba_revieweval.dataset.collect import collect_pull_request
from oba_revieweval.dataset.eligibility import evaluate_eligibility
from oba_revieweval.dataset.github import GitHubClient, require_mapping

SEARCH_QUERIES = (
    'repo:OneBusAway/maglev is:pr is:merged race',
    'repo:OneBusAway/maglev is:pr is:merged mutex OR RLock OR "data race"',
    'repo:OneBusAway/maglev is:pr is:merged deadlock OR goroutine OR concurrent',
    'repo:OneBusAway/maglev is:pr is:merged transaction OR sqlc',
)


def search_issue_numbers(client: GitHubClient, query: str, *, max_items: int = 30) -> list[int]:
    path = f"/search/issues?q={quote(query)}&per_page=30"
    payload = require_mapping(client.request_json(path), context="search")
    items = payload.get("items") or []
    numbers: list[int] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if isinstance(number, int):
            numbers.append(number)
        if len(numbers) >= max_items:
            break
    return numbers


def consider_additional(
    client: GitHubClient,
    numbers: list[int],
    *,
    exclude: set[int],
    query: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for number in numbers:
        if number in exclude or number in seen:
            continue
        seen.add(number)
        collected = collect_pull_request(client, number)
        decision = evaluate_eligibility(collected, stratum="unassigned")
        decision["search_query"] = query
        if decision["eligible_for_primary_gold"]:
            decision["decision"] = "accepted_additional"
        else:
            decision["decision"] = "rejected"
        if number in exclude:
            decision["decision"] = "already_in_candidate_list"
        rows.append(decision)
    return rows
