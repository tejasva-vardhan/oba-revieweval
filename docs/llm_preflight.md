# LLM context preflight (no API)

Date: 2026-09-14.

This is a **local** size and leak check of the messages the current pipeline would send. It does **not** call OpenAI, does **not** run `scripts/run_models.py`, and does **not** amend `protocol.md`, `research_questions.md`, `prompts/llm_review_v1.md`, or `data/human_review.csv`.

Token counts are a **provisional character heuristic**, not tokenizer output and not API `usage`. Formula: `ceil((system_chars + user_chars + 80) / 4)`. Configured max output is `4096` from `configs/llm_a.json`. Estimated maximum token usage is approximate input plus that cap.

Dollar figures below use **only** the rates recorded in `configs/llm_a.json` (`$2.50` / `$10.00` per million input / output tokens). They are **provisional estimates**, not actual API cost. LLM B has no recorded price; the two-model row **doubles the LLM A rates as a stand-in**.

Reproduce:

```bash
python scripts/preflight_llm_context.py
```

## Per-PR sizes

Pilot PRs (`#1404`, `#702`, `#1428`) are marked. Diff size is UTF-8 bytes of the merge-parent `diff.patch`. Context lines are post-merge Go excerpt lines actually included (cap 200 per file).

| PR | Pilot | Diff bytes | Changed Go files | Post-merge context lines | Approx. input tokens | Max output tokens | Est. max token usage |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 271 | | 491 | 1 | 49 | 681 | 4096 | 4777 |
| 354 | | 659 | 1 | 51 | 808 | 4096 | 4904 |
| 372 | | 14928 | 5 | 719 | 9304 | 4096 | 13400 |
| 457 | | 533 | 1 | 38 | 683 | 4096 | 4779 |
| 507 | | 8665 | 3 | 291 | 4736 | 4096 | 8832 |
| 541 | | 3494 | 2 | 277 | 3331 | 4096 | 7427 |
| 691 | | 11583 | 4 | 606 | 7679 | 4096 | 11775 |
| **702** | yes | 18341 | 4 | 509 | 8960 | 4096 | 13056 |
| 756 | | 6424 | 4 | 457 | 5688 | 4096 | 9784 |
| 1277 | | 34912 | 7 | 953 | 17476 | 4096 | 21572 |
| 1281 | | 4649 | 2 | 271 | 3688 | 4096 | 7784 |
| 1286 | | 32789 | 3 | 600 | 13872 | 4096 | 17968 |
| 1288 | | 13559 | 2 | 400 | 7515 | 4096 | 11611 |
| 1296 | | 10157 | 7 | 768 | 9139 | 4096 | 13235 |
| 1298 | | 9661 | 2 | 256 | 6232 | 4096 | 10328 |
| 1300 | | 4724 | 1 | 200 | 4547 | 4096 | 8643 |
| 1313 | | 67181 | 11 | 1925 | 33800 | 4096 | 37896 |
| 1315 | | 3130 | 3 | 150 | 2251 | 4096 | 6347 |
| 1316 | | 25013 | 5 | 798 | 13748 | 4096 | 17844 |
| 1317 | | 83028 | 12 | 1595 | 35876 | 4096 | 39972 |
| 1329 | | 14816 | 2 | 400 | 7460 | 4096 | 11556 |
| 1347 | | 4037 | 2 | 151 | 2921 | 4096 | 7017 |
| 1348 | | 104054 | 18 | 2814 | 52830 | 4096 | 56926 |
| 1352 | | 6573 | 2 | 321 | 4564 | 4096 | 8660 |
| 1359 | | 7842 | 1 | 200 | 4256 | 4096 | 8352 |
| 1372 | | 26850 | 7 | 980 | 15345 | 4096 | 19441 |
| 1375 | | 5042 | 2 | 164 | 3388 | 4096 | 7484 |
| 1380 | | 20086 | 6 | 721 | 12085 | 4096 | 16181 |
| 1385 | | 8361 | 4 | 257 | 4241 | 4096 | 8337 |
| 1386 | | 14532 | 4 | 414 | 8077 | 4096 | 12173 |
| **1404** | yes | 6528 | 4 | 275 | 4259 | 4096 | 8355 |
| 1407 | | 49818 | 2 | 400 | 16408 | 4096 | 20504 |
| **1428** | yes | 2344 | 2 | 106 | 1800 | 4096 | 5896 |

The largest constructed request is `#1348` (~53k input tokens, ~57k estimated max usage). That is inside a 128k-context GPT-4o window under this heuristic. No PR was truncated by a model context limit in this preflight; the only bound applied is the protocol 200-line excerpt cap.

## Totals

| Item | Value |
|---|---|
| Estimated total input tokens, 3-PR pilot | **15,019** |
| Estimated total input tokens, 33 PRs | **327,648** |
| Estimated worst-case output tokens, 3-PR pilot | **12,288** (4096 × 3) |
| Estimated worst-case output tokens, 33 PRs | **135,168** (4096 × 33) |
| Estimated worst-case output tokens, 2 models × 33 PRs | **270,336** (4096 × 66) |

## Provisional cost estimate (not actual API cost)

Rates from `configs/llm_a.json` only. Worst-case output assumes every call emits the full `max_tokens` cap.

| Scope | Provisional USD |
|---|---|
| 3 PRs (LLM A rates) | **$0.16** |
| 33 PRs (LLM A rates) | **$2.17** |
| 2 models × 33 PRs (LLM A rates doubled as a stand-in) | **$4.34** |

These numbers will not match the invoice. Live `usage.prompt_tokens` / `usage.completion_tokens` are the measurement after a run.

## Runner checks

Verified in code, tests, and by scanning the constructed system+user text for every corpus PR:

| Check | Result |
|---|---|
| Human review comments (`comments.json`, `reviews.json`) | Not read by context construction; no unique review-only lines in the 33 prompts |
| Human gold labels (`data/human_review.csv`) | Not read by the runner; no unique gold text in the 33 prompts |
| Linter findings (`data/lint_findings.csv`) | Not read by the runner; file is empty and unused here |
| `GITHUB_TOKEN` as prompt content | Not referenced in the model package; env value (unset in this session) not inserted |
| `OPENAI_API_KEY` as prompt content | Used only as an HTTP `Authorization` header in the client; preflight does not load it |
| Raw responses preserved | `analyze_pr` writes `raw_response.json` and `raw.txt` even when parse fails |
| Full-corpus execution | Bare `python scripts/run_models.py` exits 2. Passing all 33 `--pr` values also exits 2 until `--approve-full-corpus` is set after the pilot is approved. `--pilot` still runs only `#1404`, `#702`, `#1428`. |

Machine-readable copy: `data/llm_context_preflight.csv`.
