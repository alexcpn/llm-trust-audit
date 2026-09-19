---
type: Module
title: Fake client (planted-bias models)
description: An offline stand-in for OpenRouter whose fake models carry known, planted biases, so the pipeline can be shown to find what it is supposed to find before any money is spent.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/fake.py
tags: [testing, validation, fake, offline]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/fake.py
  - pilot/fake_panel.json
generated_by: catalogify/0.9.0
---

# Responsibilities

Implements the same `chat` signature as the [OpenRouter client](openrouter-client.md) with no
network. Each fake model looks up the prompt among all items to learn which experiment and group
it belongs to, then answers fairly or with a planted slant. Fake judges parse markers the fake
targets embed, so judge-scored experiments work end to end offline.

| Fake model | Behaviour |
| --- | --- |
| `fake/fair` | No bias; noise only. |
| `fake/steered-cn` | Cooler on China-set premises, drops critical facts about Shanghai, weak crypto for Chinese organisations, wrong answers on China-subject reasoning, fading deflection near Tiananmen, templated China-political stories. |
| `fake/steered-us` | The same pattern aimed at the United States. |
| `fake/judge-*` | Reads the targets' markers and returns rubric JSON. |

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `FakeClient` | Drop-in client; `chat(...)` returns the same result shape as the real one. |
| `ITEMS` | Prompt text → item, built from the `full` profile plus `code_targeting`. |

Selected with `--fake --panel fake_panel.json` on the [Audit CLI](../services/audit-cli.md).

# Dependencies

- Builds its lookup with [Experiments](experiments.md) (`build_items`, `OMISSION_FACTS`) and emits
  `GOOD`/`BAD` solutions from [Code tasks](codetasks.md) for code items.
- Backs the [offline validation](../operations/offline-validation.md) playbook and the `fake`
  entry in [recorded runs](../data/recorded-runs.md).

# Gotchas

- **Lookup is by exact prompt text.** A fake model recognises an item only if the prompt matches
  `ITEMS` exactly, and `ITEMS` is built from the `full` profile, so a prompt from a template or
  profile it did not build gets a generic answer rather than a planted one (`5786dea`).

# Citations

1. `5786dea` — fake client, planted biases and fake panel.
