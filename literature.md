# Literature notes

Paraphrased for study design. Read the originals; do not copy prose. This is not a claim that OBA-ReviewEval is novel.

**Search window:** 2026-09-13. Sources: arXiv, ACL Anthology, ACM DL landing pages, IEEE/TSE and JSS records, Semantic Scholar / Google Scholar via public abstracts, and GitHub repos named in those papers. Full-text PDFs were not copied into this repository.

## What this pilot can add

Published work already evaluates LLM and neural code review at scale (CodeReviewer, SWR-Bench, CR-Bench, CRScore, DeepCRCEval) and even **Go-specific** LLM review ([arXiv 2606.01859](https://arxiv.org/abs/2606.01859)). Language bias and trust/reliance are also occupied.

A 30-PR Maglev study **cannot** add a new benchmark or a general performance ranking.

It **can** add a **documented, change-scoped comparison** of prompted LLMs vs `golangci-lint` vs **typed** human comments on one production Go transit/backend server, with a strict **harm** label and an explicit ban on using the student author’s comments as gold. That is methodology and a case study, not a new task.

---

## CodeReviewer

- **Citation:** Li, Z., Lu, S., Guo, D., Duan, N., et al. Automating Code Review Activities by Large-Scale Pre-training. *arXiv:2203.09095*, 2022. Also associated with ESEC/FSE-era CodeReviewer releases.
- **URL:** https://arxiv.org/abs/2203.09095
- **Code:** https://github.com/microsoft/CodeBERT/tree/master/CodeReviewer
- **Question:** Can a diff-aware pretrained model support review quality estimation, comment generation, and refinement?
- **Data:** Large multilingual GitHub review corpus.
- **Method:** Encoder–decoder pretraining on diffs and comments; three downstream tasks.
- **Metrics:** Task-specific (classification / generation), including text overlap in the original generation setup.
- **Finding:** Specialized pretraining beat prior pretrained code models on their benchmark.
- **Limit:** Generation quality was later shown to be poorly measured by n-gram overlap (see DeepCRCEval, CRScore).
- **Relevance:** Foundational citation. We do **not** retrain CodeReviewer.

## CRScore

- **Citation:** CRScore: Grounding Automated Evaluation of Code Review Comments in Code Claims and Smells. *NAACL 2025*.
- **URL:** https://aclanthology.org/2025.naacl-long.457/
- **Question:** How can review-comment quality be scored when many comments are valid for one diff?
- **Data:** Human quality scores (reported ~2.9k) plus model/GitHub comments.
- **Method:** Reference-free scores grounded in claims and static smells; compared to LLM-as-judge.
- **Metrics:** Correlation with human quality (Spearman / Kendall reported in the paper).
- **Finding:** Review evaluation is one-to-many; their metric aligned better with humans than open n-gram metrics.
- **Limit:** Still an automated proxy, not a substitute for issue-level human labels on a small corpus.
- **Relevance:** We will **not** use BLEU as a primary metric.

## DeepCRCEval

- **Citation:** Lu, J., et al. DeepCRCEval: Revisiting the Evaluation of Code Review Comment Generation. *arXiv:2412.18291*, 2024.
- **URL:** https://arxiv.org/abs/2412.18291
- **Question:** Are OSS “gold” comments and BLEU/ROUGE adequate for review-generation research?
- **Data:** Comments from CodeReviewer / Tufano-style benchmarks; human and LLM judges.
- **Method:** Quality/category/tone/context analysis; DeepCRCEval scoring; LLM-Reviewer few-shot baseline.
- **Finding:** They report that **under 10%** of examined benchmark comments were high quality as automation targets; n-gram metrics mislead; a simple prompted LLM baseline can outperform older generators under their criteria.
- **Limit:** Judge models can be biased; criteria are still partly subjective.
- **Relevance:** Direct reason we type human comments and drop style/process/questions from the reference set.

## SWR-Bench

- **Citation:** SWR-Bench: Assessing LLM Performance in Real-World Code Review Comment Generation. *arXiv:2509.01494*, 2025.
- **URL:** https://arxiv.org/abs/2509.01494
- **Question:** How well do ACR tools and LLMs cover real PR issues with full project context?
- **Data:** 1,000 manually verified GitHub PRs (change vs clean).
- **Method:** Structured ground truth; LLM coverage judge (authors report ~90% agreement with humans in their setup).
- **Metrics:** Precision / recall / F1 on issue coverage.
- **Finding:** Current systems underperform; aggregation can raise F1 substantially in their experiment.
- **Limit:** Large annotation budget; LLM judge still in the loop.
- **Relevance:** We copy **issue coverage**, not their scale. We do not claim to replace this bench.

## CR-Bench

- **Citation:** CR-Bench: Evaluating the Real-World Utility of AI Code Review Agents. *arXiv:2603.11078*, 2026.
- **URL:** https://arxiv.org/abs/2603.11078
- **Question:** Do review agents find real defects and are extra comments useful?
- **Data:** Defects derived from SWE-Bench-style failures (authors describe verified and larger splits).
- **Method:** Agents vs single-shot LLM; evaluator for precision/recall plus usefulness and signal-to-noise.
- **Finding:** Distinguishes catching a known defect from drowning the developer in noise.
- **Relevance:** We adopt **useful vs noise / harm** thinking. We do not build an agent.

## Industry / open review benches (2026)

- Martian / ritsukai Code Review Bench: https://github.com/ritsukai/code-review-benchmark — offline golden comments plus online “did the developer fix it?” precision/recall.
- CloudAEye 2026 tool comparison (50 PRs, golden comments, LLM matching).
- **Relevance:** Same evaluation skeleton (golden issues, semantic match). Our n is similar to the **offline 50-PR** style, not to 500k-PR telemetry. Not a reason to claim a new bench.

## Go-specific LLM review

- **Citation:** Improving LLM-Based Go Code Review through Issue-List Generation and Context Augmentation. *arXiv:2606.01859*, 2026.
- **URL:** https://arxiv.org/abs/2606.01859
- **Question:** Do issue lists and extra context improve LLM Go review as measured by downstream refinement?
- **Metrics:** RefineEM (comment induces an exact match to the human revision), vs CodeReviewer.
- **Finding:** Context and multi-issue listing help; human comments remain a ceiling.
- **Limit:** RefineEM requires a later human patch; many Maglev comments do not map to a single exact hunk rewrite.
- **Relevance:** **Go LLM review is already published.** Our increment is Maglev + lint baseline + typed human comments + harm, not “first Go LLM review.”

## Earlier review-generation baselines

- **Citation:** Tufano, R., Dabić, O., Mastropaolo, A., Ciniselli, M., and Bavota, G. Code Review Automation: Strengths and Weaknesses of the State of the Art. *IEEE Transactions on Software Engineering*, 50(2):338–353, 2024. Preprint: https://arxiv.org/abs/2401.05136
- **Question:** Where do specialized review-comment and code-refinement models succeed or fail?
- **Finding:** Method-level generators often succeed on trivial edits and fail on semantically hard comments; BLEU-style scores hide that gap.
- **Relevance:** Historical baseline. We do not retrain these models.

- **Citation:** Tufano, R., Martin-Lopez, A., Tayeb, A., Dabić, O., Haiduc, S., and Bavota, G. Deep Learning-based Code Reviews: A Paradigm Shift or a Double-Edged Sword? *ICSE 2025*. Preprint: https://arxiv.org/abs/2411.11401
- **Question:** Does starting from an LLM review help humans find more serious defects?
- **Finding:** Reviewers accepted a large share of ChatGPT-flagged issues, but the treatment did not increase high-severity issue detection and appeared to anchor attention on the highlighted locations. Time was spent checking the automated comments.
- **Relevance:** This is a **human-subjects** result. We only measure comment correctness. We must not claim a trust or productivity finding.

## Industry LLM review (style/best-practice, includes Go)

- **Citation:** Vijayvergiya, M., Salawa, M., Budiselić, I., et al. AI-Assisted Assessment of Coding Practices in Modern Code Review. *AIware 2024*. https://doi.org/10.1145/3664646.3665664 Preprint: https://arxiv.org/abs/2405.13565
- **Question:** Can an LLM enforce coding best practices at industrial scale for C++, Java, Python, and **Go**?
- **Finding:** AutoCommenter was deployed at Google; a non-trivial fraction of comments were resolved in later snapshots. The system targets style-guide practices, not Maglev-style GTFS/API defects. Authors distinguish LLM comments from what existing linters already catch.
- **Relevance:** Shows LLM review of **Go** is not new. Our increment is typed human gold + lint + harm on one OSS transit API, not best-practice enforcement.

## Hallucinations and industrial false positives

- **Citation:** Liu, C., Lin, H. Y., and Thongtanunam, P. Hallucinations in Code Change to Natural Language Generation. *IJCNLP-AACL 2025*. https://aclanthology.org/2025.ijcnlp-long.137/ Preprint: https://arxiv.org/abs/2508.08661
- **Finding:** On their CodeChange2NL sample, about half of generated **review comments** contained hallucinations (input inconsistency, logic inconsistency, or intention violation). Single automatic metrics were weak detectors.
- **Relevance:** Justifies a human **incorrect** label and a refusal to use BLEU as primary evaluation.

- **Citation:** BitsAI-CR: Automated Code Review via LLM in Practice. *arXiv:2501.15134*, 2025. https://arxiv.org/abs/2501.15134
- **Finding:** Even fine-tuned industrial review models needed a filter stage; raw precision in their ablation was far below production targets because of hallucinated style and “magic number” nits.
- **Relevance:** Supports reporting **incorrect rate** separately from recall.

## Go linters on real issues

- **Citation:** Wu, J., and Clause, J. An empirical assessment of go linters on real-world issues. *Journal of Systems and Software*, 236:112797, 2026. https://doi.org/10.1016/j.jss.2026.112797
- **Question:** How well do popular Go linters (including `govet` / `staticcheck` class tools) detect and explain real industrial issues?
- **Finding:** Linters often missed the issues under study and, when they fired, did not reliably guide a correct fix.
- **Relevance:** Lint is a **necessary but incomplete** baseline. If an LLM only repeats `staticcheck`, it is not adding review value; if lint already misses domain bugs, that is expected, not a novelty claim.

## Trust and reliance (not our experiment)

- Alami, A., et al. Human and Machine: How Software Engineers Perceive and Engage with AI-Assisted Code Reviews Compared to Their Peers. *arXiv:2501.02092*, 2025. https://arxiv.org/abs/2501.02092
- Rethinking Code Review Workflows with LLM Assistance (WirelessCar field study). *arXiv:2505.16339*, 2025. https://arxiv.org/abs/2505.16339
- Later 2026 studies of agent-generated review resolution (e.g. large GitHub agent-comment corpora).

These need participants or production telemetry. **We measure comment correctness, which trust studies presuppose.** We will not claim a trust result.

## Language bias (why we are not doing alternative B)

- Twist, A., et al. LLMs Love Python. 2025. https://arxiv.org/html/2503.17181v1
- Multi-SWE-bench / SWE-bench Multilingual (2025).

Occupied at a larger scale than we can run.

## Static analysis on Go

- `golangci-lint` aggregates `govet`, `staticcheck`, and others; it is a **precision-oriented** CI baseline, not a semantic reviewer.
- GCatch / GoBench study concurrency bugs in large Go systems; we do not reimplement GCatch in the pilot.

**Relevance:** Lint is the honest cheap baseline. If an LLM only repeats `staticcheck`, it is not adding review value.

## Requirements / Graph-RAG (out of scope)

User-story NFR extraction (IEEE Access 2025 and related) and GraphRAG/CodeRAG papers are real but would clone other Mitacs listings or become a tutorial. Not this repo.
