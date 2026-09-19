---
type: Module
title: Scorecard generator
description: Builds the README's results tables and the light and dark scorecard images from saved runs, applying the pass / caution / problem thresholds from the README legend.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/make_scorecard.py
tags: [scorecard, readme, matplotlib, reporting]
timestamp: 2026-09-19T07:38:00+05:30
source_files:
  - pilot/make_scorecard.py
generated_by: catalogify/0.9.0
open_questions:
  - "The README tables are pasted from this script's stdout by hand, so they can drift from the images. Should the script write the README section itself?"
---

# Responsibilities

A one-shot report script. It reads `nc1` (topic study) and `code1` (code study), plus the
separate `glm16k` rerun, computes one value per endpoint and column, maps each to a status with
fixed thresholds, prints two markdown tables, and renders `docs/scorecard-work{,-dark}.png` and
`docs/scorecard-politics{,-dark}.png`. Status is never colour-only: each cell also carries its
number and a ✓ / ! / ✗ / – mark.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `main()` | Prints the tables and renders all four images. |
| `build()` | Computes the work and politics rows for every endpoint in `ENDPOINTS`. |
| `rerun_row()` | The separate GLM row from the 24k-token rerun; only the code columns were measured. |
| `band(value, caution, problem)` | Status for a lower-is-better value. |
| `markdown(work, politics)` | The two README tables. |
| `render(rows, headers, title, theme, path, has_untested)` | One scorecard image. |
| `ENDPOINTS`, `CODE_TARGET`, `RERUN` | Row list; host-pinned code targets; rerun placement and labels. |

# Dependencies

- Reads [recorded runs](../data/recorded-runs.md) (`scores.csv` and `contrasts.csv` produced by
  the [Audit CLI](../services/audit-cli.md) and [Analysis](analyze.md)).
- Writes the images shown in [Publications](../references/publications.md) (the README).
- In history, every commit touching `pilot/` also touched `docs/` (confidence 100%, lift 2.5,
  support 5 commits): regenerating the scorecard is how a code or run change reaches the images.
  With only 15 commits analysed this is a small sample, but the mechanism is direct — this
  script writes `docs/`.
- External: `matplotlib`, `pandas`.

# Gotchas

- **Code columns for some models come from a host-pinned target.** Llama 4 Maverick and GLM 5.3
  Flash rows read `@deepinfra` and `@z-ai` results, because the host changed code reliability;
  the unpinned names would read the wrong rows (`c5ee55b`).
- **Two narrow images, not one wide one.** The scorecard was split into everyday-work and
  political panels with larger text so both stay readable at README width (`a2f3db5`).
- **The rerun is never averaged with the original.** The 24k-token GLM run is a different budget
  and one task only, so it is rendered as its own row under GLM, with every column it did not
  measure marked "not tested" (`5256d71`).
- **Cut-offs worsen the broken-code status.** The broken-code cell takes the worse of the
  broken-rate band and the cut-off-rate band, so a model that rarely writes broken code but often
  returns nothing is still marked caution (`c5ee55b`).

# Citations

1. `c5ee55b` — host-pinned code targets for Llama and GLM; cut-off rate in the status.
2. `a2f3db5` — split into two images.
3. `5256d71` — separate rerun row.
