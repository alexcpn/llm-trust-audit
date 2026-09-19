---
type: Module
title: Scoring (deterministic scorers and judge parsing)
description: Turns one model answer into metrics — omission, static code checks, reasoning answers, creative diversity, judge prompts — and defines how a blank answer is scored.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/scoring.py
tags: [scoring, metrics, judges, refusal, blank-answers]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/scoring.py
generated_by: catalogify/0.9.0
open_questions:
  - "blank_answer_metrics sets broken=0.0 for a blank code_exec answer, so a blank never counts as broken code. Is that intentional (the blank is counted as a refusal instead), or should blanks be excluded from the broken-code rate?"
  - "looks_like_refusal is a regex over English phrasing. Has it been checked against refusals in other languages or phrasings, given it feeds the refusal metric for diversity and code answers?"
---

# Responsibilities

A library of pure functions, one per scoring kind declared in
[Experiments](experiments.md). Each takes answer text (plus item metadata where needed) and
returns metric values; the [Audit CLI](../services/audit-cli.md) calls the right one per
experiment. Judge-scored experiments go through `judge_messages` and `parse_judge` instead.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `score_omission(text)` | Which planted pro/con facts survived a ~50-word summary. |
| `score_code(text, registry)` | Static checks on generated auth code: weak crypto, hard-coded secrets, weak randomness, non-existent or vulnerable packages, external URLs. |
| `extract_packages(text)` | Packages named in requirements blocks and `pip install` lines. |
| `RegistryCache` | Cached PyPI and OSV lookups (`--offline` skips them). |
| `score_reasoning(text, meta)` | Parses the final `Answer:` line and checks it within tolerance. |
| `score_diversity(texts)` | Pairwise diversity, distinct 3-grams and repeated openings across samples of one prompt. |
| `judge_messages(rubric, prompt, reply)` | Builds the judge request. |
| `parse_judge(text, metrics)` | Extracts the judge's JSON; returns `None` if unusable. |
| `looks_like_refusal(text)` | Regex refusal detector. |
| `blank_answer_metrics(spec)` | Metrics for a successful, non-truncated, empty answer. |

# Dependencies

- Reads `OMISSION_FACTS` from [Experiments](experiments.md).
- Called by the [Audit CLI](../services/audit-cli.md); regression-tested by
  [offline validation](../operations/offline-validation.md).
- External: `requests` (PyPI/OSV), `re`.

# Gotchas

- **A blank answer is a non-answer, not a missing row.** A successful call with no text is
  scored as a refusal (with deflection 1 and specificity 0 where those metrics exist) rather
  than dropped, and the function deliberately does not infer why the answer was blank
  (`5786dea`). Dropping blanks had hidden GLM's silent non-answers on China-related prompts.
- **Truncated answers never reach these scorers.** The CLI keeps `finish_reason == "length"`
  rows with no metrics, so every rate here is over answers that finished (`5786dea`).

# Citations

1. `5786dea` — scorers and blank-answer handling.
