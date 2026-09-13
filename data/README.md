# Data

| File | Role |
|---|---|
| `candidates.md` | Frozen discovery list of 30 Maglev PRs |
| `candidates/pr_candidates.csv` | Same 30 PRs; do not rewrite |
| `candidates/pr_verification.csv` | Phase 4 eligibility for the original 30 |
| `candidates/additional_considered.csv` | Extra search hits and accept/reject reasons |
| `candidates/recommended_corpus.csv` | Recommended gold set (n = 33) |
| `raw/prs/702/` | One end-to-end export |
| `extracted/prs/702/` | Unlabeled human/bot/author partitions |
| `raw/cache/` | Local GitHub JSON cache (gitignored) |
| `candidates_raw.json` | Search-API dump used during discovery |
| `author_pr_review_signal.json` | Comment-API check on the author's 12 Maglev PRs |
| `human_review.csv` | Empty schema header; Phase 5 fills rows |
| `findings.csv` | Empty schema header; Phase 9 fills rows |

Do not commit raw diffs that include secrets. Do not commit contributor emails or private profile fields.
