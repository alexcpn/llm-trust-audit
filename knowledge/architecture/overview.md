---
type: Reference
title: LLM Trust Audit — architecture overview
description: Start here — a black-box behavioural audit harness for LLM endpoints on OpenRouter, the pilot runs it produced, and the paper and essays built on them.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/README.md
tags: [overview, architecture, audit, llm]
timestamp: 2026-09-19T07:38:00+05:30
source_files:
  - README.md
  - pilot/README.md
generated_by: catalogify/0.9.0
---

# Purpose

The repository asks one practical question: can open-weight models reached through OpenRouter
replace costly proprietary coding assistants, and where can they not be trusted? It answers it
with **metamorphic ("swap one detail") auditing**: send the same request many times, change only
something that should not matter (the country in a story, the customer asking for code, the host
serving the model), and measure what changes. It deliberately treats no country as the suspect;
US, European and Chinese models go through identical tests.

There are three layers:

1. **A harness** (`pilot/`) — generates audit prompts, collects answers, scores them
   deterministically or with LLM judges, runs generated code against hidden tests in a sandbox,
   and reports statistics.
2. **Recorded runs** (`pilot/runs/`) — every raw response, judgment and score from the pilot,
   committed so the published numbers can be regenerated without spending money.
3. **Publications** — a technical paper, a plain-language essay (which is also the repo README),
   an evidence companion, and a scorecard image.

# How the pieces fit

```
experiments.py ─┐                          ┌─> scoring.py ──────┐
codetasks.py  ──┴─> run.py ──> client.py ──┤                    ├─> analyze.py ─> report.md
                    (plan/collect/judge/   └─> sandbox.py ──────┘      │
                     score/report)             sandbox_runner.py       └─> make_scorecard.py ─> docs/*.png, README tables
```

| Concept | Role |
| --- | --- |
| [Audit CLI](../services/audit-cli.md) | Entry point; orchestrates the pipeline stages over a run directory. |
| [Experiments](../modules/experiments.md) | Builds every audit item: prompts, groups, paraphrases, repeats. |
| [Code tasks](../modules/codetasks.md) | The five security-critical coding tasks and their GOOD/BAD reference solutions. |
| [OpenRouter client](../modules/openrouter-client.md) | One chat call with retries and credit-exhaustion handling. |
| [Scoring](../modules/scoring.md) | Deterministic scorers, judge prompts and blank-answer handling. |
| [Sandbox](../modules/sandbox.md) | Isolated execution of model-written code against hidden tests. |
| [Analysis](../modules/analyze.md) | Contrasts, exact tests, BH correction, panel z, flags, report. |
| [Scorecard](../modules/scorecard.md) | README tables and scorecard images from saved runs. |
| [Fake client](../modules/fake-client.md) | Offline models with planted biases, used to validate the pipeline. |
| [Run directory](../data/run-directory.md) | The files every run writes, and which are the source of truth. |
| [Recorded runs](../data/recorded-runs.md) | `code1`, `nc1`, `glm16k`, `smoke1`, `fake` — what each contains. |
| [Panel configuration](../operations/panel-config.md) | Targets, host pinning and judges. |
| [Offline validation](../operations/offline-validation.md) | How to check the pipeline without spending money. |
| [Publications](../references/publications.md) | The paper, essays, evidence file and PDF. |

# Key ideas a newcomer needs

- **The comparison lives only on the auditor's side.** Each prompt is sent alone, in its own
  conversation, so a model never sees the pair it is being compared against.
- **Trust belongs to an endpoint doing a task**, not a model name: the same weights on two hosts
  gave very different broken-code rates, so hosts are pinned where it matters.
- **Non-answers are outcomes.** Blank replies, refusals, length cut-offs and API failures are
  counted separately rather than dropped; dropping them once hid a real pattern.
- **Everything is cached and resumable.** Rerunning a command re-sends only missing calls.
