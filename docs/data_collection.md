# Data collection (Phase 4)

Collection date: **2026-09-14**.

This document describes how Maglev pull-request review surfaces were verified and how one PR was exported. It does not change the frozen protocol.

## GitHub API source

- Host: `https://api.github.com`
- Repository: [`OneBusAway/maglev`](https://github.com/OneBusAway/maglev)
- Endpoints used: `GET /repos/{owner}/{repo}/pulls/{n}`, `/files`, `/reviews`, `/comments`, `GET /repos/{owner}/{repo}/issues/{n}/comments`, and `GET /search/issues`
- Client: `src/oba_revieweval/dataset/github.py` (stdlib `urllib`, no extra HTTP dependency)

A public-repo read token in `GITHUB_TOKEN` or `GH_TOKEN` is the intended replay path. This Phase 4 run did **not** have a token in the environment. Public REST responses were retrieved without embedding credentials in URLs and written to a local cache under `data/raw/cache/` (gitignored). No token is stored in this repository.

Replay with a token:

```bash
export GITHUB_TOKEN=...   # do not commit this
python scripts/verify_candidates.py
python scripts/search_additional_candidates.py
python scripts/export_prs.py --pr 702
```

Replay from a filled cache:

```bash
python scripts/verify_candidates.py --cache-only
python scripts/export_corpus.py --cache-only
python scripts/validate_corpus.py
python scripts/build_phase4_artifacts.py
```

## Inclusion criteria (operational)

Applied exactly as protocol §4–§5, without rewriting the protocol:

1. Repository is `OneBusAway/maglev`.
2. PR is merged (`merged` or `merged_at` present); merge SHA recorded when the API returned it.
3. Change includes Go or SQL/sqlc (non-docs, non-dependency-only).
4. At least one **meaningful** independent human review surface exists.
5. Comments by `tejasva-vardhan` are never independent gold, including on other people’s PRs.
6. PR-author comments are never independent gold.
7. Bot comments are never human gold.

“Meaningful” here is Phase 4 verification only: empty approvals, `LGTM`, CLA bots, and short merge-conflict / rebase process notes do not count. Defect/design labeling is Phase 5 (protocol §4.6).

Review **bodies** on `GET /pulls/{n}/reviews` count. The PR object’s `review_comments` count can be 0 while `/reviews` still has long written reviews.

## Exclusion criteria

- Bot-authored PRs (Dependabot and `user.type == Bot`).
- Docs / OpenAPI / changelog-only or empty file lists.
- Threads that are only bots, the PR author, and/or process-only human text.
- Study-author comments as gold.

A PR with both human and bot comments can remain eligible. Bot text is partitioned out and is not gold.

## Bot classification

A login is a bot if any of the following hold:

- GitHub `user.type == Bot`
- login ends with `[bot]`
- login is in the documented set in `src/oba_revieweval/dataset/actors.py` (CodeRabbit, Dependabot, GitHub Actions, Sonar, CLA assistant, Copilot, Renovate, and similar)

Unknown accounts without a type are `unclassified` and are **not** treated as human gold.

## Author-comment handling

| Actor | Role |
|---|---|
| `tejasva-vardhan` | Never independent gold |
| PR author (any login) | Never independent gold |
| Other human `User` | May be gold after Phase 5 labeling |
| Bot / unclassified | Never gold |

`merged_by` is not a review surface and is not stored as gold.

## Original 30

The frozen list in `data/candidates/pr_candidates.csv` was **not** rewritten.

Verification records: `data/candidates/pr_verification.csv`.

| Outcome | Count | PRs |
|---|---|---|
| Eligible for primary gold | 26 | all original except the four below |
| Excluded, bot-only / no independent review | 1 | `#1365` (reviews `[]`; CodeRabbit + Sonar issue comments) |
| Excluded, independent human not meaningful | 3 | `#1374` (empty APPROVED), `#1284` (`LGTM!` + empty reviews), `#1378` (empty APPROVED + “merge conflicts”) |

`#702` and `#507` stay eligible because other humans left review text. Author comments on those PRs are still not gold.

## Additional search

Keyword search was used only as retrieval (`race`, `mutex`, `RLock`, `deadlock`, `goroutine`, `transaction`). Acceptance required inspecting `/pulls/{n}/reviews`.

Documented in `data/candidates/additional_considered.csv`.

Accepted after review inspection:

| PR | Why accepted |
|---|---|
| `#457` | aaronbrethorst CHANGES_REQUESTED + APPROVED on missing `RLock` |
| `#354` | aaronbrethorst TOCTOU / non-reentrant `RWMutex` deadlock review |
| `#372` | aaronbrethorst race/mutex review on `RoutesForAgencyID` |
| `#541` | aaronbrethorst two-phase locking review |
| `#756` | aaronbrethorst double-locking / `simplelru` review |
| `#691` | aaronbrethorst race + double HTTP write review |
| `#271` | aaronbrethorst `GetStaticData` lock-contract review |

Rejected examples:

- Dependabot sqlite bumps (`#1410`, `#1319`, `#1266`, `#1190`, `#1422`)
- `#456`: independent review exists, but it is the same `routesForAgencyHandler` RLock as `#457`
- Search hits that matched the word “race” in tests/comments but were not inspected as concurrency gold (`#1351` and similar)

The frozen 30 is unchanged. Additional accepts are listed in `data/candidates/recommended_corpus.csv`.

## Recommended corpus

**n = 33** = 26 original eligible + 7 additional.

Stratum counts if the additional accepts are used:

| Stratum | n |
|---|---|
| api_gtfs | 16 |
| concurrency | 8 (1 original usable + 7 additional) |
| database | 4 |
| test_refactor | 5 |

Protocol §6 targeted about 4–6 concurrency PRs. The recommended set is 8 because those PRs met the gold rule. Eligible PRs were not dropped to hit the target, and ineligible PRs were not forced in to reach 30.

## One-PR export (superseded)

`#702` was the Phase 4 example export. That overlay-style file list is replaced by the merge-SHA corpus export below. `#702` remains in the n=33 set.

## Complete raw export (n = 33)

Collection date for the full export: **2026-09-14**.

Every recommended PR now has a merge-SHA-anchored raw export. The Maglev clone used to resolve those SHAs lives at `data/raw/cache/maglev` (gitignored). Diffs are taken from that commit's recorded parents, not from `HEAD`.

All 33 Maglev merges in this set are two-parent merge commits. The reconstructed diff is:

```text
git diff <parent1>...<parent2>
```

where both parents are read from the recorded merge SHA. First-parent `git diff SHA^1 SHA` is recorded only as a check. For `#457` that first-parent delta is empty (the same `RLock` already landed on main via `#456`); the three-dot range of **that merge commit** still contains `internal/restapi/routes_for_agency_handler.go`. The PR was not dropped.

Per PR, `data/raw/prs/<number>/` contains:

| File | Role |
|---|---|
| `metadata.json` | Title, author, merge SHA, parent SHAs, `diff_anchored_to_merge_sha` |
| `diff.patch` | Complete unified diff from those parents (`--binary --find-renames`) |
| `files.json` | Complete changed-file list from the same range (renames, deletes, binaries) |
| `github_files.json` | GitHub PR file list used only for coverage (`/files` or public `pull/N.diff`) |
| `reviews.json` | `/pulls/{n}/reviews` |
| `comments.json` | Issue comments, inline review comments, and review bodies |

`data/extracted/prs/<number>/` partitions comments into independent human, human-meaningful, process-only, bot, and author/study-author. `class` and `in_reference_set` stay empty / false until Phase 5.

Machine-readable completeness: `data/raw/manifest.csv`.

Replay:

```bash
python scripts/export_corpus.py
python scripts/validate_corpus.py
```

Validation fails if any of the 33 recommended PRs is missing a required file, if the reconstructed diff is not anchored to the recorded merge SHA, if a GitHub PR file is absent from the reconstructed list, if author or bot rows appear in independent-human gold, or if process-only rows are mixed into the meaningful-human partition.

Export result for this run: **33/33 complete**. Every diff is anchored to the merge SHA in `recommended_corpus.csv`. No LLM, model evaluation, scoring, or `golangci-lint` run.

## Limitations

1. The Phase 4 prompt named `OneBusAway/onebusaway-application-modules`. The frozen protocol and candidate CSV are Maglev. Collection stayed on Maglev; the protocol was not switched.
2. `GITHUB_TOKEN` was missing. A third party needs a token (or this cache) to replay live pagination.
3. File lists for some of the original 30 were not fully cached during verification. The later n=33 export reconstructs every file list and diff from the merge SHA in a local Maglev clone. GitHub `/files` was used for coverage when the API cache had it; otherwise the public `pull/N.diff` file list was used. Both were checked against the SHA-anchored reconstruction.
4. Protocol §4.6 (defect/design after annotation) is not applied yet.
5. Human review gold can live in review **bodies** even when issue comments are author/bot-only. Issue-comment-only checks undercount gold (`#457` is the example).
6. `#702` has an aaronbrethorst issue comment that is rebase/process; the gold-quality text is in the three review bodies.

## What was not run

No LLM, OpenAI API, open-weight model, or `golangci-lint` run. This phase only verifies the dataset, completes the raw export, and checks the extraction pipeline.
