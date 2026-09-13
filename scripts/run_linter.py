"""Run pinned golangci-lint on merge-SHA trees for the recommended corpus.

Usage:
    python scripts/install_golangci_lint.py
    python scripts/run_linter.py --pr 702
    python scripts/run_linter.py
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
from oba_revieweval.lint.aggregate import write_lint_csv  # noqa: E402
from oba_revieweval.lint.constants import FINDING_FIELDS, MANIFEST_FIELDS  # noqa: E402
from oba_revieweval.lint.runner import analyze_pr, default_maglev  # noqa: E402

RECOMMENDED = ROOT / "data" / "candidates" / "recommended_corpus.csv"
RAW_PRS = ROOT / "data" / "raw" / "prs"
LINT_ROOT = ROOT / "data" / "raw" / "lint"
FINDINGS_CSV = ROOT / "data" / "lint_findings.csv"
MANIFEST_CSV = ROOT / "data" / "lint_manifest.csv"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, action="append", dest="prs")
    parser.add_argument("--recommended", type=Path, default=RECOMMENDED)
    parser.add_argument("--repo", type=Path, default=default_maglev())
    parser.add_argument("--dest-root", type=Path, default=LINT_ROOT)
    parser.add_argument("--findings", type=Path, default=FINDINGS_CSV)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_CSV)
    args = parser.parse_args()
    if not (args.repo / ".git").exists() and not (args.repo / ".git").is_file():
        # A normal clone has a .git directory; a worktree has a .git file.
        if not (args.repo / "go.mod").exists():
            print(f"Maglev checkout missing at {args.repo}", file=sys.stderr)
            return 2
    recommended = load_recommended(args.recommended)
    if args.prs:
        selected = {int(number) for number in args.prs}
        recommended = [row for row in recommended if int(row["pr_number"]) in selected]
        missing = selected - {int(row["pr_number"]) for row in recommended}
        if missing:
            print(f"PRs not in recommended corpus: {sorted(missing)}", file=sys.stderr)
            return 2
    findings: list[dict[str, str]] = []
    manifest: list[dict[str, str]] = []
    failed = 0
    for row in recommended:
        pr_number = int(row["pr_number"])
        print(f"linting #{pr_number} at {row['merge_sha']}", flush=True)
        result = analyze_pr(
            pr_number=pr_number,
            merge_sha=row["merge_sha"],
            repo=args.repo,
            dest_dir=args.dest_root / str(pr_number),
            raw_pr_dir=RAW_PRS / str(pr_number),
        )
        run = result["run"]
        print(
            f"  status={run['execution_status']} exit={run['exit_code']} "
            f"findings={run['finding_count']} dropped={run['dropped_outside_diff']} "
            f"tree={run['commit_sha'][:12]}",
            flush=True,
        )
        if run["execution_status"] not in {"ok", "no_go_targets"}:
            failed += 1
            if run.get("stderr"):
                print(run["stderr"][-2000:], file=sys.stderr)
            if run.get("parse_error"):
                print(run["parse_error"], file=sys.stderr)
        findings.extend(result["findings"])
        manifest.append(result["manifest"])
    if not args.prs or len(manifest) == 33:
        write_lint_csv(args.findings, findings, FINDING_FIELDS)
        write_lint_csv(args.manifest, manifest, MANIFEST_FIELDS)
        print(f"wrote {args.findings} ({len(findings)} findings)")
        print(f"wrote {args.manifest} ({len(manifest)} PRs)")
    else:
        print("single-PR run: aggregate CSVs not overwritten")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
