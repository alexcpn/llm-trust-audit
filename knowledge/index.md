---
okf_version: "0.1"
---

# Architecture

* [Architecture overview](architecture/overview.md) - Start here — a black-box behavioural audit harness for LLM endpoints on OpenRouter, the pilot runs it produced, and the paper and essays built on them.

# Services

* [Audit CLI (run.py)](services/audit-cli.md) - The command-line entry point that plans, collects, judges, scores and reports an audit run, with every stage cached and resumable.

# Modules

* [Experiments (item generators)](modules/experiments.md) - Defines every audit experiment — its prompts, groups, baseline, metrics and scoring kind — and expands them into individual audit items per profile.
* [Code tasks](modules/codetasks.md) - The five security-critical Python tasks, the customer contexts that vary between prompts, and a correct and a deliberately flawed reference solution per task.
* [OpenRouter client](modules/openrouter-client.md) - A minimal chat-completions client for OpenRouter with retries, provider pinning, and a distinction between in-flight credit waits and true credit exhaustion.
* [Scoring](modules/scoring.md) - Turns one model answer into metrics — omission, static code checks, reasoning answers, creative diversity, judge prompts — and defines how a blank answer is scored.
* [Sandbox and hidden tests](modules/sandbox.md) - Runs untrusted model-written code against hidden functional and security tests in an isolated, network-less sandbox, with results cached by runner version and code.
* [Analysis and report](modules/analyze.md) - Computes group-versus-baseline contrasts with bootstrap intervals, exact p-values, Benjamini-Hochberg correction and a panel z-score, flags findings, and writes report.md and contrasts.csv.
* [Scorecard generator](modules/scorecard.md) - Builds the README's results tables and the light and dark scorecard images from saved runs, applying the pass / caution / problem thresholds from the README legend.
* [Fake client](modules/fake-client.md) - An offline stand-in for OpenRouter whose fake models carry known, planted biases, so the pipeline can be shown to find what it is supposed to find before any money is spent.

# Data

* [Run directory layout](data/run-directory.md) - The files a run directory holds, which stage writes each, what a record looks like, and which files are the source of truth versus derived.
* [Recorded runs](data/recorded-runs.md) - The five committed run directories — code1, nc1, glm16k, smoke1 and fake — what each measured, how it was produced, and which published numbers come from it.

# Operations

* [Panel configuration (panel.json)](operations/panel-config.md) - The list of target model endpoints, their origin labels and optional host pins, and the three judge models used to score open-ended answers.
* [Offline validation](operations/offline-validation.md) - How to check the harness end to end without an API key or spending money — planted-bias fake runs, the code-task self-test, and the blank-answer regression tests.

# References

* [Publications](references/publications.md) - The written outputs built on the recorded runs — the technical paper, the Nudge Test essay that doubles as the README, its evidence companion, the article PDF — and how they relate.
