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

Frozen primary-reference count: **75** unique atomic findings (33 defect, 42 design).

Frozen on 2026-09-14 after resolving the two remaining ambiguities. No `annotation_status=ambiguous` rows remain.

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
- Hypothetical / non-blocking “second look” notes that are not concrete defect or design issues in the merge-anchored change (see ambiguous-case resolution below)

## Atomicization

One row = one independently evaluable issue. Multi-issue review bodies were split (`atomic_issue_id` = `H-{pr}-{comment_id}-{seq}`).

Original GitHub text is stored in `original_comment`. `normalized_issue` is a concise restatement and does not replace the original.

## Schema clarifications (not protocol amendments)

1. Frozen `docs/annotation_schema.md` lists `source` as `issue` or `inline`. Phase 4 already extracts `review_body`. The annotation table keeps the real source. Class definitions were not changed.
2. Human logins posting Claude-generated review text are **not** bots. They are classified by what the posted text communicates.
3. `in_reference_set` in code now also takes `is_pr_author` and `about_the_change`. That implements protocol §7 plus the operationalization above.

## Ambiguous-case resolution (2026-09-14)

Both leftover findings were resolved from the merge-anchored PR diffs, the exact review text, and surrounding code. No model or linter output was used. `protocol.md` was not changed.

### `H-1313-3771182794-1` → `question`, not gold

1. **What the reviewer identified.** burma-shave noted that if a trip is in `tripsByID` but its route is missing from `routeAgencyMap`, `agencyID` could be `""` and `situationID()` could emit a bare alert ID. They called the collision risk “theoretical,” said reachability depends on whether `GetRoutesByIDs` can return fewer routes than `routeIDSet`, and asked for “a second look, not necessarily blocking.”
2. **What the code actually does.** In the merge-anchored `#1313` diff, `tripSituationRefs` does not fall through with an empty agency. If the trip is unindexed *or* `routeAgencyMap` has no entry, it returns `situationRefsForTrip`, which resolves route/agency itself. A comment in that hunk states the empty-agency risk and the fallback. `TestTripSituationRefsAgencyFallback` covers both a populated map and an empty map and requires the combined-form ID on both paths.
3. **Reachable / actionable?** The silent bare-ID path the comment describes is not present in the change under evaluation. The reviewer also did not treat the note as a required change.
4. **Class / gold.** `question`, `in_reference_set=false`. This is a reachability check, not a concrete defect or a design change the reviewer required.
5. **Why this follows the rules.** Defect requires a concrete correctness problem **in the change**. Design requires a maintainability/API problem the reviewer **treats as needing a change**. Neither holds. Golding it would expect tools to report a bug the merge-anchored diff already guards.

### `H-1407-5055923018-7` → `question`, not gold

1. **What the reviewer identified.** Item 7 of burma-shave’s review is labeled “Design note.” If a *future* arrivals-for-location caller looped `arrivalsForStop` across agencies on one accumulator, `alertAgencyID` could lock to the first agency. They said it was “worth flagging.” Requested changes were “primarily on #1 and #2”; the rest were follow-up candidates.
2. **What the code actually does.** This PR’s only production caller is the single-stop handler (`newArrivalsAccumulator(stopAgencyID)`). Stop-level alerts use that same scalar. The merge-anchored comment on `arrivalsAccumulator` says the field is “single-caller by design” and that a multi-stop caller “must pass a per-stop agency ID to `situations.add` directly instead.”
3. **Reachable / actionable?** The mis-namespace path requires a second caller that does not exist in this PR. Current single-stop behavior matches the pre-extract `alertAgencyID := stopAgencyID` local. The reviewer did not request a change to the field for this merge.
4. **Class / gold.** `question`, `in_reference_set=false`. Future-caller hypothetical; not a concrete current design issue the reviewer treated as needing a change.
5. **Why this follows the rules.** Design is “a maintainability or API-shape problem that a reviewer treats as needing a change (not mere taste).” A “worth flagging” note deferred behind two merge blockers is not that. Defect does not apply: current responses are not wrong.

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
- no `annotation_status=ambiguous` rows remain after freeze
- original comment text matches the unlabeled extract
- extract CSVs still have empty `class` / `in_reference_set` label columns
- rebuilding from `phase5_atoms.py` matches `data/human_review.csv`

## Counts (no tool scores)

| Quantity | Value |
|---|---|
| PRs | 33 |
| Independent human comments | 198 |
| Atomic findings | 266 |
| defect | 56 |
| design | 76 |
| style | 16 |
| question | 2 |
| process_other | 116 |
| Primary reference set | 75 |
| Ambiguous | 0 |

Findings by stratum: concurrency 22, api_gtfs 167, database 32, test_refactor 45.

Primary-reference findings by stratum: concurrency 6, api_gtfs 46, database 9, test_refactor 14.

No LLM, open-model, or `golangci-lint` precision/recall/F1 was computed.

## Rebuild

```bash
python scripts/build_human_review.py
python scripts/validate_human_review.py
```
