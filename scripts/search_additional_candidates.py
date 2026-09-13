"""Search Maglev for extra PRs. Do not accept a hit on title keywords alone."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.github import GitHubClient, load_token
from oba_revieweval.dataset.search import SEARCH_QUERIES, consider_additional, search_issue_numbers

CANDIDATE_CSV = ROOT / "data" / "candidates" / "pr_candidates.csv"
OUT_CSV = ROOT / "data" / "candidates" / "additional_considered.csv"

FIELDS = [
    "pr_number",
    "title",
    "author",
    "merge_sha",
    "stratum",
    "search_query",
    "decision",
    "eligible_for_primary_gold",
    "independent_human_review_present",
    "bot_review_present",
    "independent_human_logins",
    "exclusion_reason",
    "notes",
]


def existing_ids() -> set[int]:
    with CANDIDATE_CSV.open(encoding="utf-8", newline="") as handle:
        return {int(row["pr_id"]) for row in csv.DictReader(handle)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT_CSV)
    args = parser.parse_args()
    token = load_token()
    if not token:
        print("GITHUB_TOKEN is not set. The token is not logged.", file=sys.stderr)
        return 2
    client = GitHubClient(token=token)
    exclude = existing_ids()
    rows: list[dict] = []
    seen: set[int] = set()
    for query in SEARCH_QUERIES:
        numbers = search_issue_numbers(client, query)
        batch = consider_additional(client, numbers, exclude=exclude, query=query)
        for row in batch:
            number = int(row["pr_number"])
            if number in seen:
                continue
            seen.add(number)
            rows.append(row)
            print(
                f"#{number} decision={row['decision']} "
                f"eligible={row['eligible_for_primary_gold']}"
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.out} ({len(rows)} considered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
