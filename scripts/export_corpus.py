"""Export every recommended PR with a merge-SHA-anchored diff.

Usage:
    python scripts/export_corpus.py
    python scripts/export_corpus.py --cache-only
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import (
    corpus_is_complete,
    export_recommended_pr,
    load_recommended,
    validate_recommended_corpus,
    write_manifest,
)
from oba_revieweval.dataset.github import GitHubClient, load_token

RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"
DEST = ROOT / "data" / "raw" / "prs"
EXTRACT = ROOT / "data" / "extracted" / "prs"
MANIFEST = ROOT / "data" / "raw" / "manifest.csv"
MAGLEV = ROOT / "data" / "raw" / "cache" / "maglev"
CACHE = ROOT / "data" / "raw" / "cache"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recommended", type=Path, default=RECOMMENDED)
    parser.add_argument("--repo", type=Path, default=MAGLEV)
    parser.add_argument("--dest-root", type=Path, default=DEST)
    parser.add_argument("--extract-root", type=Path, default=EXTRACT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    parser.add_argument("--cache-only", action="store_true")
    args = parser.parse_args()
    if not (args.repo / ".git").exists():
        print(f"Maglev checkout missing at {args.repo}", file=sys.stderr)
        return 2
    token = load_token()
    client = GitHubClient(
        token=None if args.cache_only else token,
        cache_dir=args.cache_dir,
        cache_only=args.cache_only or not token,
    )
    recommended = load_recommended(args.recommended)
    rows = []
    for item in recommended:
        row = export_recommended_pr(
            item,
            repo=args.repo,
            client=client,
            dest_root=args.dest_root,
            extract_root=args.extract_root,
            collected_at=dt.date.today().isoformat(),
        )
        rows.append(row)
        print(
            f"#{row['pr_number']} complete={row['export_complete']} "
            f"files={row['changed_file_count']} {row['export_error'] or 'ok'}"
        )
    write_manifest(args.manifest, rows)
    checked = validate_recommended_corpus(recommended, args.dest_root, args.extract_root)
    complete = corpus_is_complete(checked)
    failed = [row for row in checked if not row["complete"]]
    print(f"Wrote {args.manifest}")
    print(f"complete={sum(1 for r in rows if r['export_complete'])}/33")
    if failed:
        for row in failed:
            print(f"INVALID #{row['pr_number']}: {row['errors']}")
        return 1
    if not complete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
