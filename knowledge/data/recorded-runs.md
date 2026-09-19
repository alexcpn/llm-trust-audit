---
type: Data Model
title: Recorded runs
description: The five committed run directories — code1, nc1, glm16k, smoke1 and fake — what each measured, how it was produced, and which published numbers come from it.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/runs/glm16k/PREREG.md
tags: [runs, data, pilot, replication, pre-registration]
timestamp: 2026-09-19T07:38:00+05:30
source_files:
  - pilot/runs/code1/run.json
  - pilot/runs/nc1/run.json
  - pilot/runs/glm16k/run.json
  - pilot/runs/glm16k/PREREG.md
  - pilot/runs/smoke1/run.json
  - pilot/runs/fake/run.json
generated_by: catalogify/0.9.0
open_questions:
  - "code1 and nc1 do not record the --max-tokens they were collected at in run.json; the 8,000-token figure for code1 is known from the paper and the GLM cut-offs. Should run.json record every collection flag so a run is self-describing?"
---

# Runs

| Run | Profile | Experiments | Responses | What it is |
| --- | --- | --- | ---: | --- |
| `code1` | pilot | `code_targeting` | 7,030 lines (6,860 current) | The code study: seven endpoints × 980 requests, five tasks, 49 customer contexts, 8,000-token limit. |
| `nc1` | pilot | `novel_swap`, `books`, `omission`, `reasoning_swap`, `distance_gradient`, `creative_diversity` | 5,217 | The topic study across ten endpoints, with three judges. |
| `glm16k` | pilot | `code_targeting`, `tls_client` only | 196 | Pre-registered rerun of GLM 5.3 Flash on the TLS task at a 24,000-token limit. |
| `smoke1` | smoke | defaults | 66 | Cheapest real check of the harness, two targets. |
| `fake` | pilot | defaults | 3,120 | Offline run against five planted-bias fake models; validates that the pipeline flags what it should. |

Each directory follows the [run directory layout](run-directory.md).

# The glm16k rerun

In `code1`, GLM 5.3 Flash (pinned to Z.AI) was cut off at the token limit on 90 of 196 TLS
requests, and an exploratory look showed the cut-offs clustered by customer. `PREREG.md` fixed
three hypotheses (budget artifact, real differential completion, effort scaling), a numeric
decision rule and the exact commands **before** collection. The run sent the same 196 prompts,
seed and host with only the limit raised. `analysis.py` and `analysis_8k_logit.py` in the same
directory regenerate every number reported from it.

# Dependencies

- Produced by the [Audit CLI](../services/audit-cli.md) with targets from the
  [panel configuration](../operations/panel-config.md); `fake` used the
  [Fake client](../modules/fake-client.md).
- Read by the [Scorecard](../modules/scorecard.md) (`nc1`, `code1`, `glm16k`) and reported in
  [Publications](../references/publications.md).

# Gotchas

- **Never write into a published run.** `code1` and `nc1` back every number in the paper and
  README; follow-up experiments go into a new directory, which is why the budget rerun is
  `glm16k` and not an extension of `code1` (`5256d71`).
- **The rerun's name is historical.** `glm16k` was collected at 24,000 tokens, not 16,000; the
  budget of record is the one in its `PREREG.md` (`5256d71`).
- **Pre-registration is part of the data.** `PREREG.md` was written before any request was sent
  and is not edited afterwards; its decision rule, not a later one, decides the verdict
  (`5256d71`).

# Citations

1. `5256d71` — the pre-registered glm16k rerun and its analysis scripts.
