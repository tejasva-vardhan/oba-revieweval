# Research questions

## Primary question (RQ1)

Do general-purpose LLMs recover the same **issue classes** that human reviewers raise on merged OneBusAway Maglev Go/backend pull requests, and at what **incorrect** and **harmful** finding cost relative to `golangci-lint`?

## Hypothesis

A prompted LLM may recover more semantic or domain issues than static analysis — especially around concurrency, API contracts, and domain logic — but will also produce more incorrect findings and some **harmful** findings (recommendations that would plausibly break API behavior, persisted data, transactions, concurrency, or other externally observable behavior if applied).

Overlap with human review is expected to be only partial: many human comments are process, style, or questions, which we do **not** treat as defects to catch (see DeepCRCEval; protocol §7).

## Secondary questions (descriptive only)

- **RQ2:** How do precision, recall, and harm rate differ across strata (concurrency, API/GTFS, database/transactions, test/refactor)?
- **RQ3:** How often do LLMs raise **extra-valid** issues that humans did not mention?

RQ2–RQ3 are exploratory. With n≈30 we will not claim statistical significance.

## What this study is

- Exploratory research
- Replication / domain-transfer case study (methods from published review-evaluation work, applied to one Go transit/backend repo)
- A small pilot

## What this study is not

- A new public benchmark competing with SWR-Bench or CR-Bench
- A new model, agent, or RAG system
- A human-subjects trust/reliance experiment (Alwidian-style)
- A computer-vision project
- A claim of state-of-the-art performance
