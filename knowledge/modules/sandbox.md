---
type: Module
title: Sandbox and hidden tests
description: Runs untrusted model-written code against hidden functional and security tests in an isolated, network-less sandbox, with results cached by runner version and code.
resource: https://github.com/alexcpn/llm-trust-audit/blob/main/pilot/sandbox.py
tags: [sandbox, bubblewrap, security-tests, isolation, cache]
timestamp: 2026-09-16T20:18:12+05:30
source_files:
  - pilot/sandbox.py
  - pilot/sandbox_runner.py
generated_by: catalogify/0.9.0
open_questions:
  - "The resource limits set CPU, address space and file size but not the process count (RLIMIT_NPROC). Is that deliberately omitted, and if so why?"
  - "The unshare fallback blocks the network but leaves the filesystem visible, with only a warning. Are results produced under unshare acceptable for published runs, or should publication require bwrap?"
---

# Responsibilities

Two halves with a trust boundary between them. `sandbox.py` runs on the host: it extracts the
solution from an answer, writes it to a temp directory, launches `sandbox_runner.py` inside
`bwrap` (or `unshare`) with resource limits, and reads back `result.json`. `sandbox_runner.py`
runs **inside** the sandbox next to the untrusted `solution.py`: it patches the network, imports
the solution and runs the task's hidden tests.

# Interfaces

| Symbol | Purpose |
| --- | --- |
| `extract_solution(text, required_names)` | Picks the code block (or joined blocks) that defines every required function; `None` if absent. |
| `detect_mode()` | `bwrap`, `unshare`, or `None`. |
| `run_tests(code, task, mode, cache, timeout)` | Runs the hidden tests; returns import status, functional, security and info results, network attempts, errors. |
| `ExecCache` | Append-only JSONL cache of test results. |
| `RUNNER_VERSION` | Hash of `sandbox_runner.py`, part of every cache key. |
| `TESTS` | Task name → hidden test function, in the runner. |
| `rejects(fn)`, `record(kind, name, fn)` | Test helpers: a rejection is `False`/`None` or an exception. |

Test kinds: **functional** (does the job at all), **security** (keeps a security property; only
meaningful when functional passes), **info** (recorded, not scored).

# Dependencies

- Called by the [Audit CLI](../services/audit-cli.md) (`run_code_tests`) and by the
  [Code tasks](codetasks.md) self-test. Test functions correspond one-to-one with
  `codetasks.TASKS`.
- Writes `exec_cache.jsonl` in the [run directory](../data/run-directory.md).
- External: `bwrap` or `unshare` binaries; `cryptography`, `bcrypt`, `PyJWT` inside the sandbox.

# Gotchas

- **Refuse rather than run unsandboxed.** With neither `bwrap` nor `unshare`, the CLI exits unless
  `--unsafe-exec` is passed; `unshare` runs with a warning because the filesystem stays visible
  (`5786dea`).
- **Changing the runner invalidates the cache on purpose.** The cache key includes a hash of
  `sandbox_runner.py`, so editing a hidden test re-executes every solution instead of reusing
  stale verdicts (`5786dea`).
- **The network guard is in-process.** Besides namespace isolation, the runner replaces
  `socket.connect` and `socket.getaddrinfo` so that any non-local connection is both blocked and
  recorded as a `net_attempt` — a metric in its own right (`5786dea`).
- **Security verdicts require working code.** A solution that fails import or any functional test
  is classed broken, and its security results are not counted (`5786dea`).

# Citations

1. `5786dea` — sandbox launcher, hidden tests, cache and network guard.
