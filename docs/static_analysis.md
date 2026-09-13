# Static-analysis baseline (Phase 6A)

Date: 2026-09-14.

This document is enough for another researcher to reproduce the `golangci-lint` baseline. It does **not** amend `protocol.md`. Human labels in `data/human_review.csv` were not modified. No LLM, OpenAI API, open-model, or comparative scoring run is part of this phase.

## Run result (2026-09-14)

| Item | Value |
|---|---|
| PRs analyzed | **33 / 33** (`execution_status=ok`) |
| Execution failures | **0** |
| Change-scoped findings | **0** |
| Raw issues before scope filter | **0** |
| Findings dropped as outside the PR diff | **0** |
| PRs with zero findings | **all 33** |
| `#457` | Analyzed merge `e1044a52bfdca7b1297140514df56eb4b1724cf8`; `first_parent_empty=true`; target `internal/restapi/routes_for_agency_handler.go` |
| Config hash | `sha256:8ed7fb90c68635289e5645f6cf673a911145a1a59b969e9cc50c94790a302aa7` |
| Host `golangci-lint version` | `golangci-lint has version 2.13.2 built with go1.27.0 from 27774aaf on 2026-08-27T23:01:12Z` |

Zero change-scoped findings is a measured baseline, not a parser failure. Every `raw.json` has `"Issues":[]` with `govet`, `staticcheck`, and `typecheck` enabled. A synthetic module with a `fmt.Printf("%s", 1)` defect (see `tests/test_lint_positive_control.py`) produces findings under the same binary and config, so the empty corpus is not a silent no-op.

This is consistent with protocol §9: the baseline is `govet` + `staticcheck` SA\* on already-merged Maglev code, change-scoped. Those analyzers do not target the domain/API/concurrency design issues that dominate the human gold set. Comparative scoring is deferred.

## Tool

| Field | Value |
|---|---|
| Tool | `golangci-lint` |
| Exact version | **2.13.2** |
| Release tag | `v2.13.2` (2026-08-27) |
| Installation | Official GitHub release binary, checksum-verified |
| Installer | `python scripts/install_golangci_lint.py` |
| Binary location | `tools/bin/golangci-lint` (Windows: `golangci-lint.exe`; gitignored) |

Windows amd64 asset and SHA-256 (from the official `golangci-lint-2.13.2-checksums.txt`):

```text
4735fdc8e84a0cfb7a15a1c364a650942f88215e0d36c674ebc4024f7b554524  golangci-lint-2.13.2-windows-amd64.zip
```

Linux and macOS checksums are pinned in `src/oba_revieweval/lint/constants.py`. Do not use whatever `golangci-lint` happens to be on `PATH`.

## Maglev's own lint setup (inspected, not modified)

Maglev has **no** committed `.golangci.yml` / `.golangci.yaml` at HEAD or at the corpus merge SHAs (`#271`, `#702`, `#1428` checked).

Historical Makefiles invoked `golangci-lint run --build-tags "sqlite_fts5"` with implicit defaults, or later `go vet -tags "$(BUILD_TAGS)"`. Those defaults include style-adjacent linters. This study does **not** adopt Maglev's implicit default set and does **not** edit Maglev.

## Research configuration

File: `configs/golangci-research.yml` (version-controlled; config format `version: "2"`).

Enabled analyzers:

| Analyzer | Why included |
|---|---|
| `govet` | Protocol §9 minimum. Default govet analyzers only (printf, atomic, copylocks, lostcancel, loopclosure, and the rest of the govet default set). Extra analyzers such as `shadow` / `fieldalignment` are off. |
| `staticcheck` | Protocol §9 minimum. Restricted to **SA\*** correctness checks. `S*` (simplifications), `ST*` (style), and `QF*` (quickfixes) are disabled so the baseline is defect-oriented static analysis, not a style suite. |

