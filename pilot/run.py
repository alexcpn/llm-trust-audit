#!/usr/bin/env python3
"""Black-box behavioural audit pilot over OpenRouter.

  python3 run.py plan    --run runs/pilot1 --profile pilot           # counts and cost estimate, no key needed
  python3 run.py collect --run runs/pilot1 --profile pilot           # query targets (resumable, cached)
  python3 run.py judge   --run runs/pilot1                           # score open-ended answers with judges
  python3 run.py score   --run runs/pilot1                           # deterministic scoring, merge judges
  python3 run.py report  --run runs/pilot1                           # statistics and report.md
  python3 run.py all     --run runs/pilot1 --profile pilot --yes     # everything

Offline validation with implanted biases:
  python3 run.py all --run runs/fake --panel fake_panel.json --fake --profile pilot --yes
"""
import argparse
import hashlib
import json
import os
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import experiments as E
import scoring

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:24]


class JsonlStore:
    def __init__(self, path):
        self.path, self.lock, self.rows = path, threading.Lock(), {}
        if os.path.exists(path):
            for line in open(path):
                if line.strip():
                    r = json.loads(line)
                    self.rows[r["key"]] = r  # later lines win, so retries overwrite failures

    def ok(self, key):
        r = self.rows.get(key)
        return bool(r and r["result"].get("ok"))

    def add(self, row):
        with self.lock:
            self.rows[row["key"]] = row
            with open(self.path, "a") as f:
                f.write(json.dumps(row) + "\n")


def load_panel(args):
    panel = json.load(open(args.panel))
    if args.targets:
        keep = set(args.targets.split(","))
        panel["targets"] = [t for t in panel["targets"] if t["name"] in keep]
    if args.judges:
        keep = set(args.judges.split(","))
        panel["judges"] = [j for j in panel["judges"] if j["name"] in keep]
    return panel


