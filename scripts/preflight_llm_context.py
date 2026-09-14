"""Estimate model context size locally. Does not call OpenAI or any other API.

Usage:
    python scripts/preflight_llm_context.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oba_revieweval.dataset.corpus import load_recommended  # noqa: E402
from oba_revieweval.models.constants import PILOT_PRS, load_llm_a_config  # noqa: E402
from oba_revieweval.models.preflight import (  # noqa: E402
    CHARS_PER_TOKEN,
    measure_corpus,
    provisional_cost_usd,
)

FIELDS = (
    "pr_number",
    "pilot",
    "diff_bytes",
    "changed_go_files",
    "post_merge_context_lines",
    "approx_input_tokens",
    "max_output_tokens",
    "estimated_max_token_usage",
)


def main() -> int:
    recommended = load_recommended(ROOT / "data" / "candidates" / "recommended_corpus.csv")
    rows = measure_corpus(recommended, ROOT / "data" / "raw" / "prs")
    leaked = [
        (row["pr_number"], kind, hits)
        for row in rows
        for kind, hits in row["leaks"].items()
        if hits
    ]
    if leaked:
        print("Refusing to report sizes: model-facing text leaked forbidden content.", file=sys.stderr)
        for number, kind, hits in leaked:
            print(f"#{number} {kind}: {len(hits)} snippet(s)", file=sys.stderr)
        return 2
    dest = ROOT / "data" / "llm_context_preflight.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "pr_number": row["pr_number"],
                    "pilot": "true" if row["pilot"] else "false",
                    "diff_bytes": row["diff_bytes"],
                    "changed_go_files": row["changed_go_files"],
                    "post_merge_context_lines": row["post_merge_context_lines"],
                    "approx_input_tokens": row["approx_input_tokens"],
                    "max_output_tokens": row["max_output_tokens"],
                    "estimated_max_token_usage": row["estimated_max_token_usage"],
                }
            )
    config = load_llm_a_config()
    pilot = [row for row in rows if row["pr_number"] in PILOT_PRS]
    all_input = sum(row["approx_input_tokens"] for row in rows)
    pilot_input = sum(row["approx_input_tokens"] for row in pilot)
    max_out = int(config["max_tokens"])
    print(f"token heuristic: {CHARS_PER_TOKEN} chars/token + framing; not an API measurement")
    print(f"wrote {dest}")
    print(f"pilot_input_tokens={pilot_input}")
    print(f"corpus_input_tokens={all_input}")
    print(f"worst_case_output_tokens_33={max_out * 33}")
    print(
        "provisional_usd_3="
        f"{provisional_cost_usd(pilot_input, max_out * 3, config):.4f}"
    )
    print(
        "provisional_usd_33="
        f"{provisional_cost_usd(all_input, max_out * 33, config):.4f}"
    )
    print(
        "provisional_usd_2x33="
        f"{provisional_cost_usd(all_input * 2, max_out * 66, config):.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
