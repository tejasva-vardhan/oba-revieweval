# OBA-ReviewEval

Exploratory evaluation of **LLM findings vs `golangci-lint` vs human review** on production Go pull requests from [OneBusAway/maglev](https://github.com/OneBusAway/maglev).

This is a **pilot / domain-transfer case study**, not a new benchmark and not a claim of state-of-the-art performance.

## Research question

Do general-purpose LLMs recover the same issue classes that human reviewers raise on merged OneBusAway Go/backend pull requests, and at what false-positive and harmful-finding cost relative to static analysis?

See [research_questions.md](research_questions.md) and the frozen [protocol.md](protocol.md).

## Status

| Artifact | Status |
|---|---|
| Protocol | Frozen for the pilot (2026-09-13) |
| Literature notes | Started |
| 30-PR candidate list | Identified; human-vs-bot review not fully verified (no GitHub token) |
| Diffs / labels / metrics | Not collected |
| LLM or linter runs | Not started |
| Report | Not written |

Do not cite numbers from this repository until `results/` contains generated tables.

## Why this corpus

Maglev is a Go rewrite of the OneBusAway REST API (GTFS import, SQLite queries, HTTP handlers, real-time vs schedule behavior). The author of this study is a Maglev contributor. That is a **data-access and annotation** advantage, not a novelty claim.

**Ground-truth rule:** the author's own review comments are never independent gold. Author-authored PRs enter the primary set only if another human left review or issue comments that can be labeled. GitHub issue-comment checks on 2026-09-13 found independent humans on `#507` and `#702` only. Other author PRs stay out of the gold set unless Phase 4 finds review submissions that the unauthenticated comment APIs missed.

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

## Reproduce one PR (after export exists)

1. Confirm `data/candidates.md` lists the PR and that human comments are non-bot.
2. `python scripts/export_prs.py --pr 702` (export is not implemented until Phase 4).
3. `python scripts/run_linter.py --pr 702` (requires a local Maglev checkout; not run in this scaffold).
4. `python scripts/run_models.py --pr 702` (requires API credentials; stop rather than invent keys).
5. `python scripts/score_findings.py` then `python scripts/generate_tables.py`.

Until those scripts are implemented, `pytest` only checks schemas and scoring functions.

## Ethics and privacy

Use only public GitHub pull-request data. Store logins needed for exclusion rules (author vs reviewer), not emails or other profile fields. Do not treat bot comments (for example CodeRabbit) as human review. Do not feed human review comments into the model prompt.

## License

MIT. OneBusAway/maglev source remains under its own license; this repo stores study artifacts, not a Maglev fork.

## Citation

Unpublished student technical report. Cite the repository URL and date, not as a peer-reviewed paper.
