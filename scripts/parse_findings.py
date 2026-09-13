"""Re-parse stored golangci-lint JSON into atomic finding rows.

Does not re-run the linter. Does not score against human gold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import load_recommended  # noqa: E402
from oba_revieweval.dataset.git_anchor import list_changed_files, resolve_merge_commit  # noqa: E402
from oba_revieweval.lint.aggregate import write_lint_csv  # noqa: E402
from oba_revieweval.lint.constants import FINDING_FIELDS  # noqa: E402
from oba_revieweval.lint.parse import assign_stable_ids, findings_from_issues, parse_linter_output  # noqa: E402
from oba_revieweval.lint.runner import default_maglev  # noqa: E402
from oba_revieweval.lint.scope import changed_file_set, partition_issues  # noqa: E402


def main() -> int:
    lint_root = ROOT / "data" / "raw" / "lint"
    recommended = load_recommended(ROOT / "data" / "candidates" / "recommended_corpus.csv")
    repo = default_maglev()
    rows: list[dict[str, str]] = []
    missing: list[int] = []
    for item in recommended:
        pr_number = int(item["pr_number"])
        raw_json = lint_root / str(pr_number) / "raw.json"
        run_path = lint_root / str(pr_number) / "run.json"
        if not raw_json.exists() or not run_path.exists():
            missing.append(pr_number)
            continue
        run = json.loads(run_path.read_text(encoding="utf-8"))
        issues = parse_linter_output(json_text=raw_json.read_text(encoding="utf-8"))
        merge = resolve_merge_commit(repo, item["merge_sha"])
        changed = changed_file_set(list_changed_files(repo, merge))
        kept, _dropped = partition_issues(issues, changed)
        rows.extend(
            assign_stable_ids(
                findings_from_issues(
                    kept,
                    pr_number=pr_number,
                    commit_sha=run["commit_sha"],
                    tool_version=run["tool_version"],
                )
            )
        )
    if missing:
        print(f"missing raw lint output for PRs: {missing}", file=sys.stderr)
        return 2
    dest = ROOT / "data" / "lint_findings.csv"
    write_lint_csv(dest, rows, FINDING_FIELDS)
    print(f"wrote {dest} ({len(rows)} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
