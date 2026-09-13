# Method decisions (scaffold)

- **Corpus = Maglev, not go-gtfs.** go-gtfs has only four merged PRs and no review-comment volume in search. Maglev is the production Go API the author actually contributed to.
- **Gold comments exclude the study author.** Comment-API check on 2026-09-13: most author PRs lack independent humans. Only `#507` and `#702` enter the candidate 30 from that set.
- **No GitHub token in the environment.** Unauthenticated search cannot page all 453 Maglev PRs with comments. The 30 is a documented sample. Phase 4 should use a personal access token (public `repo` read is enough for public data) to verify reviews and export diffs.
- **No model calls in this commit.** Calling APIs without a user-supplied key would be fake science.
- **Concurrency stratum is short.** Do not drag `#457` into gold without an independent reviewer. Search more race/lock PRs in Phase 4.

## Phase 4 (2026-09-14)

- Stayed on `OneBusAway/maglev`. Did not switch to `onebusaway-application-modules`.
- Did not rewrite `protocol.md` or `pr_candidates.csv`.
- `#457` has independent review bodies; recorded as an additional accept, not forced into the frozen 30.
- Recommended **n = 33** rather than inventing n = 30.
- Concurrency recommended count is 8 versus the protocol target of 4–6 because those PRs met the gold rule. Eligible PRs were not dropped to hit the target.
- No LLM or linter runs.
