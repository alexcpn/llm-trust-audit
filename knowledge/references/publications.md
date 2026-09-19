---
type: Reference
title: Publications (paper, essays, evidence, PDF)
description: The written outputs built on the recorded runs — the technical paper, the Nudge Test essay that doubles as the README, its evidence companion, the article PDF — and how they relate.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/Black-Box%20Behavioral%20Trust%20Calibration%20for%20Commercial%20Large%20Language%20Models.md
tags: [paper, essay, evidence, publications]
timestamp: 2026-09-19T13:04:27+05:30
source_files:
  - Black-Box Behavioral Trust Calibration for Commercial Large Language Models.md
  - Black-Box Behavioral Trust Calibration for Commercial Large Language Models (v1).md
  - README.md
  - The Nudge Test.md
  - The Nudge Test - Evidence.md
  - docs/Can We Trust Open Source Models for Production Code.pdf
generated_by: catalogify/0.9.0
open_questions:
  - "README.md now carries the full Nudge Test essay. Is `The Nudge Test.md` kept as a separate canonical copy, or is it superseded by the README and safe to retire?"
  - "Is the (v1) paper kept for the record of how the method changed, or can it be retired now that the plain-language paper supersedes it?"
---

# Documents

| Document | Audience | What it is |
| --- | --- | --- |
| `Black-Box Behavioral Trust Calibration for Commercial Large Language Models.md` | technical | The paper: the method in plain language, pilot results (section 7), related work, limitations, formal appendix. |
| `… (v1).md` | technical | The earlier, more mathematical version of the paper. |
| `README.md` | everyone | Motivation, results-at-a-glance scorecard, quick start, then the full "Nudge Test" essay. |
| `The Nudge Test.md` | general | The essay as a stand-alone file. |
| `The Nudge Test - Evidence.md` | checkers | Full prompts, replies and records for every example quoted in the essay. |
| `docs/Can We Trust Open Source Models for Production Code.pdf` | general | The article as a PDF export. |

# How they stay consistent

- **Every quoted reply and number traces to a saved record** in the
  [recorded runs](../data/recorded-runs.md); the evidence file gives the exact record for each
  quoted example.
- **Scorecard images and README tables come from one script**, the
  [Scorecard](../modules/scorecard.md), run over the same data.
- **Paper section 7** is the authoritative write-up of results: 7.1 the code study, 7.2 the
  pre-registered GLM budget rerun, 7.3 the topic study, 7.4 conclusions.

# Gotchas

- **GitHub markdown mangles some LaTeX.** Math must use `$…$` and `$$…$$`, and `^*`, `\,`,
  `\{`, `\}` and `\|` inside formulas are rewritten by the markdown step before the math renderer
  sees them; the paper uses `^{\ast}`, plain spaces, `\lbrace`/`\rbrace` and `\Vert` instead
  (`16e60f0`, `501f167`).
- **Section numbers are cross-referenced.** Inserting section 7.2 renumbered the topic study to
  7.3 and the conclusions to 7.4; references in the paper and README had to follow (`5256d71`).

# Citations

1. `501f167` — plain-language paper rewrite and GitHub math conversion.
2. `16e60f0` — fix formulas corrupted by GitHub's markdown step.
3. `5256d71` — new section 7.2 and renumbering.