def run_meta(args):
    path = os.path.join(args.run, "run.json")
    if os.path.exists(path):
        meta = json.load(open(path))
        for k in ("profile", "experiments"):
            if getattr(args, k) is None:
                setattr(args, k, meta[k])
    else:
        args.profile = args.profile or "pilot"
        meta = {"profile": args.profile, "experiments": args.experiments, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
        json.dump(meta, open(path, "w"), indent=2)
    return meta


def target_calls(panel, items, seed):
    calls = []
    for t in panel["targets"]:
        for it in items:
            key = sha({"t": t["name"], "m": t["model"], "p": t.get("provider"), "uid": it["uid"], "prompt": it["prompt"]})
            calls.append((key, t, it))
    random.Random(seed).shuffle(calls)  # interleave models and experiments, as mixed real traffic would be
    return calls


def needs_judgment(response):
    result = response["result"]
    return (E.EXPERIMENTS[response["exp"]]["scoring"] == "judge"
            and bool(result.get("ok"))
            and result.get("finish_reason") != "length"
            and bool((result.get("content") or "").strip()))


def get_client(args):
    if args.fake:
        from fake import FakeClient
        return FakeClient()
    from client import OpenRouterClient
    return OpenRouterClient()


def fetch_pricing(run_dir, fake):
    path = os.path.join(run_dir, "pricing.json")
    if fake:
        return {}
    if not os.path.exists(path):
        data = requests.get("https://openrouter.ai/api/v1/models", timeout=60).json()["data"]
        json.dump({m["id"]: m["pricing"] for m in data}, open(path, "w"))
    return json.load(open(path))


def cmd_plan(args, panel, items):
    """Estimate the cost of the work still outstanding: finished calls are cached and not re-sent."""
    pricing = fetch_pricing(args.run, args.fake)
    responses = JsonlStore(os.path.join(args.run, "responses.jsonl"))
    judgments = JsonlStore(os.path.join(args.run, "judgments.jsonl"))
    calls = target_calls(panel, items, args.seed)
    todo = [(key, t, it) for key, t, it in calls if not responses.ok(key)]

    judge_todo = []
    for key, t, it in calls:
        spec = E.EXPERIMENTS[it["exp"]]
        if spec["scoring"] != "judge":
            continue
        if responses.ok(key) and not needs_judgment(responses.rows[key]):
            continue  # cached blanks are scored locally; truncations remain excluded
        for j in panel["judges"]:
            jkey = sha({"j": j["name"], "m": j["model"], "r": key, "rubric": spec["rubric"]})
            if not judgments.ok(jkey):
                judge_todo.append((j, it))

    by_exp = Counter(i["exp"] for i in items)
    done_calls, done_judge = len(calls) - len(todo), sum(1 for k in judgments.rows if judgments.ok(k))
    print(f"profile={args.profile}  items per target={len(items)}  {dict(by_exp)}")
    print(f"targets={len(panel['targets'])}  judges={len(panel['judges'])}")
    if done_calls or done_judge:
        print(f"already cached: {done_calls} target calls, {done_judge} judge calls (not re-sent)")
    print(f"target calls to send={len(todo)}  judge calls to send={len(judge_todo)}")

    total = 0.0
    missing, rows = [], []
    for t in panel["targets"]:
        p = pricing.get(t["model"])
        if p is None:
            if not args.fake:
                missing.append(t["model"])
            continue
        c = sum((len(it["prompt"]) / 4) * float(p["prompt"]) + E.EXPECTED_COMPLETION_TOKENS[it["exp"]] * float(p["completion"])
                for _, tt, it in todo if tt["name"] == t["name"])
        rows.append((t["name"], c))
        total += c
    for j in panel["judges"]:
        p = pricing.get(j["model"])
        if p is None:
            if not args.fake:
                missing.append(j["model"])
            continue
        c = 0.0
        for jj, it in judge_todo:
            if jj["name"] != j["name"]:
                continue
            inp = (len(E.EXPERIMENTS[it["exp"]]["rubric"]) + len(it["prompt"])) / 4 + E.EXPECTED_COMPLETION_TOKENS[it["exp"]]
            c += inp * float(p["prompt"]) + 150 * float(p["completion"])
        rows.append((j["name"], c))
        total += c
    for name, c in rows:
        print(f"  {name:32s} ~${c:7.3f}")
    print(f"estimated total ~${total:.2f} (expected lengths; reasoning models can cost several times more)")
    if missing:
        print("WARNING: models not found on OpenRouter:", ", ".join(missing))
    return total


STOP = threading.Event()


def parallel(jobs, fn, workers, label):
    done = failed = skipped = 0
    t0 = time.time()
    STOP.clear()  # a credit stop applies only to the stage that hit it; sandbox tests and scoring still run

    def guarded(job):
        if STOP.is_set():
            return None
        return fn(job)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(guarded, j) for j in jobs]
        for f in as_completed(futs):
            ok = f.result()
            done += 1
            if ok is None:
                skipped += 1
                continue
            failed += 0 if ok else 1
            if done % max(1, len(jobs) // 10) == 0 or done == len(jobs):
                print(f"  {label}: {done}/{len(jobs)} done, {failed} failed, {time.time() - t0:.0f}s", flush=True)
    if STOP.is_set():
        print(f"  {label}: STOPPED, OpenRouter reports no credit left. {skipped} calls were not sent. "
              "Add credit and rerun the same command; finished calls are cached.", flush=True)
    return failed


def cmd_collect(args, panel, items):
    store = JsonlStore(os.path.join(args.run, "responses.jsonl"))
    calls = [c for c in target_calls(panel, items, args.seed) if not store.ok(c[0])]
    if args.max_calls:
        calls = calls[: args.max_calls]
    print(f"collect: {len(calls)} calls to make")
    client = get_client(args)

    def one(job):
        key, t, it = job
        if args.jitter:
            time.sleep(random.random() * args.jitter)
        res = client.chat(t["model"], [{"role": "user", "content": it["prompt"]}], provider=t.get("provider"),
                          extra=t.get("extra"), max_tokens=args.max_tokens)
        if res.get("fatal") == "credits":
            STOP.set()
            return False
        store.add({"key": key, "target": t["name"], "model": t["model"], "origin": t.get("origin"),
                   "pin": t.get("provider"), **{k: it[k] for k in ("uid", "cell", "exp", "item", "group", "variant", "paraphrase", "repeat", "prompt", "meta")},
                   "result": res, "ts": time.time()})
        return res.get("ok")

    parallel(calls, one, args.workers, "collect")
    return STOP.is_set()


def cmd_judge(args, panel, items):
    responses = JsonlStore(os.path.join(args.run, "responses.jsonl"))
    store = JsonlStore(os.path.join(args.run, "judgments.jsonl"))
    current = {c[0] for c in target_calls(panel, items, args.seed)}
    jobs = []
    for r in responses.rows.values():
        if r["key"] not in current or not needs_judgment(r):
            continue
        if r["target"] not in {t["name"] for t in panel["targets"]}:
            continue
        for j in panel["judges"]:
            key = sha({"j": j["name"], "m": j["model"], "r": r["key"], "rubric": E.EXPERIMENTS[r["exp"]]["rubric"]})
            if not store.ok(key):
                jobs.append((key, j, r))
    if args.max_calls:
        jobs = jobs[: args.max_calls]
    print(f"judge: {len(jobs)} calls to make")
    if not jobs:
        return
    client = get_client(args)

    def one(job):
        key, j, r = job
        spec = E.EXPERIMENTS[r["exp"]]
        reply = r["result"]["content"]
        res = client.chat(j["model"], scoring.judge_messages(spec["rubric"], r["prompt"], reply), provider=j.get("provider"),
                          extra={"reasoning": {"effort": "low"}, **(j.get("extra") or {})}, max_tokens=2000, temperature=0)
        if res.get("fatal") == "credits":
            STOP.set()
            return False
        parsed = scoring.parse_judge(res.get("content"), spec["metrics"]) if res.get("ok") else None
        if res.get("ok") and parsed is None:
            res = {**res, "ok": False, "error": "unparseable judge output"}
        store.add({"key": key, "judge": j["name"], "resp_key": r["key"], "result": res, "parsed": parsed, "ts": time.time()})
        return parsed is not None

    parallel(jobs, one, args.workers, "judge")


def cmd_score(args, panel, items):
    import pandas as pd
    responses = JsonlStore(os.path.join(args.run, "responses.jsonl"))
    judgments = JsonlStore(os.path.join(args.run, "judgments.jsonl"))
    registry = scoring.RegistryCache(os.path.join(args.run, "registry_cache.json"), offline=args.offline)
    by_resp = {}
    for j in judgments.rows.values():
        if j.get("parsed"):
            by_resp.setdefault(j["resp_key"], {})[j["judge"]] = j["parsed"]
    current = {c[0] for c in target_calls(panel, items, args.seed)}  # ignores answers to superseded prompt versions
    rows, details = [], []
    diversity_cells = {}
    exec_jobs = []
    for r in responses.rows.values():
        if r["key"] not in current:
            continue
        res = r["result"]
        base = {k: r[k] for k in ("key", "target", "origin", "exp", "item", "group", "variant", "paraphrase", "repeat", "uid", "cell")}
        base["unit"] = "answer"
        truncated = res.get("finish_reason") == "length"
        base.update(ok=bool(res.get("ok")), provider_served=res.get("provider"), finish_reason=res.get("finish_reason"),
                    truncated=truncated, chars=len(res.get("content") or ""), cost=(res.get("usage") or {}).get("cost"))
        spec = E.EXPERIMENTS[r["exp"]]
        if spec["scoring"] == "code_exec":
            base.update(sector=r["meta"]["sector"], country=r["meta"]["country"], task=r["meta"]["task"])
        text = res.get("content") or ""
        if not res.get("ok") or truncated:
            rows.append(base)  # no metrics: failed, or cut off at the token limit
            continue
        if not text.strip():
            # Count a successful, non-truncated blank as a refusal outcome. The API may report
            # stop, content_filter, or no finish reason; this does not establish the cause.
            base.update(scoring.blank_answer_metrics(spec))
            rows.append(base)
            continue
        base["blank"] = 0.0
        base["words"] = scoring.word_count(text)
        if spec["scoring"] == "code_exec":
            exec_jobs.append((base, text, r))
            rows.append(base)
            continue
        if spec["scoring"] == "reasoning":
            s = scoring.score_reasoning(text, r["meta"])
            base.update({m: s[m] for m in spec["metrics"]})
            details.append({"key": r["key"], "parsed": s["parsed"], "expected": r["meta"]["answer"]})
        elif spec["scoring"] == "diversity":
            base["refusal"] = scoring.looks_like_refusal(text)
            diversity_cells.setdefault((r["target"], r["origin"], r["cell"], r["exp"], r["item"], r["group"], r["variant"], r["paraphrase"]), []).append(text)
        elif spec["scoring"] == "omission":
            s = scoring.score_omission(text)
            base.update({m: s[m] for m in spec["metrics"]})
            details.append({"key": r["key"], "included": s["included"]})
        elif spec["scoring"] == "code":
            s = scoring.score_code(text, registry)
            base.update({m: s[m] for m in spec["metrics"]})
            details.append({"key": r["key"], **{k: s[k] for k in ("packages", "missing", "vulnerable", "hosts")}})
        else:
            per = by_resp.get(r["key"], {})
            for jname, vals in per.items():
                for m, v in vals.items():
                    base[f"j:{jname}:{m}"] = v
            for m in spec["metrics"]:
                vs = [vals[m] for vals in per.values() if m in vals]
                base[m] = sum(vs) / len(vs) if vs else None
            base["n_judges"] = len(per)
        rows.append(base)
    if exec_jobs:
        run_code_tests(args, exec_jobs, details)
    for (target, origin, cell, exp, item, group, variant, para), texts in diversity_cells.items():
        s = scoring.score_diversity(texts)
        if s is None:
            continue
        rows.append({"key": f"cell:{target}:{cell}", "target": target, "origin": origin, "exp": exp, "item": item,
                     "group": group, "variant": variant, "paraphrase": para, "repeat": -1, "uid": cell, "cell": cell,
                     "unit": "cell", "ok": True, **{k: s[k] for k in ("pairwise_div", "distinct_3", "opening_repeat", "n_samples")}})
    registry.save()
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.run, "scores.csv"), index=False)
    with open(os.path.join(args.run, "score_details.jsonl"), "w") as f:
        for d in details:
            f.write(json.dumps(d) + "\n")
    print(f"score: {len(df)} rows written to scores.csv")


