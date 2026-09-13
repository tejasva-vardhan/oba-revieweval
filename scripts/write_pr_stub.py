"""Write a minimal sanitized PR object into the API cache."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.github import cache_path_for


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--merge-sha", required=True)
    parser.add_argument("--merged", action="store_true", default=True)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "raw" / "cache")
    args = parser.parse_args()
    payload = {
        "number": args.number,
        "title": args.title,
        "state": "closed",
        "merged": bool(args.merged),
        "merge_commit_sha": args.merge_sha,
        "html_url": f"https://github.com/OneBusAway/maglev/pull/{args.number}",
        "user": {"login": args.author, "type": "User"},
    }
    url = f"https://api.github.com/repos/OneBusAway/maglev/pulls/{args.number}"
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_path_for(args.cache_dir, url)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    print(f"stub {args.number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