No other linters are enabled (`linters.default: none`). Issue caps are disabled (`max-issues-per-linter: 0`, `max-same-issues: 0`, `uniq-by-line: false`) so atomic issues are not collapsed.

Build tags are **not** stored in the YAML (so one config hash applies to all 33 PRs). They are read from the merge-SHA `Makefile` (`BUILD_TAGS` or the historical `golangci-lint --build-tags` line) and passed on the CLI. Fallback if neither is present: `sqlite_fts5`.

## Exact commands

```bash
python scripts/install_golangci_lint.py
python scripts/run_linter.py --pr 702    # single-PR validation
python scripts/run_linter.py             # all 33 recommended PRs
python scripts/parse_findings.py         # reparse stored raw.json only
pytest
```

Per PR, the runner:

1. Resolves the merge SHA from `data/candidates/recommended_corpus.csv` (never Maglev `HEAD`).
2. Reconstructs the changed-file list with the existing merge-parent three-dot logic (`git diff parent1...parent2` of that merge commit).
3. Checks the SHA out in a disposable worktree at `data/raw/cache/lint-worktree` (gitignored).
4. Verifies `git rev-parse HEAD` in the worktree equals the recorded merge SHA.
5. Runs `go mod download` in that worktree.
6. Invokes the pinned binary on the **packages** that contain those files. `go/packages` rejects a single `run` that names `.go` files from more than one directory, so the CLI arguments are package paths such as `./gtfsdb` `./internal/restapi`. Findings are still filtered to the changed-file list afterward.

Equivalent linter invocation (paths abbreviated):

```text
tools/bin/golangci-lint run
  --config configs/golangci-research.yml
  --build-tags "<tags from that SHA's Makefile>"
  --output.json.path=data/raw/lint/<pr>/raw.json
  --output.text.path=data/raw/lint/<pr>/raw.txt
  --output.text.colors=false
  --uniq-by-line=false
  -- <package dirs of changed .go files>
```

Working directory is the worktree, not the study repo and not Maglev `HEAD`.

## Commit / tree selection

Protocol §9: analyze the **post-merge** tree for files touched by the PR.

| Object | Source |
|---|---|
| Merge SHA | `recommended_corpus.csv` (must match `data/raw/prs/<n>/metadata.json` when that file exists) |
| Analyzed tree | That merge commit (the merged result) |
| Changed files | `git diff <parent1>...<parent2>` of the merge commit (`diff_mode=merge_parents_three_dot`) |
| First-parent delta | Recorded only as a check |

`HEAD` of the Maglev clone is never used as a substitute. A later main snapshot is never used.

### `#457`

First-parent `git diff SHA^1 SHA` is empty: the same `RLock` already landed on main via `#456`. The three-dot range of merge `e1044a52bfdca7b1297140514df56eb4b1724cf8` still contains `internal/restapi/routes_for_agency_handler.go`. That file is linted on the `#457` merge tree. The PR is not dropped.

## Changed vs unchanged code

Protocol §9: “Findings outside the PR diff are dropped so the comparison is change-scoped.”

Operationalization (file-scoped):

