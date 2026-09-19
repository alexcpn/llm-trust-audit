---
type: Configuration
title: Panel configuration (panel.json)
description: The list of target model endpoints, their origin labels and optional host pins, and the three judge models used to score open-ended answers.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/panel.json
tags: [configuration, models, openrouter, judges, host-pinning]
timestamp: 2026-09-17T09:59:11+05:30
source_files:
  - pilot/panel.json
generated_by: catalogify/0.9.0
open_questions:
  - "Several targets in panel.json (gpt-5.4, claude-haiku-4.5, grok-4.3, gpt-oss-120b, minimax-m3, and the unpinned glm-5.3-flash and llama-4-maverick) do not appear in the scorecard. Are they retired, or kept for future runs?"
---

# Schema

```json
{
  "_comment": "...",
  "targets": [
    {"name": "<unique id used in run data>", "model": "<openrouter model id>",
     "origin": "<label for reports>", "provider": {"order": ["<host>"], "allow_fallbacks": false},
     "extra": {"...": "optional request fields"}}
  ],
  "judges": [{"name": "judge-<id>", "model": "<openrouter model id>"}]
}
```

| Field | Meaning |
| --- | --- |
| `name` | The key everything else uses: cache keys, `target` column, scorecard lookups, `--targets`. |
| `model` | OpenRouter model id. |
| `provider` | Optional pin. With `allow_fallbacks: false`, the call fails rather than moving to another host. |
| `origin` | Free-text label (country, open weights, host). |

The file contains no secrets; the API key comes from the `OPENROUTER_API_KEY` environment
variable read by the [OpenRouter client](../modules/openrouter-client.md).

**Targets (18):** US proprietary (GPT-5.4 Mini, GPT-5.4, Claude Haiku 4.5, Claude Sonnet 5,
Gemini 3.1 Flash Lite, Grok 4.3), US open weights (gpt-oss-120b, Llama 4 Maverick and its
DeepInfra pin), EU (Mistral Medium 3.5), and Chinese families (DeepSeek V4 Flash unpinned and
pinned to DeepInfra and Alibaba, Qwen3.7 Plus, GLM 5.3 Flash and its Z.AI pin, Kimi K2.6,
MiniMax M3). **Judges (3):** GPT-5.4 Mini, Qwen3.7 Plus, Mistral Small — deliberately from three
different makers.

# Dependencies

- Read by the [Audit CLI](../services/audit-cli.md) (`load_panel`, `analysis_panel`); the
  offline counterpart is `fake_panel.json`, used by the [Fake client](../modules/fake-client.md).
- The [Scorecard](../modules/scorecard.md) looks up rows by these `name` values.

# Gotchas

- **A pin is a different target, not a setting.** `deepseek-v4-flash@deepinfra` and
  `@alibaba` are separate names with separate cache keys and separate results, because the same
  weights produced very different broken-code rates on the two hosts. Llama 4 Maverick and GLM
  5.3 Flash were added to the code study as pinned targets for the same reason (`c5ee55b`).
- **Renaming a target orphans its data.** The name is part of every cache key, so a renamed
  target looks uncollected and its old answers disappear from scoring (`5786dea`).

# Citations

1. `5786dea` — initial panel and name-based cache keys.
2. `c5ee55b` — pinned Llama 4 Maverick and GLM 5.3 Flash targets.
