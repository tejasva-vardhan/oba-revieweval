"""Copy WebFetch/API dumps into the GitHub JSON cache. No tokens involved."""

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


def extract_json(text: str) -> object:
    start_obj = text.find("\n{")
    start_arr = text.find("\n[")
    candidates = [i for i in (start_obj, start_arr) if i != -1]
    if not candidates:
        if text.lstrip().startswith(("{", "[")):
            return json.loads(text)
        raise ValueError("no JSON payload")
    start = min(candidates) + 1
    return json.loads(text[start:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "raw" / "cache")
    args = parser.parse_args()
    payload = extract_json(args.source.read_text(encoding="utf-8"))
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_path_for(args.cache_dir, args.url)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    print(f"cached {args.url} -> {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
