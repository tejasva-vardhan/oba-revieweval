# Annotation schema

## Human review comments

Source: GitHub issue comments and inline review comments on the PR, after dropping bots (CodeRabbit, Dependabot, GitHub Actions, Sonar, and any `*[bot]` login).

**Never** treat comments by `tejasva-vardhan` as independent ground truth, including on PRs the author did not write.

| Field | Meaning |
|---|---|
| `pr_id` | Maglev PR number |
| `comment_id` | GitHub comment id |
| `source` | `issue` or `inline` |
| `author_login` | Public GitHub login |
| `is_pr_author` | True if commenter is the PR author |
| `text` | Comment body (public) |
| `path` | File path if inline |
| `class` | `defect` / `design` / `style` / `question` / `process_other` |
| `atomic_issue_id` | Stable id after splitting multi-issue comments |
| `in_reference_set` | True iff class is `defect` or `design` **and** `is_pr_author` is false |

### Class definitions

- **defect:** A concrete correctness, reliability, security, or data-integrity problem in the change.
- **design:** A maintainability or API-shape problem that a reviewer treats as needing a change (not mere taste).
- **style:** Formatting, naming-only, or nits with no behavioral stake.
- **question:** A request for explanation that does not assert a defect.
- **process_other:** CI, CLA, review process, “LGTM” without substance, changelog nits.

Style, questions, and process comments are **not** “issues worth catching.” Using them as gold would reward models for matching chatter, which DeepCRCEval shows is common in OSS review datasets.

If one comment states two defects, split into two rows.

## Tool findings (linter / LLM)

| Field | Meaning |
|---|---|
| `finding_id` | Stable id |
| `pr_id` | PR number |
| `tool` | `golangci-lint` / `llm_a` / `llm_b` |
| `category` | `concurrency` / `api_gtfs` / `database` / `test_refactor` / `other` |
| `text` | Atomic finding |
| `location` | File and line if available |
| `label` | `tp_useful` / `incorrect` / `harmful` / `extra_valid` |
| `human_issue_id` | Matching reference issue, if any |
| `rationale` | Short reason for the label |

### Labels

- **tp_useful:** Matches a reference (defect/design) human issue; applying it would address that issue without breaking behavior.
- **incorrect:** Wrong about the code, or a non-issue.
- **harmful:** Incorrect **and** applying the recommendation could plausibly break API behavior, persisted data, transaction semantics, concurrency correctness, or other externally observable functionality. Not used for mere nits.
- **extra_valid:** A real issue humans did not mention; not incorrect; not used in recall (recall uses the human reference only). Extra-valid items are excluded from the precision denominator's false-positive count: they are reported separately so we do not punish tools for finding true misses.

A finding cannot be both `incorrect` and `extra_valid`. `harmful` implies incorrect-and-dangerous; it is also counted in the incorrect rate.

## Inter-rater agreement

If a second annotator labels ≥20% of findings, report percent agreement and Cohen's κ on `label`. If not, the report must state single-annotator bias.
