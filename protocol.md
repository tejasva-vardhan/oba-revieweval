# Protocol (frozen 2026-09-13)

Do not change this method after seeing results in order to improve scores. If a change is required for feasibility or ethics, add a dated amendment at the bottom.

## 1. Research question

Do general-purpose LLMs recover the same issue classes that human reviewers raise on merged OneBusAway Maglev Go/backend pull requests, and at what incorrect and harmful finding cost relative to static analysis?

## 2. Hypothesis

A prompted LLM may recover more semantic or domain issues than `golangci-lint`, particularly around concurrency, API contracts, and domain logic, but will also generate more incorrect findings and some harmful findings.

## 3. Corpus

Public merged pull requests from [OneBusAway/maglev](https://github.com/OneBusAway/maglev) (Go REST API / GTFS backend). Metadata lives in `data/candidates.md` and `data/candidates/pr_candidates.csv`. Diffs and comments will be exported in Phase 4 into `data/prs/` and are not in this scaffold.

## 4. Inclusion criteria

A PR is eligible if all of the following hold:

1. Repository is `OneBusAway/maglev`.
2. State is merged; merge SHA is recorded.
3. Primary language of the change is Go (or SQL/sqlc that the Go server executes).
4. The change is non-trivial: not typo-only, not format-only, not dependency-bump-only, not docs-only.
5. At least one **human** (non-bot) review comment or issue comment exists that is not written by `tejasva-vardhan`.
6. After annotation, at least one human comment is classed `defect` or `design`, **or** the PR is explicitly kept as a “clean change” note — default is to require ≥1 reference issue. The pilot prefers PRs with meaningful review, not silent merges.

## 5. Exclusion criteria

- Dependabot and other bot-authored PRs.
- Docs-only, OpenAPI-path-only, or changelog-only PRs.
- PRs whose only discussion is a bot (for example CodeRabbit) plus the author.
- PRs authored by `tejasva-vardhan` **unless** another human left review or issue comments (confirmed so far: `#507`, `#702`).
- Using the study author’s comments as gold on any PR.

## 6. Stratification

Target about 30 PRs, roughly:

| Stratum | Target | Examples in the candidate list |
|---|---|---|
| Concurrency / races / caching correctness | 4–6 | `#1374`, `#1428`, plus any Phase 4 PRs with lock/race review |
| API / GTFS / domain logic | 12–14 | `#1277`, `#1316`, `#1317`, `#1352`, `#1380`, `#1348`, … |
| Database / transactions / import | 6–8 | `#702`, `#1372`, `#1378`, `#1288` |
| Test / refactor | 6–8 | `#1298`, `#1300`, `#1407`, `#1365` |

Do not select only PRs expected to make LLMs look good. The candidate list was taken from merged Maglev PRs with ≥2 issue comments, then filtered by title.

## 7. Human-review annotation

Follow `docs/annotation_schema.md`. Primary reference set = non-author human comments labeled `defect` or `design`.

## 8. LLM models

- **LLM A (GPT-class):** one hosted API model, exact name and snapshot recorded at run time in `results/run_manifest.json`. Not chosen here to avoid pretending a key exists.
- **LLM B (open model):** one inexpensive hosted open-weight API if credentials exist; otherwise document “LLM B not run” rather than inventing a local GPU stack.

Do not start model calls until the corpus export and prompt `prompts/llm_review_v1.md` are frozen.

## 9. Static-analysis baseline

`golangci-lint` on the **post-merge** tree for files touched by the PR (or the merge commit). Enable at least `govet` and `staticcheck`. Record the linter version. Findings outside the PR diff are dropped so the comparison is change-scoped.

## 10. Prompt

`prompts/llm_review_v1.md` only. Structured JSON findings. No human review text in the prompt. No RAG. No extra agents.

## 11. Context supplied to models

- PR title (public).
- Diff of the PR.
- For each changed Go file, at most a bounded amount of surrounding file text if the diff hunk is incomplete (limit will be recorded in the run manifest; suggested cap 200 lines per file).

No issue thread, no review comments, no other PRs.

## 12. Decoding settings

Temperature `0`. One sample per model per PR. Record `max_tokens` and date.

## 13. Number of runs

One frozen run per (PR, tool). No retry-until-better. A failed API call may be retried once for transport errors; the retry is logged.

## 14. Finding extraction

Parse linter output and model JSON into atomic rows (`docs/annotation_schema.md`). One issue per row. Discard empty or purely complimentary text.

## 15. Finding annotation

The study author labels each tool finding: `tp_useful`, `incorrect`, `harmful`, `extra_valid`. Harmful is reserved for recommendations that could break observable behavior if applied.

Second annotator on ≥20% if available; otherwise report single-annotator bias.

## 16. Metrics

Against the human defect/design reference:

- Precision, recall, F1 for `tp_useful` matched to a reference issue.
- Incorrect rate, harmful rate, extra-valid rate.
- Findings per PR; breakdown by stratum and category.

**Do not** use BLEU or ROUGE as primary metrics.

Matching is manual (same issue, not same wording). With n≈30, report descriptive tables. Do not manufacture p-values.

## 17. Threats to validity

- **Construct:** human comments are incomplete gold (DeepCRCEval). Extra-valid findings may be correct.
- **Internal:** single annotator; author contributed to Maglev (bias). Public PRs may be in model training data.
- **External:** one repository, Go, transit API. Not general LLM-review quality.
- **Conclusion:** pilot sample; no significance testing.

## 18. Reproducibility

1. Check out this repo and Maglev at recorded SHAs.
2. Export PRs with `scripts/export_prs.py` (Phase 4).
3. Run linter with recorded `golangci-lint` version.
4. Run models only with user-provided keys.
5. Score with `scripts/score_findings.py`.
6. A third party should be able to replay **one** PR from documented files.

## Amendments

None yet.
