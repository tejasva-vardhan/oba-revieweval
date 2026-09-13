# Data

| File | Role |
|---|---|
| `candidates.md` | Frozen candidate list of 30 Maglev PRs (human-vs-bot still incomplete) |
| `candidates/pr_candidates.csv` | Same 30 PRs in tabular form |
| `candidates/pr_candidates.csv` | Machine-readable copy of that list |
| `candidates_raw.json` | Search-API dump used during discovery |
| `author_pr_review_signal.json` | Comment-API check on the author's 12 Maglev PRs |
| `human_review.csv` | Empty schema header; Phase 5 fills rows |
| `findings.csv` | Empty schema header; Phase 9 fills rows |

Do not commit raw diffs that include secrets. Do not commit contributor emails or private profile fields.
