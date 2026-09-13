"""Gold-eligibility checks. Does not change the frozen protocol.

Protocol §4–§5 decide inclusion. This module only applies those rules to
collected GitHub surfaces. Phase 5 still has to type comments as
defect/design before a row enters the scored reference set.
"""

from __future__ import annotations

from typing import Any, Iterable

from oba_revieweval.dataset.actors import (
    AUTHOR_LOGIN,
    classify_actor,
    is_forbidden_gold_author,
    is_meaningful_review_text,
)


def _iter_review_surfaces(collected: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in ("issue_comments", "inline_comments", "review_bodies"):
        for row in collected.get(key) or []:
            yield row


def summarize_actors(collected: dict[str, Any]) -> dict[str, Any]:
    humans: set[str] = set()
    independent_humans: set[str] = set()
    bots: set[str] = set()
    unclassified: set[str] = set()
    author_comments = 0
    independent_meaningful = 0
    independent_any = 0
    bot_review = False

    pr_author = (collected.get("author") or "").lower()

    for row in _iter_review_surfaces(collected):
        login = row.get("login")
        kind = classify_actor(login, row.get("user_type"))
        login_l = (login or "").lower()
        if kind == "bot":
            bots.add(login or "")
            bot_review = True
            continue
        if kind == "unclassified":
            if login:
                unclassified.add(login)
            continue
        if kind == "study_author" or (login_l and login_l == pr_author):
            author_comments += 1
            if kind == "human":
                humans.add(login or "")
            continue
        humans.add(login or "")
        independent_humans.add(login or "")
        independent_any += 1
        if is_meaningful_review_text(row.get("body"), inline=bool(row.get("inline"))):
            independent_meaningful += 1

    return {
        "human_logins": sorted(humans),
        "independent_human_logins": sorted(independent_humans),
        "bot_logins": sorted(x for x in bots if x),
        "unclassified_logins": sorted(unclassified),
        "author_comment_count": author_comments,
        "independent_any_count": independent_any,
        "independent_meaningful_count": independent_meaningful,
        "bot_review_present": bot_review,
    }


def evaluate_eligibility(collected: dict[str, Any], *, stratum: str = "") -> dict[str, Any]:
    actors = summarize_actors(collected)
    author = collected.get("author")
    author_is_study = is_forbidden_gold_author(author)
    change_kind = collected.get("change_kind") or "unknown"
    merged = bool(collected.get("merged"))
    repo = collected.get("repo") or ""

    human_review_present = bool(actors["human_logins"] or actors["author_comment_count"])
    independent_human_review_present = actors["independent_meaningful_count"] > 0
    author_comments_present = actors["author_comment_count"] > 0
    bot_review_present = actors["bot_review_present"]

    reasons: list[str] = []
    if repo != "OneBusAway/maglev":
        reasons.append("not_maglev")
    if not merged:
        reasons.append("not_merged")
    if classify_actor(author, collected.get("author_type")) == "bot":
        reasons.append("bot_authored")
    if change_kind in {"docs_or_openapi", "dependency_only", "empty", "no_go_or_sql"}:
        reasons.append(f"change_kind:{change_kind}")
    if not independent_human_review_present:
        if bot_review_present and actors["independent_any_count"] == 0:
            reasons.append("bot_only_or_author_only")
        elif actors["independent_any_count"] == 0:
            reasons.append("no_independent_human")
        else:
            reasons.append("independent_human_not_meaningful")
    if actors["unclassified_logins"] and not independent_human_review_present:
        reasons.append("unclassified_actors_not_used_as_gold")

    eligible = (
        repo == "OneBusAway/maglev"
        and merged
        and change_kind == "code"
        and independent_human_review_present
        and classify_actor(author, collected.get("author_type")) != "bot"
    )

    exclusion_reason = "" if eligible else ";".join(reasons) or "ineligible"
    notes_parts = []
    if author_is_study:
        notes_parts.append(
            f"PR author is {AUTHOR_LOGIN}; author comments are never gold"
        )
    if actors["bot_logins"]:
        notes_parts.append("bots=" + ",".join(actors["bot_logins"]))
    if actors["human_logins"]:
        notes_parts.append("humans=" + ",".join(actors["human_logins"]))
    if stratum:
        notes_parts.append(f"candidate_stratum={stratum}")

    return {
        "pr_number": collected.get("pr_number"),
        "title": collected.get("title"),
        "author": author,
        "merge_sha": collected.get("merge_sha"),
        "stratum": stratum,
        "changed_files": ";".join(collected.get("changed_files") or []),
        "changed_file_count": collected.get("changed_file_count"),
        "change_kind": change_kind,
        "review_count": collected.get("review_count"),
        "human_review_present": human_review_present,
        "independent_human_review_present": independent_human_review_present,
        "author_comments_present": author_comments_present,
        "bot_review_present": bot_review_present,
        "eligible_for_primary_gold": eligible,
        "exclusion_reason": exclusion_reason,
        "independent_human_logins": ";".join(actors["independent_human_logins"]),
        "bot_logins": ";".join(actors["bot_logins"]),
        "notes": "; ".join(notes_parts),
    }
