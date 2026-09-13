"""Export Maglev PR metadata. Requires a GitHub token for pagination.

Usage (after you set GITHUB_TOKEN):
    python scripts/export_prs.py --pr 507

Do not run this in CI with secrets committed.
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "GITHUB_TOKEN is required to export PR diffs and review threads "
            f"for #{args.pr}. Create a classic PAT with public repo read "
            "and export it in the environment. No token was invented.",
            file=sys.stderr,
        )
        return 2
    print("Token present; export implementation is Phase 4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
