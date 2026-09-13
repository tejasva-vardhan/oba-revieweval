"""Compute precision/recall tables from labeled findings (Phase 10)."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "Scoring is not run until data/human_review.csv and data/findings.csv have labels.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
