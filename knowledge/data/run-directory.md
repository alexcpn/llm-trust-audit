---
type: Data Model
title: Run directory layout
description: The files a run directory holds, which stage writes each, what a record looks like, and which files are the source of truth versus derived.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/run.py
tags: [data, cache, jsonl, csv, run-directory]
timestamp: 2026-09-19T07:38:00+05:30
source_files:
  - pilot/run.py
  - pilot/sandbox.py
  - pilot/analyze.py
generated_by: catalogify/0.9.0
---

# Schema

| File | Written by | Kind | Contents |
| --- | --- | --- | --- |
| `run.json` | first command | source | `profile`, `experiments`, `created`. Later commands inherit profile and experiments from it. |
| `responses.jsonl` | `collect` | **source of truth** | One line per call attempt: `key`, `target`, `model`, `origin`, `pin`, item fields (`uid`, `cell`, `exp`, `item`, `group`, `variant`, `paraphrase`, `repeat`, `prompt`, `meta`), `result`, `ts`. |
| `judgments.jsonl` | `judge` | source | `key`, `judge`, `resp_key`, `result`, `parsed` (rubric JSON or `null`). |
| `exec_cache.jsonl` | `score` | cache | `key` (runner version, task, code), `result` of the hidden tests. |
| `pricing.json` | `plan` | cache | OpenRouter's public per-model prices at plan time. |
| `registry_cache.json` | `score` | cache | PyPI and OSV lookups. |
| `scores.csv` | `score` | derived | One row per answer (`unit == "answer"`) plus one per diversity cell (`unit == "cell"`): identifiers, `ok`, `provider_served`, `finish_reason`, `truncated`, `chars`, `cost`, per-experiment metrics, and for code `sector`, `country`, `task`. |
| `score_details.jsonl` | `score` | derived | Per-answer detail; for code: `status`, `failed_security`, `failed_functional`, `info_fail`, `net_attempts`, `errors`. |
| `contrasts.csv` | `report` | derived | Every contrast with CI, `p`, `q`, `panel_z`, `flag`. |
| `report.md` | `report` | derived | Human-readable findings. |

`result` in `responses.jsonl` is the [OpenRouter client](../modules/openrouter-client.md)'s
return value: `ok`, `content`, `finish_reason`, `provider`, `model_served`, `usage` (including
`completion_tokens_details.reasoning_tokens` and `cost`), `id`, or `status`/`error` on failure.

# Examples

```python
# Read a run the way the harness does: dedupe by key, last line wins.
rows = {}
for line in open("pilot/runs/code1/responses.jsonl"):
    r = json.loads(line)
    rows[r["key"]] = r
```

# Dependencies

- Written by the [Audit CLI](../services/audit-cli.md), the [Sandbox](../modules/sandbox.md)
  (`exec_cache.jsonl`) and [Analysis](../modules/analyze.md) (`contrasts.csv`, `report.md`).
- Read by the [Scorecard](../modules/scorecard.md). Concrete instances are listed under
  [recorded runs](recorded-runs.md).

# Gotchas

- **Line count is not request count.** `responses.jsonl` is append-only: a retry appends a new
  line for the same key (readers must dedupe by `key`, last line winning, as `JsonlStore` does),
  and answers to a prompt that was later edited stay in the file under their old key
  (`5786dea`). Scoring keeps only keys that match the current items. `code1` holds 7,030
  distinct keys for 6,860 current requests; the other 170 are answers to the firmware task's
  second wording from before it was clarified, and are ignored.
- **Everything derived can be regenerated offline.** `score` and `report` read only cached files
  (use `--offline` to skip registry lookups), so deleting `scores.csv` costs nothing, while
  deleting `responses.jsonl` loses paid data (`5786dea`).
- **`scores.csv` covers every target with answers in the run**, not only those named when it was
  last regenerated (`03c822b`).
- **A run's `max_tokens` is not recorded in `run.json`.** It is visible only indirectly, from
  completion-token ceilings in `usage`; the budget rerun therefore lives in its own directory
  with its budget written in `PREREG.md` (`5256d71`).

# Citations

1. `5786dea` — run-directory files and the append-only store.
2. `03c822b` — whole-run scoring.
3. `5256d71` — separate run directory for a different budget.
