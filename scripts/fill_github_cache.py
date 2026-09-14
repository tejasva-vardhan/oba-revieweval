"""Fill the gitignored GitHub JSON cache for recommended PRs.

Does not log tokens. Public unauthenticated REST is used when no token exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import load_recommended
from oba_revieweval.dataset.github import GitHubAPIError, GitHubClient, load_token

CACHE = ROOT / "data" / "raw" / "cache"
RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"


def _paths(number: int) -> list[tuple[str, str]]:
    base = f"/repos/OneBusAway/maglev/pulls/{number}"
    return [
        ("pr", base),
        ("files", f"{base}/files"),
        ("reviews", f"{base}/reviews"),
        ("inline", f"{base}/comments"),
        ("issues", f"/repos/OneBusAway/maglev/issues/{number}/comments"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    parser.add_argument("--recommended", type=Path, default=RECOMMENDED)
    parser.add_argument(
        "--kinds",
        default="pr,files,reviews,inline,issues",
        help="Comma-separated: pr,files,reviews,inline,issues",
    )
    args = parser.parse_args()
    wanted = {part.strip() for part in args.kinds.split(",") if part.strip()}
    token = load_token()
    client = GitHubClient(token=token, cache_dir=args.cache_dir, cache_only=False)
    rows = load_recommended(args.recommended)
    failed: list[str] = []
    for row in rows:
        number = int(row["pr_number"])
        for kind, path in _paths(number):
            if kind not in wanted:
                continue
            try:
                if kind == "pr":
                    client.request_json(path)
                else:
                    client.paginate(path)
                print(f"ok {number} {kind}")
            except GitHubAPIError as exc:
                failed.append(f"{number}:{kind}:{exc}")
                print(f"fail {number} {kind}: {exc}")
    if failed:
        print("FAILED", len(failed))
        for item in failed:
            print(item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
