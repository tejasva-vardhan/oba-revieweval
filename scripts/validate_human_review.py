"""Quality-control checks for the Phase 5 human reference table."""

from __future__ import annotations

from pathlib import Path

from oba_revieweval.annotation.human_review import load_human_review_csv, validate_human_review


def main() -> int:
    path = Path("data/human_review.csv")
    rows = load_human_review_csv(path)
    errors = validate_human_review(rows)
    if errors:
        print("FAIL")
        for error in errors:
            print(error)
        return 1
    print(f"OK rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
