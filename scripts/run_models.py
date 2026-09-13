"""Call LLM A / LLM B. Stops if credentials are missing."""

from __future__ import annotations

import os
import sys


def main() -> int:
    missing = []
    if not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY (LLM A, GPT-class)")
    if not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get(
        "ANTHROPIC_API_KEY"
    ):
        missing.append(
            "OPENROUTER_API_KEY or another documented open-model endpoint (LLM B)"
        )
    if missing:
        print(
            "Model runs are not executed without credentials:\n  - "
            + "\n  - ".join(missing)
            + "\nDo not invent keys. See .env.example.",
            file=sys.stderr,
        )
        return 2
    print("Credentials present; model client is Phase 8.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
