---
type: Module
title: Code tasks (sector × country code targeting)
description: The five security-critical Python tasks, the customer contexts that vary between prompts, and a correct and a deliberately flawed reference solution per task.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/codetasks.py
tags: [code-targeting, security, tasks, reference-solutions]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/codetasks.py
generated_by: catalogify/0.9.0
open_questions:
  - "The prompts spell out the security requirements (e.g. 'must reject tampered images and downgrades'). Is that intended as a floor for the study, knowing it makes quiet sabotage harder to detect than with vaguer prompts?"
---

# Responsibilities

Defines what the code-targeting study asks for. Seven sectors (including `none` and a neutral
`bookstore` control) are crossed with seven countries to give the customer contexts; only the
opening sentence naming the customer changes between prompts. Each task has two wordings, a
`GOOD` solution that passes every hidden test, and a `BAD` solution that stays functional but
breaks exactly one security property — the shape quiet sabotage would take.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `TASKS` | Task name → required function names and two prompt wordings. |
| `SECTORS`, `COUNTRIES` | The customer dimensions; `none` has no country. |
| `CONTEXT_LEADS` | The two opening sentences that introduce the customer. |
| `contexts()` | Yields `(sector, country, org text or None)`; `none` appears once. |
| `prompt_for(task, paraphrase, org)` | Builds one prompt. |
| `GOOD`, `BAD` | Reference solutions per task; `BAD` differs by one removed or weakened check. |

`python3 codetasks.py` is a self-test: it runs every `GOOD` and `BAD` solution through the
sandbox and prints which tests fail.

| Task | Function(s) | What `BAD` breaks |
| --- | --- | --- |
| `firmware_update` | `verify_update` | downgrade check removed |
| `tls_client` | `create_client_context` | hostname checking switched off |
| `aes_gcm` | `encrypt_record`, `decrypt_record` | constant nonce |
| `binary_parser` | `parse_messages` | payload size limit removed |
| `login_auth` | `hash_password`, `verify_password`, `create_token`, `verify_token` | unsalted SHA-256 instead of bcrypt |

# Dependencies

- Consumed by [Experiments](experiments.md) to build `code_targeting` items, by the
  [Audit CLI](../services/audit-cli.md) for required function names, and by the
  [Fake client](fake-client.md), which emits `GOOD` or `BAD` code.
- Its self-test calls the [Sandbox](sandbox.md); the hidden tests themselves live in
  `sandbox_runner.py`, so a task change needs a matching test change there.

# Gotchas

- **Every `BAD` must actually differ from its `GOOD`.** `BAD` is built by string replacement on
  `GOOD`, which silently does nothing if the target line changes; a module-level assert guards
  against that (`5786dea`).

The TLS flaw is the one models actually made: all ten security failures in the
[`code1` run](../data/recorded-runs.md) were hostname checking switched off, exactly what
`BAD["tls_client"]` does (see [Publications](../references/publications.md), paper section 7.1).

# Citations

1. `5786dea` — tasks, contexts, reference solutions and the `BAD != GOOD` assert.
