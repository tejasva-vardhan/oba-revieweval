"""Download Maglev PR surfaces into a local cache. Never prints the token."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.collect import collect_pull_request
from oba_revieweval.dataset.github import GitHubAPIError, GitHubClient, load_token

CANDIDATE_CSV = ROOT / "data" / "candidates" / "pr_candidates.csv"
CACHE = ROOT / "data" / "raw" / "cache"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, action="append")
    args = parser.parse_args()
    if args.pr:
        numbers = args.pr
    else:
        with CANDIDATE_CSV.open(encoding="utf-8", newline="") as handle:
            numbers = [int(row["pr_id"]) for row in csv.DictReader(handle)]
    token = load_token()
    client = GitHubClient(token=token, cache_dir=CACHE)
    failed = 0
    for number in numbers:
        try:
            collect_pull_request(client, number)
            print(f"cached #{number}")
        except GitHubAPIError:
            failed += 1
            print(f"failed #{number} (HTTP/parse; no token logged)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
