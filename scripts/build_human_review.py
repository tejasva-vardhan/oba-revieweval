"""Write data/human_review.csv from Phase 5 atoms plus extract text.

Does not call models, linters, or scoring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oba_revieweval.annotation.human_review import (
    annotation_summary,
    build_human_review_rows,
    validate_human_review,
    write_human_review_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/human_review.csv"),
        help="Annotation table path",
    )
    args = parser.parse_args()
    rows = build_human_review_rows()
    errors = validate_human_review(rows)
    if errors:
        raise SystemExit("validation failed:\n" + "\n".join(errors))
    write_human_review_csv(args.output, rows)
    summary = annotation_summary(rows)
    print(json.dumps(summary, indent=2))
    print(f"wrote {args.output} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
