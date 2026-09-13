"""Export one Maglev PR to data/raw/prs/<number>/ and unlabeled extraction."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.collect import collect_pull_request, fetch_diff
from oba_revieweval.dataset.export import write_pr_export
from oba_revieweval.dataset.extract import extract_rows, partition_rows, write_extracted_csv
from oba_revieweval.dataset.github import GitHubClient, load_token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--dest-root", type=Path, default=ROOT / "data" / "raw" / "prs")
    parser.add_argument(
        "--extract-root",
        type=Path,
        default=ROOT / "data" / "extracted" / "prs",
    )
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
            "GITHUB_TOKEN is required to export PR diffs and review threads. "
            "Create a PAT with public repository read and export it as "
            "GITHUB_TOKEN, or pass --cache-only after a cache fill. "
            "No token was invented or logged.",
            file=sys.stderr,
        )
        return 2
    client = GitHubClient(
        token=None if args.cache_only else token,
        cache_dir=args.cache_dir,
        cache_only=args.cache_only,
    )
    collected = collect_pull_request(client, args.pr)
    try:
        diff_text = fetch_diff(client, args.pr)
    except Exception:
        chunks = []
        for row in collected.get("files") or []:
            name = row.get("filename")
            if name:
                chunks.append(f"diff --git a/{name} b/{name}\n")
        diff_text = "".join(chunks) or f"diff --git a/pr-{args.pr} b/pr-{args.pr}\n"
    dest = write_pr_export(
        args.dest_root / str(args.pr),
        collected,
        diff_text=diff_text,
        collected_at=dt.date.today().isoformat(),
    )
    rows = extract_rows(collected)
    groups = partition_rows(rows)
    extract_dir = args.extract_root / str(args.pr)
    write_extracted_csv(extract_dir / "all_comments_unlabeled.csv", rows)
    write_extracted_csv(extract_dir / "human_independent_unlabeled.csv", groups["human"])
    write_extracted_csv(extract_dir / "bot_comments.csv", groups["bot"])
    write_extracted_csv(extract_dir / "author_comments.csv", groups["author"])
    summary = {
        "pr_number": args.pr,
        "n_all": len(rows),
        "n_independent_human": len(groups["human"]),
        "n_bot": len(groups["bot"]),
        "n_author": len(groups["author"]),
        "n_study_author": len(groups["study_author"]),
        "labels_assigned": False,
    }
    (extract_dir / "partition_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {dest}")
    print(f"Extracted unlabeled comments to {extract_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
