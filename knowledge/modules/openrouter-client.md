---
type: Module
title: OpenRouter client
description: A minimal chat-completions client for OpenRouter with retries, provider pinning, and a distinction between in-flight credit waits and true credit exhaustion.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/client.py
tags: [client, openrouter, http, retries]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/client.py
generated_by: catalogify/0.9.0
open_questions:
  - "Are the 240-second timeout and 8 retries tuned for long reasoning-model responses (the 24k-token GLM rerun took about 70 minutes for 196 calls at 8 workers), or arbitrary defaults?"
---

# Responsibilities

One method, one HTTP call pattern: build a chat-completions body (model, messages, `max_tokens`,
usage accounting, optional provider pin and extra fields), post it, retry transient failures with
exponential backoff, and return a flat result dict. It never raises for API errors; callers read
`ok`, `status`, `error` and `fatal`.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `OpenRouterClient` | Reads the API key from the environment; holds timeout and retry settings. |
| `chat(model, messages, provider, extra, max_tokens, temperature)` | One completion. Returns `ok`, `content`, `finish_reason`, `provider` (who actually served it), `model_served`, `usage`, `id`. |
| `RETRY_STATUS` | HTTP statuses retried with backoff (408, 409, 425, 429, 5xx, Cloudflare 52x). |

# Dependencies

- Used by the [Audit CLI](../services/audit-cli.md) for target and judge calls; the
  [Fake client](fake-client.md) implements the same `chat` signature for offline runs.
- Provider pins come from the [panel configuration](../operations/panel-config.md).
- External: `requests`.

# Gotchas

- **A 402 is not always "out of money".** OpenRouter returns 402 both when credit is reserved by
  requests still in flight and when the balance is exhausted. The first waits (honouring
  `Retry-After`) and retries; the second returns `fatal: "credits"`, which the CLI turns into a
  clean stop for the stage (`5786dea`).
- **Audit traffic is deliberately anonymous.** No `HTTP-Referer` or `X-Title` headers are sent,
  because naming the tool would make audit traffic identifiable (`5786dea`).
- **Record the serving provider.** `provider` in the result is the company that actually served
  the call; with unpinned routing one model can be served by many hosts, which matters because
  reliability differed by host (`5786dea`).

# Citations

1. `5786dea` — client, 402 handling and header policy.
