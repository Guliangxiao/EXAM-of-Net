"""Alpha scan: how the predictive quality of R_alpha depends on alpha.

    python exp_alpha.py --csv out/full.csv --gt2 out/gt_betweenness.csv --out out/alpha_scan.csv

For the same 105 networks and the degree ordering, it computes R_alpha on a grid
of alpha and correlates each with the three ground truths.  This turns the
"which alpha should I use" question into a measured curve instead of a choice.
"""
import argparse
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402

GRID = (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def one(job):
    family, n, seed = job
    G = netlib.make(family, n, seed)
    order = netlib.order_degree(G)
    metrics, _ = netlib.curve(G, order, alphas=GRID)
    return [dict(family=family, n=n, seed=seed, alpha=a, R=metrics[f"R{a:g}"]) for a in GRID]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="out/full.csv")
    ap.add_argument("--gt2", default="out/gt_betweenness.csv")
    ap.add_argument("--out", default="out/alpha_scan.csv")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    rows = []
    jobs = [(f, n, s) for f in netlib.FAMILIES for n in (500, 1000, 2000) for s in range(5)]
    with Pool(args.workers) as pool:
        for res in pool.imap_unordered(one, jobs, chunksize=1):
            rows.extend(res)
    scan = pd.DataFrame(rows).sort_values(["family", "n", "seed", "alpha"])
    scan.to_csv(args.out, index=False)

    df = pd.read_csv(args.csv)
    df = df[df.strategy == "degree"][["family", "n", "seed", "D20", "D10", "D_unif"]]
    gt2 = pd.read_csv(args.gt2)[["family", "n", "seed", "B20", "B10"]]
    df = df.merge(gt2, on=["family", "n", "seed"]).merge(
        scan, on=["family", "n", "seed"])

    out = []
    for a, g in df.groupby("alpha"):
        rec = dict(alpha=a)
        for t in ("D20", "B20", "D_unif", "D10", "B10"):
            rec[t] = stats.spearmanr(g.R, g[t]).statistic
        out.append(rec)
    tab = pd.DataFrame(out)
    tab.to_csv(os.path.splitext(args.out)[0] + "_rho.csv", index=False)
    print(tab.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
