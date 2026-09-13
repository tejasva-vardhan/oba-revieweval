# LLM A pipeline pilot (Phase 6B)

Date: 2026-09-14.

This document records the **engineering** pilot for the GPT-class review pipeline. It does **not** amend `protocol.md`, `research_questions.md`, `prompts/llm_review_v1.md`, or `data/human_review.csv`.

The pilot exists only to validate that one frozen prompt, one recorded model, and merge-SHA-anchored context can be sent, stored, and parsed. It is **not** a scoring run.

## Pilot PRs (chosen before any model call)

Selected from the recommended corpus for **stratum coverage**, **non-zero primary gold**, and **modest diffs** so the pipeline can be inspected. Not chosen because the model was expected to do well or poorly on them. Clean-change PRs (`#271`, `#541`, `#691`, `#756`, `#1315`, `#1329`, `#1352`, `#1375`, `#1386`) were excluded because they have no gold for later scoring. The largest API diffs (`#1348`, `#1317`) were left for the full run; they are context-size stress tests, not parser tests.

| PR | Stratum | Gold findings | Changed files | Diff bytes | Merge SHA | Why this one |
|---|---|---|---|---|---|---|
| `#1404` | api_gtfs | 3 | 4 | 6703 | `cb2c54171d9004df29ca7f1d51e354179f676d15` | Mid-size API/GTFS change with gold |
| `#702` | database | 3 | 4 | 18880 | `abebfc2f9193603f67b25ac6b976623623857826` | Database/transaction helper; same representative PR as the Phase 6A single-PR lint check |
| `#1428` | concurrency | 2 | 2 | 2396 | `239664889cbb9500a4943c4ba5ac386b4fd2b09a` | Concurrency-stratum PR with gold; small enough to inspect the request |

Human gold counts are listed only to show the PRs are eligible. **Those labels are not sent to the model.**

## What the model is allowed to see

Protocol §11:

1. PR title (from `metadata.json`)
2. Unified merge-parent three-dot diff (`diff.patch`)
3. At most 200 lines of post-merge file text per changed Go file, covering the hunks

Not sent: issue comments, review bodies, inline comments, human labels, linter findings, other PRs, RAG, extra agents.

## Frozen prompt

`prompts/llm_review_v1.md` (`llm_review_v1`). The file was readable as a system prompt: it already requires JSON `findings` with `title`, `severity`, `category`, `path`, `line`, `rationale`, `recommendation`. It was **not** rewritten after this document was created.

## Model A

Project config: `configs/llm_a.json`. Credential: `OPENAI_API_KEY` only (environment or local `.env`). Never printed, logged, or written to artifacts.

LLM B is not part of this pilot.

## Commands

```bash
python scripts/run_models.py --pilot
```

This command runs **only** the three PRs above. It does not iterate the remaining 30.

Live API calls require `OPENAI_API_KEY` in the environment or a local `.env`. The key is never printed or written to artifacts. If the key is absent, the runner exits without inventing a credential and without writing fake findings.

## Out of scope

Precision, recall, F1, harm rate, extra-valid rate, and LLM-vs-linter comparison are not computed here.
