"""Run golangci-lint on a checked-out Maglev merge SHA (Phase 6)."""

from __future__ import annotations

import sys


def main() -> int:
    print("Phase 6: check out Maglev at the merge SHA, then run golangci-lint.")
    print("No Maglev clone or lint results are produced in the scaffold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
