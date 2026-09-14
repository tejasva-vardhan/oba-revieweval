"""Fail if any recommended PR export is incomplete."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import (
    corpus_is_complete,
    load_recommended,
    validate_recommended_corpus,
)


def main() -> int:
    recommended = load_recommended(ROOT / "data" / "candidates" / "recommended_corpus.csv")
    results = validate_recommended_corpus(
        recommended,
        ROOT / "data" / "raw" / "prs",
        ROOT / "data" / "extracted" / "prs",
    )
    failed = [row for row in results if not row["complete"]]
    print(f"validated={len(results)} complete={len(results) - len(failed)}")
    if failed:
        for row in failed:
            print(f"#{row['pr_number']}: {row['errors']}")
        return 1
    if not corpus_is_complete(results):
        print("corpus incomplete")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
