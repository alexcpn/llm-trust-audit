---
type: Service
title: Audit CLI (run.py)
description: The command-line entry point that plans, collects, judges, scores and reports an audit run, with every stage cached and resumable.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/run.py
tags: [cli, orchestration, pipeline, cache]
timestamp: 2026-09-21T19:19:19+05:30
source_files:
  - pilot/run.py
generated_by: catalogify/0.9.0
open_questions:
  - "Response cache keys hash target, model, provider pin, uid and prompt, but not --max-tokens or temperature. Should they, so that rerunning into an existing run directory at a different budget cannot silently reuse answers from the old budget?"
  - "`--run` is used as given, so a relative path resolves against the shell's working directory, not the repository. Should it be anchored to the repo or to pilot/, given the documented commands assume the repo root?"
  - "The `plan` cost estimate uses a fixed expected completion length per experiment, which badly underestimates reasoning models that run to the token limit. Is the estimate meant only as a floor, or should it use observed usage from earlier runs?"
---

# Responsibilities

A single-process batch job, driven by one subcommand per stage: `plan` (counts and cost
estimate), `collect` (query targets), `judge` (LLM judges for open-ended answers), `score`
(deterministic scoring plus sandboxed code tests), `report` (statistics), and `all`. Each stage
reads and appends to files in a run directory; nothing is recomputed that is already cached, so
an interrupted run is resumed by rerunning the same command.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `main()` | Parses the CLI (`--run`, `--profile`, `--experiments`, `--tasks`, `--targets`, `--judges`, `--max-tokens`, `--seed`, `--workers`, `--fake`, `--unsafe-exec`, `--yes`) and dispatches a stage. |
| `JsonlStore` | Append-only JSONL cache keyed by request hash; later lines win, so a retry overwrites a failure. |
| `target_calls(panel, items, seed)` | Every (key, target, item) triple, shuffled with the seed to interleave models and experiments like real traffic. |
| `cmd_plan(args, panel, items)` | Prices only outstanding work from OpenRouter's public pricing. |
| `cmd_collect(args, panel, items)` | Sends uncached calls in parallel; stops the stage cleanly on credit exhaustion. |
| `cmd_judge(args, panel, items)` | Sends each finished, non-blank, judge-scored answer to every judge. |
| `cmd_score(args, panel, items)` | Builds `scores.csv` and `score_details.jsonl`; routes code answers to `run_code_tests`. |
| `run_code_tests(args, jobs, details)` | Extracts a solution and runs the hidden tests in the sandbox. |
| `analysis_panel(args, items)` | The targets scoring and reporting must cover: all with cached answers, plus any requested. |
| `parallel(jobs, fn, workers, label)` | Thread pool with progress output and a per-stage credit stop. |

# Dependencies

- Builds items with [Experiments](../modules/experiments.md) (`build_items`, `EXPERIMENTS`,
  `EXPECTED_COMPLETION_TOKENS`).
- Calls models through the [OpenRouter client](../modules/openrouter-client.md), or the
  [Fake client](../modules/fake-client.md) under `--fake`.
- Scores with [Scoring](../modules/scoring.md) and executes code through the
  [Sandbox](../modules/sandbox.md), using task names from [Code tasks](../modules/codetasks.md).
- Hands the scored run to [Analysis](../modules/analyze.md) for `report`.
- Reads targets and judges from the [panel configuration](../operations/panel-config.md) and
  writes the [run directory](../data/run-directory.md).
- External: `requests`, `pandas` (imported lazily in `cmd_score`).

# Gotchas

- **Scoring and reporting must describe the whole run, not the targets named on the command
  line.** Collecting with `--targets <subset>` once made `score` and `report` rewrite the run's
  shared `scores.csv` and report with only that subset, dropping every other model's results;
  `analysis_panel` now widens scoring to every target with cached answers (`03c822b`).
- **`--tasks` narrows `code_targeting` without changing identity.** It filters items after
  `build_items`, leaving prompts, uids and cache keys untouched, so a single-task run is a strict
  subset of a full one (`5256d71`).
- **A changed token budget needs a new run directory.** Cache keys do not include
  `--max-tokens` (defined in `5786dea`), so the pre-registered 24k rerun went into its own
  directory, `glm16k`, rather than into `code1` (`5256d71`).
- **Scoring refuses to run without a working sandbox.** `run_code_tests` probes the sandbox
  before scoring and exits if it cannot start, and stops the stage if it breaks part way
  through, because a launcher failure would otherwise be written into the results as broken
  model code (`1f96970`).
- **Truncated answers are never scored for content.** `finish_reason == "length"` rows are kept
  with no metrics and are skipped by `needs_judgment`; blank but successful answers are scored as
  non-answers instead of being dropped (`5786dea`).

# Citations

1. `5786dea` — initial harness, including the cache-key definition and truncation handling.
2. `03c822b` — keep scoring whole-run when a subset of targets is collected.
3. `5256d71` — add `--tasks`; the budget rerun uses a separate run directory.
4. `1f96970` — refuse to score when the sandbox cannot start.
