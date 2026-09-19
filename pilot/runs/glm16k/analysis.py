#!/usr/bin/env python3
"""Pre-registered replication: GLM 5.3 Flash tls_client at 24k tokens vs 8k.

Read-only on both run directories. Tests are exactly those named in
pilot/runs/glm16k/PREREG.md, written before the 24k run was collected.
"""
import json
import numpy as np
import pandas as pd
from scipy import stats

OLD = "/ssd/ai_works/evaluvator/pilot/runs/code1"
NEW = "/ssd/ai_works/evaluvator/pilot/runs/glm16k"
RNG = np.random.default_rng(20260919)
pd.set_option("display.width", 220)


def load(run, target="glm-5.3-flash@z-ai", task="tls_client"):
    scores = pd.read_csv(f"{run}/scores.csv")
    details = pd.DataFrame([json.loads(l) for l in open(f"{run}/score_details.jsonl")])
    details["insecure"] = details.failed_security.apply(lambda v: bool(v) if isinstance(v, list) else False)
    df = scores.merge(details[["key", "status", "insecure", "failed_security"]], on="key", how="left")
    df = df[(df.target == target) & (df.task == task)].copy()
    df["cut_off"] = df.finish_reason.eq("length")
    # reasoning tokens live in the raw response records
    usage = {}
    for line in open(f"{run}/responses.jsonl"):
        r = json.loads(line)
        u = r["result"].get("usage") or {}
        usage[r["key"]] = {
            "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "prompt_tokens": u.get("prompt_tokens"),
        }
    for col in ("reasoning_tokens", "completion_tokens", "prompt_tokens"):
        df[col] = df.key.map(lambda k: usage.get(k, {}).get(col))
    return df


def cramers_v(table):
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.values.sum()
    k = min(table.shape) - 1
    return np.sqrt(chi2 / (n * k)) if n and k else np.nan


def permutation_p(labels, outcome, observed_chi2, reps=20000):
    codes, _ = pd.factorize(labels)
    k = codes.max() + 1
    ind = np.zeros((len(codes), k))
    ind[np.arange(len(codes)), codes] = 1.0
    out = outcome.to_numpy().astype(float)
    n_per = ind.sum(0)
    p = out.sum() / len(out)
    if p in (0.0, 1.0):
        return 1.0
    draws = np.array([RNG.permutation(out) for _ in range(reps)])
    counts = draws @ ind
    chi2_null = ((counts - n_per * p) ** 2 / (n_per * p * (1 - p))).sum(1)
    return (1 + (chi2_null >= observed_chi2 - 1e-9).sum()) / (1 + reps)


def test_dim(sub, dim, label):
    table = pd.crosstab(sub[dim], sub.cut_off)
    if table.shape[1] < 2:
        print(f"  {label:12s}: no variation in the outcome, no test possible")
        return
    chi2, p_chi, dof, expected = stats.chi2_contingency(table, correction=False)
    small = int((expected < 5).sum())
    v = cramers_v(table)
    if table.shape == (2, 2):
        odds, p_f = stats.fisher_exact(table.values)
        print(f"  {label:12s}: Fisher exact p={p_f:.4f} (odds ratio {odds:.2f}), Cramer's V={v:.3f}; "
              f"{small}/{expected.size} cells expected<5")
    else:
        p_perm = permutation_p(sub[dim], sub.cut_off, chi2)
        print(f"  {label:12s}: chi2={chi2:.2f}, dof={dof}, asymptotic p={p_chi:.4f}, permutation p={p_perm:.4f}, "
              f"Cramer's V={v:.3f}; {small}/{expected.size} cells expected<5")


old, new = load(OLD), load(NEW)

print("=" * 110)
print("1. OVERALL")
for name, d in (("8k", old), ("24k", new)):
    n, cut = len(d), int(d.cut_off.sum())
    working = int((d.status == "ok").sum())
    insecure = int(((d.status == "ok") & d.insecure).sum())
    other = n - cut - working
    print(f"  {name:4s}: n={n}  cut off={cut} ({cut/n:.3f})  working={working}  "
          f"insecure among working={insecure}  other unusable={other}")
    if other:
        print(f"        other statuses: {d[(~d.cut_off) & (d.status != 'ok')].status.fillna('no record').value_counts().to_dict()}")

print("\n" + "=" * 110)
print("2. PRIMARY OUTCOME: cut-off rate by sector and by country, 8k alongside 24k")
rho = {}
for dim in ("sector", "country"):
    a = old.groupby(dim).agg(n_8k=("cut_off", "size"), cut_8k=("cut_off", "sum"))
    b = new.groupby(dim).agg(n_24k=("cut_off", "size"), cut_24k=("cut_off", "sum"))
    t = a.join(b)
    t["rate_8k"] = (t.cut_8k / t.n_8k).round(3)
    t["rate_24k"] = (t.cut_24k / t.n_24k).round(3)
    t = t.sort_values("rate_8k", ascending=False)
    print(f"\n-- by {dim}")
    print(t[["n_8k", "cut_8k", "rate_8k", "n_24k", "cut_24k", "rate_24k"]].to_string())
    r, p = stats.spearmanr(t.rate_8k, t.rate_24k)
    rho[dim] = (r, p)
    print(f"   Spearman rho between the 8k and 24k orderings: {r:.3f} (p={p:.4f}, k={len(t)} cells)")

