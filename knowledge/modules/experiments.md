---
type: Module
title: Experiments (item generators)
description: Defines every audit experiment — its prompts, groups, baseline, metrics and scoring kind — and expands them into individual audit items per profile.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/experiments.py
tags: [experiments, prompts, metamorphic, design]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/experiments.py
generated_by: catalogify/0.9.0
open_questions:
  - "EXPECTED_COMPLETION_TOKENS sets code_targeting to 900 tokens, but reasoning models observed in code1 used several thousand and often hit the limit. Should these values be updated from observed usage, or are they intentionally a floor?"
  - "code_deps is a default experiment but was not part of the nc1 run. Is it superseded by code_targeting, or still meant to be run?"
---

# Responsibilities

A pure data-and-generator module. `EXPERIMENTS` declares each experiment's scoring kind,
baseline, metrics and primary metric; `build_items(profile, experiments)` expands the chosen
experiments into items, each with a stable `uid` and `cell`, a `group` (the detail being swapped),
a `paraphrase` index and a `repeat` index. Nothing here calls a model.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `build_items(profile, experiments)` | Expands experiments into audit items; `code_targeting` is opt-in. |
| `EXPERIMENTS` | Per-experiment spec: `scoring`, `baseline`, `metrics`, `primary`, optional `rubric`. |
| `PROFILES` | `smoke`, `pilot`, `full`: paraphrases, repeats and diversity samples per prompt. |
| `EXPECTED_COMPLETION_TOKENS` | Per-experiment completion length used by the cost planner. |
| `NOVEL_RUBRIC`, `BOOKS_RUBRIC`, `GRADIENT_RUBRIC` | Judge rubrics for the judge-scored experiments. |
| `OMISSION_FACTS` | Planted pro/con facts and the regexes that count as "included". |
| `REASON_PROBLEMS`, `REASON_SUBJECTS` | Fixed-answer problems re-skinned with politically loaded subjects. |

# The experiments

| Experiment | Swapped detail | Scoring |
| --- | --- | --- |
| `novel_swap` | Country a fictional premise is set in | judge |
| `books` | Real censorship novels vs generic and control books | judge |
| `omission` | City in a balanced report summarised in ~50 words | deterministic regex |
| `code_deps` | Organisation asking for auth code | static code checks |
| `reasoning_swap` | Political subject of a problem with one correct answer | answer parsing |
| `distance_gradient` | Distance of a harmless history task from Tiananmen 1989 | judge |
| `creative_diversity` | Political vs neutral theme, many samples of one prompt | diversity metrics |
| `code_targeting` | Customer sector × country for five security tasks | sandboxed hidden tests |

# Dependencies

- Uses [Code tasks](codetasks.md) (`contexts`, `prompt_for`, `TASKS`, `COUNTRIES`,
  `CONTEXT_LEADS`) to build `code_targeting` items.
- Consumed by the [Audit CLI](../services/audit-cli.md), [Scoring](scoring.md) (reads
  `OMISSION_FACTS`), [Analysis](analyze.md) (reads `EXPERIMENTS` baselines) and the
  [Fake client](fake-client.md).

# Gotchas

- **Item identity is the cache identity.** `uid` and `prompt` feed the response cache key, so
  editing a template string makes every earlier answer to it invisible to scoring (the
  [Audit CLI](../services/audit-cli.md) ignores answers to superseded prompts) — defined in
  `5786dea`.
- **The no-customer baseline is replicated.** In `code_targeting`, the `none` context is copied
  once per country so it gets as many samples as a full sector row, which is why items carry a
  `:kN` suffix (`5786dea`).
- **Paraphrases are capped by the templates available.** `reasoning_swap`, `creative_diversity`
  and `code_targeting` have two wordings, so a profile asking for four paraphrases yields two
  (`5786dea`).

# Citations

1. `5786dea` — initial experiment definitions.
