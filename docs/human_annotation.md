# Human annotation (Phase 5)

Annotation date: 2026-09-14.

This file records how the independent human reference set was constructed. It does **not** amend `protocol.md`, `research_questions.md`, or the class definitions in `docs/annotation_schema.md`.

The labeled table is `data/human_review.csv`. Raw GitHub exports and unlabeled extract CSVs were not overwritten.

## Annotator status

Single-annotator study; inter-rater agreement could not be measured.

A second person was not available. No labels were fabricated for a second rater.

## What was labeled

Every independent-human comment on the recommended corpus (n = 33 PRs; 198 comments).

Comments by `tejasva-vardhan` are never independent gold. PR-author comments are never gold. Bot comments are never gold. Process-only comments are never defect/design gold.

## Class definitions (unchanged)

Used exactly as frozen in `docs/annotation_schema.md`:

- **defect:** concrete correctness, reliability, security, or data-integrity problem in the change
- **design:** maintainability or API-shape problem the reviewer treats as needing a change (not mere taste)
- **style:** formatting, naming-only, or nits with no behavioral stake
- **question:** request for explanation that does not assert a defect
- **process_other:** CI, CLA, review process, LGTM without substance, changelog/git nits

Classification used the reviewer's meaning after reading the comment (and the PR diff when the comment was incomplete), not keyword matching.

## Primary reference set

Protocol §7 / annotation schema: primary gold = non-author human comments labeled **defect** or **design**.

Style, question, and process_other comments are recorded so every independent `comment_id` is covered. They are **not** issues automated systems are expected to detect. Review-comment presence is not the same as software-defect presence.

Final provisional primary-reference count: **75** unique atomic findings (33 defect, 42 design).

This count is **not** a freeze while two findings remain `annotation_status=ambiguous`. Those two are excluded from gold until resolved.

## Gold-set decision rule used here

`in_reference_set` is true only when all of the following hold:

1. `class` is `defect` or `design`
2. the commenter is not the PR author
3. the commenter is not `tejasva-vardhan`
4. `annotation_status` is `resolved` (ambiguous findings are not forced into gold)
5. the reviewer is identifying an issue **about the change under review** that they treat as needing a change on this PR

Rule 5 is a Phase 5 operationalization, not a silent protocol rewrite. Evaluation will score tools against the PR diff. Golding pre-existing, follow-up, out-of-scope, or explicitly optional notes would require models to invent issues in untouched code.

## Exclusions from primary gold (still stored)

- Complimentary approvals, empty review submissions, “no issues found”
- Merge/rebase/conflict/CLA/CodeRabbit-ping text
- Claude-generated “no issues found” posts by human logins (still human comments; classified by content)
- Style nits and optional/non-blocking suggestions that are not concrete correctness bugs
- Pre-existing / other-handler / “not this PR” / “follow-up” observations
- Later restatements of an already-golded unique issue (same reviewer or another reviewer). The first complete instance is gold; later copies are stored with `in_reference_set=false` and a restatement note
- Bugs a PR already fixed, when the later review only confirms the fix
- Ambiguous findings, until resolved

## Atomicization

One row = one independently evaluable issue. Multi-issue review bodies were split (`atomic_issue_id` = `H-{pr}-{comment_id}-{seq}`).

Original GitHub text is stored in `original_comment`. `normalized_issue` is a concise restatement and does not replace the original.

## Schema clarifications (not protocol amendments)

1. Frozen `docs/annotation_schema.md` lists `source` as `issue` or `inline`. Phase 4 already extracts `review_body`. The annotation table keeps the real source. Class definitions were not changed.
2. Human logins posting Claude-generated review text are **not** bots. They are classified by what the posted text communicates.
3. `in_reference_set` in code now also takes `is_pr_author` and `about_the_change`. That implements protocol §7 plus the operationalization above.

## Ambiguous findings (unresolved)

Do not treat the reference set as frozen until these are decided.

| atomic_issue_id | PR | Why unresolved |
|---|---|---|
| `H-1313-3771182794-1` | #1313 | Reviewer flags a possible unprefixed alert ID when `routeAgencyMap` misses, then says reachability is unclear and it is “not necessarily blocking.” |
| `H-1407-5055923018-7` | #1407 | Reviewer flags `alertAgencyID` as a future multi-stop trap and says it is “worth flagging”; requested changes were primarily items 1–2. |

Both are stored with `annotation_status=ambiguous` and `in_reference_set=false`.

## Clean-change PRs

Protocol §4.6 allows keeping a PR with no defect/design gold as an explicit clean-change note. These recommended PRs have **no** primary-reference findings after annotation:

`#271`, `#541`, `#691`, `#756`, `#1315`, `#1329`, `#1352`, `#1375`, `#1386`

They remain in the corpus. They are not dropped to improve later scores.

## Quality control

`scripts/validate_human_review.py` and `tests/test_human_review.py` check:

- every recommended PR is present
- every independent `comment_id` is covered
- no study-author, PR-author, or bot rows
- process_other is never gold
- ambiguous rows are never gold
- original comment text matches the unlabeled extract
- extract CSVs still have empty `class` / `in_reference_set` label columns
- rebuilding from `phase5_atoms.py` matches `data/human_review.csv`

## Counts (no tool scores)

| Quantity | Value |
|---|---|
| PRs | 33 |
| Independent human comments | 198 |
| Atomic findings | 266 |
| defect | 57 |
| design | 77 |
| style | 16 |
| question | 0 |
| process_other | 116 |
| Primary reference set | 75 |
| Ambiguous | 2 |

Findings by stratum: concurrency 22, api_gtfs 167, database 32, test_refactor 45.

Primary-reference findings by stratum: concurrency 6, api_gtfs 46, database 9, test_refactor 14.

No LLM, open-model, or `golangci-lint` precision/recall/F1 was computed.

## Rebuild

```bash
python scripts/build_human_review.py
python scripts/validate_human_review.py
```