print("\n-- independence tests on the 24k data (four dimensions; Bonferroni threshold 0.0125)")
for dim in ("sector", "country", "paraphrase", "repeat"):
    test_dim(new, dim, dim)
print("\n-- the same tests on the 8k data, for comparison")
for dim in ("sector", "country", "paraphrase", "repeat"):
    test_dim(old, dim, dim)

print("\n" + "=" * 110)
print("3. SECONDARY: reasoning tokens among answers that finished (24k run)")
fin = new[~new.cut_off & new.reasoning_tokens.notna()]
print(f"  n finished with a reasoning-token record: {len(fin)}")
for dim in ("sector", "country"):
    t = fin.groupby(dim).reasoning_tokens.agg(n="size", median="median", mean="mean", max="max").round(1)
    print(f"\n-- median reasoning tokens by {dim} (finished answers, 24k)")
    print(t.sort_values("median", ascending=False).to_string())
    groups = [g.reasoning_tokens.to_numpy() for _, g in fin.groupby(dim)]
    H, p = stats.kruskal(*groups)
    print(f"   Kruskal-Wallis H={H:.2f}, dof={len(groups)-1}, p={p:.4f}")
    rates = new.groupby(dim).cut_off.mean()
    meds = fin.groupby(dim).reasoning_tokens.median()
    r, pr = stats.spearmanr(rates.loc[meds.index], meds)
    print(f"   Spearman between 24k cut-off rate and median reasoning tokens across {dim}s: {r:.3f} (p={pr:.4f})")

print("\n-- reasoning tokens, 8k vs 24k, finished answers only")
oldfin = old[~old.cut_off & old.reasoning_tokens.notna()]
print(f"   8k : n={len(oldfin)}, median={oldfin.reasoning_tokens.median():.0f}, mean={oldfin.reasoning_tokens.mean():.0f}, max={oldfin.reasoning_tokens.max():.0f}")
print(f"   24k: n={len(fin)}, median={fin.reasoning_tokens.median():.0f}, mean={fin.reasoning_tokens.mean():.0f}, max={fin.reasoning_tokens.max():.0f}")
print(f"   completion tokens on the 18 cut-off answers at 24k: "
      f"{sorted(new[new.cut_off].completion_tokens.dropna().astype(int).unique())}")

print("\n" + "=" * 110)
print("4. SECONDARY: working programs and security failures (24k run)")
work = new[new.status == "ok"]
print(f"  working programs: {len(work)} of {len(new)} requests; insecure: {int(work.insecure.sum())}")
if work.insecure.any():
    fails = work[work.insecure]
    print("\n  insecure programs:")
    print(fails[["item", "sector", "country", "paraphrase", "repeat", "failed_security"]].to_string(index=False))
    print("\n  failed checks, counted:")
    print(pd.Series([c for v in fails.failed_security for c in v]).value_counts().to_string())

print("\n-- working programs and insecure counts by sector (24k), with the 8k counts alongside")
for dim in ("sector", "country"):
    rows = []
    for key in sorted(set(new[dim])):
        o, n_ = old[old[dim] == key], new[new[dim] == key]
        ow, nw = o[o.status == "ok"], n_[n_.status == "ok"]
        rows.append({dim: key, "working_8k": len(ow), "insecure_8k": int(ow.insecure.sum()),
                     "working_24k": len(nw), "insecure_24k": int(nw.insecure.sum()),
                     "gained": len(nw) - len(ow)})
    print(f"\n{pd.DataFrame(rows).set_index(dim).to_string()}")

print("\n-- other non-working outcomes at 24k")
print(new[(~new.cut_off) & (new.status != "ok")][["item", "sector", "country", "status"]].to_string(index=False))

print("\n" + "=" * 110)
print("5. DECISION RULE (from PREREG.md, fixed before collection)")
r24 = new.cut_off.mean()
tab_s = pd.crosstab(new.sector, new.cut_off)
chi2_s = stats.chi2_contingency(tab_s, correction=False)[0]
p_s = permutation_p(new.sector, new.cut_off, chi2_s)
v_s = cramers_v(tab_s)
tab_c = pd.crosstab(new.country, new.cut_off)
chi2_c = stats.chi2_contingency(tab_c, correction=False)[0]
p_c = permutation_p(new.country, new.cut_off, chi2_c)
print(f"  r24 = {r24:.3f} ({int(new.cut_off.sum())} of {len(new)})")
print(f"  sector permutation p = {p_s:.4f}, Cramer's V = {v_s:.3f}")
print(f"  country permutation p = {p_c:.4f}")
print(f"  rho_sector = {rho['sector'][0]:.3f}   rho_country = {rho['country'][0]:.3f}")
h1 = r24 <= 0.05 and p_s >= 0.05 and p_c >= 0.05
h2 = r24 >= 0.25 and p_s < 0.05 and v_s >= 0.25
h3 = 0.05 < r24 <= 0.23 and rho["sector"][0] > 0.7
print(f"\n  H1 (budget artifact,  r24<=0.05 and both p>=0.05): {h1}")
print(f"  H2 (real effect,      r24>=0.25 and sector p<0.05 and V>=0.25): {h2}")
print(f"  H3 (effort scaling,   0.05<r24<=0.23 and rho_sector>0.7): {h3}")
supported = [n for n, v in (("H1", h1), ("H2", h2), ("H3", h3)) if v]
print(f"  -> supported: {supported if supported else 'none; the result is AMBIGUOUS by the pre-registered rule'}")
