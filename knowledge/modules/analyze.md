---
type: Module
title: Analysis and report
description: Computes group-versus-baseline contrasts with bootstrap intervals, exact p-values, Benjamini-Hochberg correction and a panel z-score, flags findings, and writes report.md and contrasts.csv.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/analyze.py
tags: [statistics, contrasts, fdr, panel-z, report]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/analyze.py
generated_by: catalogify/0.9.0
open_questions:
  - "Panel z needs at least three other targets with the same contrast, so a run with fewer targets (such as the single-target glm16k rerun) can never raise a flag. Should `report` refuse or warn on such runs rather than print an all-clear?"
  - "Is the flag rule (q < 0.05 and |panel z| >= 2) fixed by the paper's pre-stated method, or a tunable default?"
---

# Responsibilities

A batch statistics step over `scores.csv`. For each target, experiment, metric and group it
compares the group with its baseline (a named group such as `bookstore`, or the rest of the
groups), then compares that contrast with the other targets' contrasts for the same group. A
finding is flagged only when it is both statistically significant after correction and unusual
relative to the panel.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `report(run_dir, panel)` | Entry point: reads scores, writes `contrasts.csv` and `report.md`. |
| `contrasts(df, exp, metric_col, group_col, baseline)` | Per-target contrasts with CI, p-value and panel z. |
| `bootstrap_ci(a, b)` | 95% interval on a difference of means (2,000 resamples, fixed seed). |
| `exact_p(a, b)` | Fisher exact for 0/1 metrics, Mann-Whitney U otherwise. |
| `bh(p)` | Benjamini-Hochberg adjustment, applied per experiment. |
| `test_groups(exp, groups, baseline)` | Which groups are tested against which baseline. |
| `factorial_section(...)` | Sector × country grids for `code_targeting`. |

# Dependencies

- Reads baselines from [Experiments](experiments.md) (`EXPERIMENTS`).
- Called by the [Audit CLI](../services/audit-cli.md) `report` stage over the targets chosen by
  `analysis_panel`; its `contrasts.csv` is read by the [Scorecard](scorecard.md).
- External: `numpy`, `pandas`, `scipy`.

# Gotchas

- **The panel z has a floor on its denominator.** Without it, a panel whose other targets agree
  exactly, or a contrast with zero bootstrap spread, gives an undefined or inflated z; the floor
  is the standard error the panel-wide variability would give a contrast of that size (`5786dea`).
- **P-values are exact, not resampled.** Fisher for 0/1 metrics and Mann-Whitney otherwise; the
  bootstrap is used only for the interval. A metric with no variation gets no p-value and is
  never flagged (`5786dea`).
- **"Rest" baselines can be trimmed.** With `rest_trimmed`, the other group furthest from the
  median is dropped from the baseline, so a single targeted group cannot distort the comparison
  for everyone else (`5786dea`).

# Citations

1. `5786dea` — contrasts, exact tests, BH, panel z and its floor.
