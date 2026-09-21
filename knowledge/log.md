# Knowledge Bundle Update Log

## 2026-09-21
Commit: `1f96970`
* **Update**: Sandbox startup failures are no longer scored as broken model code. Refreshed `modules/sandbox.md` (added `preflight` and `SandboxUnavailable` to the interfaces, plus gotchas on infrastructure faults and on `sandbox_runner.py` being frozen by the cache key), `services/audit-cli.md` (scoring refuses to run without a working sandbox) and `data/run-directory.md` (poisoned `exec_cache.jsonl` rows are dropped on load). No concepts added or retired; open questions unchanged.

## 2026-09-19
Commit: `e8c542a`
* **Initialization**: Generated bundle from commit `e8c542a` with catalogify. 15 concepts across architecture, services, modules, data, operations and references. History is thin (16 commits; every module except run.py and make_scorecard.py arrived in the initial commit `5786dea`), so most gotchas are drawn from code comments tied to their introducing commit, and uncertain intent is parked in open_questions.
