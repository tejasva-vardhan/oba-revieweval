# OBA-ReviewEval

Exploratory evaluation of **LLM findings vs `golangci-lint` vs human review** on production Go pull requests from [OneBusAway/maglev](https://github.com/OneBusAway/maglev).

This is a **pilot / domain-transfer case study**, not a new benchmark and not a claim of state-of-the-art performance.

## Research question

Do general-purpose LLMs recover the same issue classes that human reviewers raise on merged OneBusAway Go/backend pull requests, and at what false-positive and harmful-finding cost relative to static analysis?

See [research_questions.md](research_questions.md) and the frozen [protocol.md](protocol.md).

## Status

| Artifact | Status |
|---|---|
| Protocol | Frozen for the pilot (2026-09-13). Not amended. |
| Literature notes | Started |
| 30-PR candidate list | Frozen discovery list preserved |
| Phase 4 verification | Complete (2026-09-14). See `docs/data_collection.md` |
| Raw corpus export | Complete: all 33 recommended PRs in `data/raw/prs/` |
| Human labels | Phase 5 table written 2026-09-14. Two findings remain ambiguous; see `docs/human_annotation.md`. Not a tool-score freeze. |
| LLM or linter runs | Not started |
| Report | Not written |

Do not cite precision/recall numbers from this repository. None exist yet.

**Phase 4 headline:** 30 original candidates checked; **26** eligible for primary gold; **4** excluded; recommended corpus **n = 33** if the 7 additional concurrency PRs with independent human review are included. The study should say `n = 33` (or `n = 26` if extras are held out), not pretend `n = 30`.

## Why this corpus

Maglev is a Go rewrite of the OneBusAway REST API (GTFS import, SQLite queries, HTTP handlers, real-time vs schedule behavior). The author of this study is a Maglev contributor. That is a **data-access and annotation** advantage, not a novelty claim.

**Ground-truth rule:** the author's own review comments are never independent gold. Author-authored PRs enter the primary set only if another human left review or issue comments that can be labeled. Phase 4 confirmed independent humans on `#507` and `#702` via `/pulls/{n}/reviews`. `#457` also has independent review bodies; it was **not** silently inserted into the frozen 30 and is listed as an additional accept.

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
docs/                       Annotation schema and Mitacs evidence notes
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

Copy `.env.example` to `.env` only when you are ready to call a model API. **Do not commit `.env`.**

## Reproduce the raw corpus

1. Read `docs/data_collection.md`.
2. Clone Maglev to `data/raw/cache/maglev` (gitignored) if it is not already there.
3. `python scripts/export_corpus.py` (uses `GITHUB_TOKEN` when set; otherwise the local cache plus public PR diffs).
4. `python scripts/validate_corpus.py` — this fails if any of the 33 recommended exports is incomplete.
5. Inspect `data/raw/prs/<number>/`, `data/raw/manifest.csv`, and unlabeled partitions in `data/extracted/prs/<number>/`.
6. Do **not** run `scripts/run_linter.py` or `scripts/run_models.py` until later phases.

`pytest` checks schemas, eligibility, bot/author rules, merge-SHA diffs, and complete-corpus validation.

## Ethics and privacy

Use only public GitHub pull-request data. Store logins needed for exclusion rules (author vs reviewer), not emails or other profile fields. Do not treat bot comments (for example CodeRabbit) as human review. Do not feed human review comments into the model prompt.

## License

MIT. OneBusAway/maglev source remains under its own license; this repo stores study artifacts, not a Maglev fork.

## Citation

Unpublished student technical report. Cite the repository URL and date, not as a peer-reviewed paper.