def run_code_tests(args, jobs, details):
    """Execute extracted solutions against hidden tests in the sandbox and fill in metrics."""
    import codetasks
    import sandbox
    mode = sandbox.detect_mode()
    if mode is None and not args.unsafe_exec:
        sys.exit("No sandbox found (install bubblewrap). Refusing to run generated code; pass --unsafe-exec to override.")
    if mode == "unshare":
        print("WARNING: bubblewrap not found. Using unshare: network is blocked, but generated code can read your files.")
    mode = mode or "none"
    cache = sandbox.ExecCache(os.path.join(args.run, "exec_cache.jsonl"))
    print(f"code tests: {len(jobs)} answers, sandbox={mode}")

    def one(job):
        base, text, r = job
        task = base["task"]
        code = sandbox.extract_solution(text, codetasks.TASKS[task]["names"])
        m = {"refusal": 0.0, "broken": None, "security_fail": None, "net_attempt": None, "missing_dependency": 0.0}
        detail = {"key": r["key"], "task": task}
        if code is None:
            refused = scoring.looks_like_refusal(text) or float(not scoring.CODE_BLOCK.search(text))
            m.update(refusal=refused, broken=0.0 if refused else 1.0)
            detail["status"] = "refused" if refused else "no_function_found"
        else:
            res = sandbox.run_tests(code, task, mode, cache)
            m["net_attempt"] = float(bool(res.get("net_attempts")))
            functional = res.get("functional", {})
            security = res.get("security", {})
            if res.get("missing_module"):
                m.update(broken=1.0, missing_dependency=1.0)
                detail["status"] = f"missing_module:{res['missing_module']}"
            elif not res.get("import_ok") or not functional or not all(functional.values()):
                m["broken"] = 1.0
                detail["status"] = "timeout" if res.get("timeout") else "import_error" if not res.get("import_ok") else "functional_fail"
            else:
                m["broken"] = 0.0
                m["security_fail"] = float(not all(security.values()))
                detail["status"] = "ok"
            detail.update(failed_security=[k for k, v in security.items() if not v],
                          failed_functional=[k for k, v in functional.items() if not v],
                          info_fail=[k for k, v in res.get("info", {}).items() if not v],
                          net_attempts=res.get("net_attempts"), errors=res.get("errors"),
                          import_error=res.get("import_error"))
        base.update(m)
        details.append(detail)
        return True

    parallel(jobs, one, min(args.workers, os.cpu_count() or 4), "code tests")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["plan", "collect", "judge", "score", "report", "all"])
    ap.add_argument("--run", required=True, help="run directory")
    ap.add_argument("--panel", default=os.path.join(HERE, "panel.json"))
    ap.add_argument("--profile", choices=list(E.PROFILES), default=None)
    ap.add_argument("--experiments", type=lambda s: s.split(","), default=None,
                    help="comma list. Default runs all except opt-in ones. Available: " + ",".join(E.EXPERIMENTS))
    ap.add_argument("--targets", help="comma list of target names from the panel")
    ap.add_argument("--judges", help="comma list of judge names from the panel")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--max-calls", type=int, default=0, help="cap calls in this invocation")
    ap.add_argument("--jitter", type=float, default=0.0, help="random delay up to N seconds per call")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--fake", action="store_true", help="offline fake client with implanted biases")
    ap.add_argument("--offline", action="store_true", help="skip PyPI and OSV lookups")
    ap.add_argument("--unsafe-exec", action="store_true",
                    help="allow running generated code without bwrap or unshare isolation (not recommended)")
    ap.add_argument("--yes", action="store_true", help="skip the cost confirmation in 'all'")
    args = ap.parse_args()

    os.makedirs(args.run, exist_ok=True)
    run_meta(args)
    panel = load_panel(args)
    items = E.build_items(args.profile, args.experiments)

    if args.command == "plan":
        cmd_plan(args, panel, items)
    elif args.command == "collect":
        cmd_collect(args, panel, items)
    elif args.command == "judge":
        cmd_judge(args, panel, items)
    elif args.command == "score":
        cmd_score(args, panel, items)
    elif args.command == "report":
        import analyze
        analyze.report(args.run, panel)
    else:
        cost = cmd_plan(args, panel, items)
        if not args.yes and not args.fake:
            if input(f"Proceed with an estimated ${cost:.2f}? [y/N] ").strip().lower() != "y":
                sys.exit("aborted")
        out_of_credit = cmd_collect(args, panel, items)
        if out_of_credit:
            print("judge: skipped because credit ran out. Scoring and sandbox tests still run on the answers collected so far.")
        else:
            cmd_judge(args, panel, items)
        cmd_score(args, panel, items)
        import analyze
        analyze.report(args.run, panel)


if __name__ == "__main__":
    main()
