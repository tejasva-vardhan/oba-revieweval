# OBA-ReviewEval

Student study: when humans review merged pull requests on [OneBusAway/maglev](https://github.com/OneBusAway/maglev) (a Go transit backend), do a static analyzer and a language model raise the same defect and design issues?

This is a pilot case study, not a published paper and not a new benchmark. Do not cite precision or recall numbers from this repository. None exist yet.

## What is in the study

- **Humans:** review comments on merged Maglev pull requests.
- **Static analysis:** pinned `golangci-lint` 2.13.2 run on the merge commit.
- **Language model:** same pull requests, scored later. That run is not finished.

See [research_questions.md](research_questions.md) and the frozen [protocol.md](protocol.md).

## How the study is built

**RQ1:** Do prompted LLMs recover the same defect/design issue classes that human reviewers raised on merged Maglev PRs, and at what incorrect / harmful cost relative to `golangci-lint`?

Corpus: public merged Maglev PRs with a human (non-bot) review comment that is not by this repo’s author. Diffs, review threads, and issue comments sit under `data/raw/prs/` (33 PRs).

Human labels (`data/human_review.csv`): each review comment is split into atomic findings and tagged (defect, design, process, question, …). **Gold** = findings with `in_reference_set=true` (75 defect/design). Process chatter is not treated as something a linter or model must catch.

Static analysis: pinned `golangci-lint` **2.13.2**, `govet` + `staticcheck` SA\*, **change-scoped** to the PR diff (`docs/static_analysis.md`). On this corpus that run produced **0** change-scoped findings. That is a measured baseline (the same binary flags a synthetic `fmt.Printf` bug in tests). It is not “266 lint issues” — 266 is the count of human atomic findings.

LLM path: prompts in `prompts/`, runner in `src/oba_revieweval/models/`. A 3-PR engineering check exists. Full-corpus scoring is not finished; `results/` has no metrics. Do not quote precision or recall from this repo.

## Status

| Artifact | Status |
|---|---|
| Protocol | Frozen for the pilot (2026-09-13) |
| Corpus | 33 merged pull requests exported under `data/raw/prs/` |
| Human labels | Frozen 2026-09-14. Gold set = 75 defect/design findings. See `docs/human_annotation.md` |
| Static-analysis baseline | Done. See `docs/static_analysis.md` |
| Language-model scoring | Pipeline ready for a 3-pull-request engineering check. Live scoring needs `OPENAI_API_KEY` and is not finished |
| Report | Not written |

Headline counts: **33** merged pull requests, **198** human comments, **266** atomic findings, **75** gold defect/design findings.

## Why Maglev

Maglev is a Go rewrite of the OneBusAway REST API (GTFS import, SQLite, HTTP handlers). The author of this study is a Maglev contributor. That helps with data access and annotation. It is not a novelty claim.

The author's own review comments are never used as independent gold. Author-authored pull requests enter the gold set only if another human left review comments that can be labeled.

## Repository layout

```
protocol.md                 Frozen method
research_questions.md
literature.md
data/                       Corpus metadata and labels (no secrets)
prompts/                    Versioned model prompts
scripts/                    Export, lint, score
src/oba_revieweval/         Library code
tests/
results/                    Generated tables (empty until experiments run)
report/                     Technical report (later)
docs/
```

## Setup

Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Copy `.env.example` to `.env` only when you are ready to call a model API. Do not commit `.env`.

## Reproduce the raw corpus

1. Read `docs/data_collection.md`.
2. Clone Maglev to `data/raw/cache/maglev` (gitignored) if it is not already there.
3. `python scripts/export_corpus.py` (uses `GITHUB_TOKEN` when set).
4. `python scripts/validate_corpus.py`.
5. Replay the static-analysis baseline with `python scripts/install_golangci_lint.py` then `python scripts/run_linter.py`.
6. Do not run `scripts/run_models.py` until the language-model phase.

## Ethics

Use only public GitHub pull-request data. Store logins needed for exclusion rules (author vs reviewer), not emails. Do not treat bot comments as human review. Do not put human review comments into the model prompt.

## License

MIT. OneBusAway/maglev source remains under its own license; this repository stores study artifacts, not a Maglev fork.

## Citation

Unpublished student technical report. Cite the repository URL and date, not as a peer-reviewed paper.
