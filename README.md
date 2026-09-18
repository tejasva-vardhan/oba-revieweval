# OBA-ReviewEval

Evaluate how well **human code review**, **golangci-lint**, and a **prompted LLM** agree on merged pull requests in [OneBusAway/maglev](https://github.com/OneBusAway/maglev) (Go transit REST API: GTFS, SQLite, HTTP handlers).

The repo is the study machinery plus a frozen corpus: PR exports, human labels, a pinned linter baseline, and an LLM runner. Precision / recall tables are **not** in `results/` yet — the scoring CLI is stubbed until the model phase is run.

## Question

Do general-purpose LLMs recover the same **defect / design** issues that human reviewers wrote on merged Maglev PRs, and at what incorrect or harmful-finding cost compared with `golangci-lint`?

Harmful = a finding that would plausibly break API behaviour, persisted data, transactions, or concurrency if applied. Process comments, nits, and questions are labelled but are **not** gold.

Protocol: [`protocol.md`](protocol.md). Questions: [`research_questions.md`](research_questions.md).

## What is in the box

| Piece | Location | State |
|---|---|---|
| 33 merged Maglev PRs (diffs, reviews, issue comments) | `data/raw/prs/` | frozen |
| Human labels | `data/human_review.csv` | frozen 2026-09-14 |
| Gold defect/design set | `in_reference_set=true` in that CSV | **75** findings |
| Atomic split of comments | same CSV | **198** comments → **266** atoms |
| golangci-lint 2.13.2, change-scoped | `data/raw/lint/`, [`docs/static_analysis.md`](docs/static_analysis.md) | done; **0** issues on this corpus |
| LLM prompts + runner | `prompts/`, `src/oba_revieweval/models/` | 3-PR engineering path ready; full corpus not scored |
| Overlap metrics | `scripts/score_findings.py`, `results/` | not produced |

Zero lint findings is a real baseline (`govet` + `staticcheck` SA\* on already-merged diffs). Those checkers do not target the domain / concurrency / API-contract issues that dominate the gold set. A synthetic `fmt.Printf` fixture still trips the same binary.

Author (`tejasva-vardhan`) review comments are never gold. Author-authored PRs stay in the corpus only if another human reviewed them.

## Pipeline

```
GitHub Maglev PRs
        │  scripts/export_corpus.py  (GITHUB_TOKEN)
        ▼
 data/raw/prs/     ──►  annotate  ──►  data/human_review.csv
        │
        ├── scripts/run_linter.py      → lint JSON per merge SHA
        └── scripts/run_models.py      → LLM findings (needs OPENAI_API_KEY)
                    │
                    ▼
          scripts/score_findings.py    → results/  (not run yet)
```

Library code lives in `src/oba_revieweval/`: `dataset/` (GitHub + git anchors), `annotation/`, `lint/`, `models/`, `evaluation/`.

## Layout

```
protocol.md  research_questions.md  literature.md
data/          corpus, labels, lint manifests
prompts/       versioned review prompt
scripts/       export, validate, lint, models, score
src/oba_revieweval/
tests/
docs/          annotation, data collection, static analysis, LLM pilot
results/       empty until scoring runs
```

## Setup

Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

`.env` is only required for the LLM phase (`OPENAI_API_KEY`). Copy from `.env.example`. Do not commit it.

Reproduce the exported corpus (optional):

```bash
# clone Maglev to data/raw/cache/maglev (gitignored)
python scripts/export_corpus.py
python scripts/validate_corpus.py
python scripts/install_golangci_lint.py
python scripts/run_linter.py
# do not run scripts/run_models.py until you intend to call a model
```

## Ethics

Public GitHub review data only. Store logins for author-vs-reviewer exclusion, not emails. Ignore bot comments. Do not put human review text into the model prompt.

## License

MIT. Maglev itself stays under its own license; this repo does not vendor the Maglev tree.