* A finding is **in-scope** iff its path is in the reconstructed changed-file list (including a rename's old path).
* Findings that `golangci-lint` emits on other files in the same package are stored in `dropped_outside_diff.json` and **excluded** from `findings.json` / `data/lint_findings.csv`.
* Findings on **unchanged lines of a changed file** are **kept**. Protocol §9 names “files touched by the PR” as the analysis unit and does not specify hunk-line matching. Hunk-level dropping was not invented.

Deleted `.go` files cannot be linted on the post-merge tree (they are gone). Non-Go files (SQL, YAML) are not golangci-lint targets.

This distinction is recorded, not scored, in Phase 6A.

## Environment assumptions

Recorded for the 2026-09-14 run:

* Host OS: Windows 10 (build 26200), amd64
* Host Go: `go1.25.4 windows/amd64` (`GOTOOLCHAIN=auto`)
* Corpus `go` directives: `1.24.2` (PRs `#271`–`#756`) and `1.25.0` (`#1277`–`#1428`)
* CGO: `CGO_ENABLED=1`, `CGO_CFLAGS=-DSQLITE_ENABLE_FTS5`
* C compiler: MSYS2 MinGW64 `gcc` 15.2.0 at `C:\msys64\mingw64\bin\gcc.exe` (Maglev uses `github.com/mattn/go-sqlite3`)
* Module cache: the host `GOMODCACHE`; `modules-download-mode: readonly` after `go mod download`
* Maglev clone: `data/raw/cache/maglev` (gitignored)
* `relative-path-mode: gitroot` so the research YAML (outside Maglev) does not need a `go.mod` beside it
* PATH must put the official Go toolchain ahead of MSYS2. MSYS2 ships a trimmed `go.exe` that fails `go env GOMOD` (`GOROOT` unset). The runner prefers `C:\Program Files\Go\bin`.

A C compiler is required. Do not silently fall back to `CGO_ENABLED=0`.

## Parser behavior

* Primary input is `raw.json` (`Issues` array). `Issues: null` or `[]` means zero findings.
* Text output in `raw.txt` is stored unmodified and used only as a fallback parser in tests.
* Process stdout/stderr are stored separately in `process.stdout.txt` / `process.stderr.txt`. They are not spliced into `raw.txt`.
* One JSON issue → one atomic row. Same file/line with different rules stays two rows. `uniq-by-line` is off.
* `raw_finding_id` is `L-{pr}-{n}` after a deterministic sort on file, line, column, rule, message.
* Paths are normalized to repo-relative POSIX paths (worktree prefix stripped).
* Malformed JSON is an execution failure, not an empty finding set.

## Outputs

| Path | Role |
|---|---|
| `data/raw/lint/<pr>/raw.txt` | Unmodified text formatter output |
| `data/raw/lint/<pr>/raw.json` | Unmodified JSON formatter output |
| `data/raw/lint/<pr>/findings.json` | Change-scoped atomic findings |
| `data/raw/lint/<pr>/dropped_outside_diff.json` | Parsed issues whose file is not in the PR diff |
| `data/raw/lint/<pr>/run.json` | Command, version, SHAs, tags, exit status |
| `data/lint_findings.csv` | Aggregate atomic findings |
| `data/lint_manifest.csv` | One row per PR |

Finding fields: `pr_number`, `tool`, `tool_version`, `commit_sha`, `file`, `line`, `column`, `rule`, `message`, `severity`, `raw_finding_id`.

No `tp_useful` / precision / recall / F1 / harm / extra-valid labels are assigned here.

## Known limitations

1. The linter version (2026-08) is newer than the older corpus merges. Historical trees are analyzed with a current analyzer, not the golangci-lint that Maglev CI used at merge time.
2. File-scoped change filtering may keep findings on pre-existing lines inside a touched file. Hunk-scoped filtering was not specified by the protocol and was not applied.
3. `staticcheck` SA\* and default `govet` do not cover domain/API/concurrency design issues that dominate the human gold set. That comparison is deferred until the LLM pipeline exists.
4. SQL / sqlc files are in some PRs but are not golangci-lint inputs.
5. Typechecking needs CGO + the merge tree's modules. A missing compiler or module fetch is an execution failure, not a finding.

## Replay checklist

1. Clone Maglev to `data/raw/cache/maglev` and ensure every recommended merge SHA is present.
2. Install a C compiler usable as `CC` for `go-sqlite3`.
3. `python scripts/install_golangci_lint.py` — confirm printed version `2.13.2`.
4. `python scripts/run_linter.py`
5. `pytest` — parser, scope, and manifest tests must pass.
6. Do not run `scripts/run_models.py` or `scripts/score_findings.py` as part of this phase.
