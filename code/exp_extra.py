"""Extra statistics needed for the expanded paper.

Prints (and saves) the breakdowns that were only mentioned in passing:
  * rho by network size (does the metric ranking hold at every N?)
  * rho by network family (already in by_family.csv, recomputed here for one table)
  * the cascade calibration table that justifies dropping the cascade criterion
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")


def main():
    df = pd.read_csv(os.path.join(OUT, "full.csv"))
    sub = df[df.strategy == "degree"]
    metrics = ["R0", "R1", "R2"]

    print("== rho vs D20, by size ==")
    rows = []
    for n, g in sub.groupby("n"):
        rec = dict(n=n, nets=len(g))
        for m in metrics:
            rec[m] = round(stats.spearmanr(g[m], g.D20).statistic, 3)
        rows.append(rec)
    bysize = pd.DataFrame(rows)
    print(bysize.to_string(index=False))
    bysize.to_csv(os.path.join(OUT, "analysis", "by_size.csv"), index=False)

    print("\n== rho vs D20, by family ==")
    rows = []
    for fam, g in sub.groupby("family"):
        rec = dict(family=fam, nets=len(g))
        for m in metrics:
            rec[m] = round(stats.spearmanr(g[m], g.D20).statistic, 3)
        rows.append(rec)
    byfam = pd.DataFrame(rows)
    print(byfam.to_string(index=False))
    byfam.to_csv(os.path.join(OUT, "analysis", "by_family_rho.csv"), index=False)

    # ---- cascade calibration -------------------------------------------
    print("\n== cascade calibration: mean damage, 3 seeds ==")
    fams = ["ER-k4", "BA-m2", "WS-k6", "PL-2.5"]
    rows = []
    for beta in (0.2, 0.5, 1.0, 2.0):
        for pct in (0.01, 0.02, 0.05):
            vals = {f: [] for f in fams}
            for fam in fams:
                for seed in range(3):
                    G = netlib.make(fam, 500, seed)
                    order = netlib.order_degree(G)
                    k = max(1, int(round(pct * G.number_of_nodes())))
                    failed = netlib.cascade(G, set(order[:k]), beta=beta, k=100, seed=seed)
                    vals[fam].append(len(failed) / G.number_of_nodes())
            rec = dict(beta=beta, pct=pct)
            for fam in fams:
                rec[fam] = round(float(np.mean(vals[fam])), 2)
            rec["mean"] = round(float(np.mean([v for f in fams for v in vals[f]])), 2)
            rows.append(rec)
    calib = pd.DataFrame(rows)
    print(calib.to_string(index=False))
    calib.to_csv(os.path.join(OUT, "analysis", "cascade_calibration.csv"), index=False)


if __name__ == "__main__":
    main()
