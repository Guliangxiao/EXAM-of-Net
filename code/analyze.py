"""Statistical analysis of the batch results.

    python analyze.py --csv out/full.csv --gt2 out/gt_betweenness.csv --outdir out/analysis

The pooled Spearman correlation across 105 networks is the headline number, but
it can be driven by between-family differences.  So this script also reports
  * leave-one-family-out correlations (sign stability),
  * partial correlations controlling for family (within-family signal),
  * within-(family,size) rank agreement (the fine-grained regime),
and it is the *negative* correlation that counts as correct, because a more
robust network should suffer less damage.
"""
import argparse
import os

import numpy as np
import pandas as pd
from scipy import stats

METRICS = ["R0", "R05", "R1", "R2"]
TRUTHS = ["D20", "D10", "D_unif", "B20", "B10"]


def boot_rho(x, y, n_boot=2000, seed=0):
    rho, p = stats.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    n = len(x)
    vals = []
    for _ in range(n_boot):
        ii = rng.integers(0, n, n)
        r = stats.spearmanr(np.asarray(x)[ii], np.asarray(y)[ii]).statistic
        if np.isfinite(r):
            vals.append(r)
    lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan)
    return rho, p, lo, hi


def partial_spearman(df, metric, truth, group="family"):
    """Spearman correlation after removing group means from the rank scores."""
    r = df[[metric, truth]].rank()
    dummies = pd.get_dummies(df[group], drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(df)), dummies.to_numpy()])
    rx = r[metric].to_numpy()
    ry = r[truth].to_numpy()
    ex = rx - X @ np.linalg.lstsq(X, rx, rcond=None)[0]
    ey = ry - X @ np.linalg.lstsq(X, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="out/full.csv")
    ap.add_argument("--gt2", default="out/gt_betweenness.csv")
    ap.add_argument("--outdir", default="out/analysis")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.csv)
    if os.path.exists(args.gt2):
        gt2 = pd.read_csv(args.gt2)[["family", "n", "seed", "B10", "B20", "kb"]]
        df = df.merge(gt2, on=["family", "n", "seed"], how="left")
    truths = [t for t in TRUTHS if t in df.columns]
    sub = df[df.strategy == "degree"].reset_index(drop=True)

    # ---- 1. pooled correlation ------------------------------------------
    recs = []
    for strat in sorted(df.strategy.unique()):
        s = df[df.strategy == strat]
        for m in METRICS:
            for t in truths:
                rho, p, lo, hi = boot_rho(s[m].to_numpy(), s[t].to_numpy())
                recs.append(dict(strategy=strat, metric=m, truth=t, n=len(s),
                                 rho=rho, p=p, ci_lo=lo, ci_hi=hi))
    tab = pd.DataFrame(recs)
    tab.to_csv(os.path.join(args.outdir, "metrics_vs_truth.csv"), index=False)

    # ---- 2. robustness: leave one family out + partial -------------------
    rob = []
    for m in METRICS:
        for t in truths:
            loo = [stats.spearmanr(g[m], g[t]).statistic
                   for _, g in sub.groupby("family") if len(g) > 3]
            vals = []
            for fam in sub.family.unique():
                g = sub[sub.family != fam]
                vals.append(stats.spearmanr(g[m], g[t]).statistic)
            rob.append(dict(metric=m, truth=t,
                            rho_pooled=stats.spearmanr(sub[m], sub[t]).statistic,
                            rho_within_median=float(np.nanmedian(loo)),
                            rho_partial=partial_spearman(sub, m, t),
                            loo_min=float(np.nanmin(vals)),
                            loo_max=float(np.nanmax(vals))))
    pd.DataFrame(rob).to_csv(os.path.join(args.outdir, "robustness.csv"), index=False)

    # ---- 3. within-group ranking agreement (fine-grained regime) --------
    groups = []
    for (fam, n), g in sub.groupby(["family", "n"]):
        if len(g) < 4:
            continue
        rec = dict(family=fam, n=n, size=len(g))
        for m in METRICS:
            rec[m] = stats.kendalltau(g[m], g.D20).statistic
        groups.append(rec)
    grp = pd.DataFrame(groups)
    grp.to_csv(os.path.join(args.outdir, "group_consistency.csv"), index=False)

    # ---- 4. gap vs heterogeneity ----------------------------------------
    gap = []
    for strat in ("degree", "betweenness"):
        g = df[df.strategy == strat]
        rho, p = stats.spearmanr(g.R1 - g.R0, g.cv_k)
        gap.append(dict(strategy=strat, rho=rho, p=p, n=len(g)))
    pd.DataFrame(gap).to_csv(os.path.join(args.outdir, "gap_vs_heterogeneity.csv"),
                             index=False)

    # ---- 5. rank shift ---------------------------------------------------
    alltau = {m: stats.kendalltau(sub.R0, sub[m]).statistic for m in METRICS[1:]}

    # ---- summary ---------------------------------------------------------
    print("== networks ==", len(sub))
    print("\n== Spearman(metric, truth): negative rho = metric correctly reflects damage ==")
    print(tab[tab.strategy == "degree"].pivot_table(index="truth", columns="metric",
                                                    values="rho").round(3).to_string())
    print("\n== robustness of (degree ordering, D20) ==")
    print(pd.DataFrame(rob).query("truth=='D20'").round(3).to_string(index=False))
    print("\n== within (family,size) Kendall tau vs D20 (negative = correct) ==")
    print(grp[METRICS].agg(["mean", "median", "std"]).round(3).to_string())
    better = (grp.R1 < grp.R0)
    print(f"R1 more negative than R0 in {better.sum()}/{len(grp)} groups; "
          f"sign test p={stats.binomtest(int(better.sum()), len(grp), 0.5).pvalue:.4g}")
    print("\n== Kendall tau between metric rankings (degree) ==")
    print({k: round(v, 3) for k, v in alltau.items()})
    print("\n== gap (R1-R0) vs degree CV ==")
    print(pd.DataFrame(gap).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
