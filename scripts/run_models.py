"""Call LLM A on merge-SHA-anchored PR context.

Phase 6B: --pilot runs only the three documented PRs.
This script does not iterate the remaining corpus.

Usage:
    python scripts/run_models.py --pilot
    python scripts/run_models.py --pr 1404 --pr 702 --pr 1428
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import load_recommended  # noqa: E402
from oba_revieweval.models.constants import PILOT_PRS, repo_root  # noqa: E402
from oba_revieweval.models.runner import run_pilot  # noqa: E402
from oba_revieweval.models.secrets import MissingAPIKey  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true", help="run the three Phase 6B PRs only")
    parser.add_argument("--pr", type=int, action="append", dest="prs")
    parser.add_argument(
        "--approve-full-corpus",
        action="store_true",
        help="required to send every recommended PR after the 3-PR pilot is approved",
    )
    args = parser.parse_args()
    if args.prs:
        selected = tuple(args.prs)
    elif args.pilot:
        selected = PILOT_PRS
    else:
        print(
            "Refusing to run the full corpus. Use --pilot for the three "
            f"documented PRs {list(PILOT_PRS)}, or pass explicit --pr values.",
            file=sys.stderr,
        )
        return 2
    extra = [number for number in selected if number not in PILOT_PRS]
    if extra and args.pilot:
        print(f"--pilot does not accept extra PRs: {extra}", file=sys.stderr)
        return 2
    recommended = {
        int(row["pr_number"])
        for row in load_recommended(repo_root() / "data" / "candidates" / "recommended_corpus.csv")
    }
    if set(selected) == recommended and not args.approve_full_corpus:
        print(
            "Refusing to run the full corpus before the 3-PR pilot is "
            "explicitly approved. Use --pilot now, or pass "
            "--approve-full-corpus after that approval.",
            file=sys.stderr,
        )
        return 2
    try:
        result = run_pilot(prs=selected)
    except MissingAPIKey as exc:
        print(str(exc), file=sys.stderr)
        print("Set OPENAI_API_KEY in the environment or .env. Do not invent a key.", file=sys.stderr)
        return 2
    failed = [
        row
        for row in result["manifest"]
        if row["execution_status"] not in {"ok"}
    ]
    print(f"wrote data/llm_a_pilot_findings.csv ({len(result['findings'])} findings)")
    print(f"wrote data/llm_a_pilot_manifest.csv ({len(result['manifest'])} PRs)")
    print("LLM B not run")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
