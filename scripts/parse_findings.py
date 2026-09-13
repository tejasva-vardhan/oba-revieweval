"""Parse structured model/linter JSON into finding rows (Phase 8)."""

from __future__ import annotations

import sys


def main() -> int:
    print("No model or linter JSON exists in the scaffold.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
