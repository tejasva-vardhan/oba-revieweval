"""Dataset helpers. Loaders for exported diffs arrive in Phase 4."""

from __future__ import annotations

AUTHOR_LOGIN = "tejasva-vardhan"
BOT_LOGINS = frozenset(
    {
        "coderabbitai",
        "coderabbitai[bot]",
        "dependabot",
        "dependabot[bot]",
        "github-actions",
        "github-actions[bot]",
        "sonarcloud",
        "sonarqubecloud",
        "claassistant",
    }
)


def is_bot_login(login: str) -> bool:
    low = login.lower()
    return low.endswith("[bot]") or low in BOT_LOGINS


def is_forbidden_gold_author(login: str) -> bool:
    """Study author comments are never independent ground truth."""
    return login.lower() == AUTHOR_LOGIN.lower()
