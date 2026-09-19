---
type: Playbook
title: Offline validation
description: How to check the harness end to end without an API key or spending money — planted-bias fake runs, the code-task self-test, and the blank-answer regression tests.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/test_blank_answers.py
tags: [playbook, testing, validation, offline]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/test_blank_answers.py
  - pilot/fake_panel.json
generated_by: catalogify/0.9.0
---

# When to use

Run these after any change to scoring, analysis, experiments or the sandbox, before a paid run.

# Steps

All commands run from `pilot/`.

1. **Planted-bias run.** Plant known biases and check the audit finds them and nothing else:

   ```bash
   python3 run.py all --run runs/fake --panel fake_panel.json --fake --profile pilot --yes
   ```

   Read `runs/fake/report.md`: effects planted in `fake/steered-cn` and `fake/steered-us`
   should be flagged, and `fake/fair` should have no flags.

2. **Hidden-test self-test.** Every `GOOD` solution must pass and every `BAD` solution must
   fail exactly its targeted security test:

   ```bash
   python3 codetasks.py
   ```

3. **Regression tests** for blank-answer scoring and judge scheduling:

   ```bash
   python3 -m unittest test_blank_answers
   ```

# Dependencies

- Uses the [Fake client](../modules/fake-client.md) and `fake_panel.json`, the
  [Code tasks](../modules/codetasks.md) reference solutions and the
  [Sandbox](../modules/sandbox.md).
- `test_blank_answers.py` exercises [Scoring](../modules/scoring.md),
  [Analysis](../modules/analyze.md) and the [Audit CLI](../services/audit-cli.md).

# Gotchas

- **The fake run directory is committed.** `runs/fake` is tracked, so rerunning step 1 into it
  changes tracked files; `runs/fake-check/` and `runs/fake-code/` are the git-ignored scratch
  locations for throwaway validation runs (`5786dea`).
- **Sandbox tests need `bwrap`.** Without it, step 2 and any code scoring either fall back to
  `unshare` with a warning or refuse to run (see [Sandbox](../modules/sandbox.md)) (`5786dea`).

# Citations

1. `5786dea` — fake panel, regression tests, tracked `runs/fake` and the git-ignored scratch runs.
