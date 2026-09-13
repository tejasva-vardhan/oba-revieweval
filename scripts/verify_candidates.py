"""Verify the frozen 30-PR candidate list. Does not rewrite pr_candidates.csv."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.collect import collect_pull_request
from oba_revieweval.dataset.eligibility import evaluate_eligibility
from oba_revieweval.dataset.github import GitHubAPIError, GitHubClient, load_token

CANDIDATE_CSV = ROOT / "data" / "candidates" / "pr_candidates.csv"
OUT_CSV = ROOT / "data" / "candidates" / "pr_verification.csv"

FIELDS = [
    "pr_number",
    "title",
    "author",
    "merge_sha",
    "stratum",
    "changed_files",
    "changed_file_count",
    "change_kind",
    "review_count",
    "human_review_present",
    "independent_human_review_present",
    "author_comments_present",
    "bot_review_present",
    "eligible_for_primary_gold",
    "independent_human_logins",
    "bot_logins",
    "exclusion_reason",
    "notes",
]


def read_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_CSV)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "cache",
    )
    parser.add_argument("--cache-only", action="store_true")
    args = parser.parse_args()
    token = load_token()
    if not token and not args.cache_only:
        print(
            "GITHUB_TOKEN is not set. Export a public-repo read token "
            "and rerun, or pass --cache-only after a cache fill. "
            "The token is not logged.",
            file=sys.stderr,
        )
        return 2
    if args.cache_only:
        token = None
    client = GitHubClient(
        token=token,
        cache_dir=args.cache_dir,
        cache_only=args.cache_only,
    )
    rows = []
    for candidate in read_candidates(CANDIDATE_CSV):
        number = int(candidate["pr_id"])
        try:
            collected = collect_pull_request(client, number)
            decision = evaluate_eligibility(collected, stratum=candidate.get("stratum", ""))
        except GitHubAPIError as exc:
            decision = {
                "pr_number": number,
                "title": candidate.get("title"),
                "author": candidate.get("author"),
                "merge_sha": "",
                "stratum": candidate.get("stratum", ""),
                "changed_files": "",
                "changed_file_count": "",
                "change_kind": "",
                "review_count": "",
                "human_review_present": False,
                "independent_human_review_present": False,
                "author_comments_present": False,
                "bot_review_present": False,
                "eligible_for_primary_gold": False,
                "independent_human_logins": "",
                "bot_logins": "",
                "exclusion_reason": "api_error",
                "notes": "GitHubAPIError (message omitted if it could leak auth)",
            }
            _ = exc
        rows.append(decision)
        print(
            f"#{number} eligible={decision['eligible_for_primary_gold']} "
            f"reason={decision.get('exclusion_reason') or 'ok'}"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    stamp = dt.date.today().isoformat()
    print(f"Wrote {args.out} ({len(rows)} rows) on {stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
