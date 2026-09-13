"""Actor classification for gold-standard eligibility.

A login is never treated as human gold merely because it looks like a person.
GitHub `user.type == Bot` and known automation logins are bots. Unknown
accounts without a type are unclassified and are not independent gold.
"""

from __future__ import annotations

import re

AUTHOR_LOGIN = "tejasva-vardhan"

# Lowercase logins. GitHub Apps usually appear as name[bot].
KNOWN_BOT_LOGINS = frozenset(
    {
        "coderabbitai",
        "coderabbitai[bot]",
        "dependabot",
        "dependabot[bot]",
        "github-actions",
        "github-actions[bot]",
        "sonarcloud",
        "sonarqubecloud",
        "sonarcloud[bot]",
        "claassistant",
        "cla-assistant[bot]",
        "copilot",
        "copilot-pull-request-reviewer[bot]",
        "copilot-swe-agent[bot]",
        "renovate",
        "renovate[bot]",
        "imgbot",
        "imgbot[bot]",
        "vercel[bot]",
        "netlify[bot]",
        "linear[bot]",
        "cursor[bot]",
        "chatgpt-codex-connector[bot]",
    }
)

_BOT_SUFFIX = re.compile(r"\[bot\]$", re.IGNORECASE)
_PROCESS_ONLY = re.compile(
    r"^(lgtm[!.,\s]*|\+1[.!]?|approved[.!]?|nit[.!]?|thanks[.!]?|"
    r"thank you[.!]?|sgtm[.!]?|looks good( to me)?[.!]?|"
    r"merge conflicts?[.!]?|please rebase[.!]?)$",
    re.IGNORECASE,
)


def normalize_login(login: str | None) -> str:
    return (login or "").strip()


def is_forbidden_gold_author(login: str | None) -> bool:
    """Study author comments are never independent ground truth."""
    return normalize_login(login).lower() == AUTHOR_LOGIN.lower()


def is_known_bot_login(login: str | None) -> bool:
    low = normalize_login(login).lower()
    if not low:
        return False
    return low.endswith("[bot]") or low in KNOWN_BOT_LOGINS or bool(_BOT_SUFFIX.search(low))


def classify_actor(login: str | None, user_type: str | None = None) -> str:
    """Return `bot`, `human`, `study_author`, or `unclassified`."""
    if is_forbidden_gold_author(login):
        return "study_author"
    if (user_type or "").lower() == "bot" or is_known_bot_login(login):
        return "bot"
    if not normalize_login(login):
        return "unclassified"
    if user_type is None or user_type == "":
        if is_known_bot_login(login):
            return "bot"
        return "unclassified"
    if user_type.lower() == "user":
        return "human"
    return "unclassified"


def is_bot_login(login: str | None, user_type: str | None = None) -> bool:
    return classify_actor(login, user_type) == "bot"


_SHORT_CONFLICT_PROCESS = re.compile(
    r"(merge( in| into)? main and fix conflicts|"
    r"needs? merge conflicts resolved( again)?|"
    r"conflicts need to be resolved( again)?|"
    r"merge main and fix conflicts)",
    re.IGNORECASE,
)


def is_process_only_text(text: str | None) -> bool:
    body = (text or "").strip()
    if not body:
        return True
    compact = re.sub(r"\s+", " ", body)
    if _PROCESS_ONLY.match(compact):
        return True
    if compact.lower().startswith("all committers have signed the cla"):
        return True
    if len(compact) <= 80 and _SHORT_CONFLICT_PROCESS.search(compact):
        return True
    return False


def is_meaningful_review_text(text: str | None, *, inline: bool = False) -> bool:
    """Operationalization of protocol §4.5 for verification.

    Inline comments on a file are treated as review content even if short.
    Empty approvals and CLA/LGTM-only bodies are not enough for gold.
    This is not defect/design labeling (Phase 5).
    """
    if inline and (text or "").strip():
        return True
    return not is_process_only_text(text)
