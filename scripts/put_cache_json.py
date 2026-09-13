"""Write a JSON payload to the collector cache key, including the paginated form."""

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
    parser.add_argument("--url", required=True)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--empty-array", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "raw" / "cache")
    args = parser.parse_args()
    if args.empty_array:
        payload: object = []
    elif args.file:
        text = args.file.read_text(encoding="utf-8")
        start_obj = text.find("\n{")
        start_arr = text.find("\n[")
        starts = [i for i in (start_obj, start_arr) if i != -1]
        if starts:
            payload = json.loads(text[min(starts) + 1 :])
        else:
            payload = json.loads(text)
    else:
        payload = json.loads(sys.stdin.read())
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    urls = [args.url]
    if "?" not in args.url and (
        "/comments" in args.url or "/reviews" in args.url or "/files" in args.url
    ):
        urls.append(args.url + "?per_page=100&page=1")
    for url in urls:
        dest = cache_path_for(args.cache_dir, url)
        dest.write_text(json.dumps(payload), encoding="utf-8")
        print(dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
