"""Batch experiment driver.

    python run_exp.py --out out/results.csv --workers 32 [--sizes 500,1000,2000] [--seeds 5]

Per (family, size, seed) network we compute
  * metric values on three fixed attack orderings (random / degree / betweenness),
  * an independent ground truth: the connectivity damage actually inflicted by a
    recalculated-degree attacker (it never uses the metric) at 10% and 20% of the
    total degree-cost budget, plus 20% of the node budget (the classic setting),
  * structural descriptors used in the discussion (heterogeneity, assortativity,
    clustering), so the paper can explain *when* the classic metric fails.
"""
import argparse
import json
import os
import sys
import time
import traceback
from multiprocessing import Pool

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402

ALPHAS = (0.0, 0.5, 1.0, 2.0)
BUDGET = 0.2


def structure(G):
    deg = np.array([d for _, d in G.degree()], dtype=float)
    feat = dict(mean_k=float(deg.mean()), kmax=float(deg.max()),
                cv_k=float(deg.std() / max(deg.mean(), 1e-9)))
    try:
        feat["assort"] = float(nx.degree_assortativity_coefficient(G))
    except Exception:
        feat["assort"] = float("nan")
    try:
        feat["clust"] = float(nx.average_clustering(G))
    except Exception:
        feat["clust"] = float("nan")
    return feat


def one(job):
    family, n, seed = job
    t0 = time.time()
    G = netlib.make(family, n, seed)
    feat = structure(G)

    gt_order = netlib.GROUND_TRUTH_ATTACK(G)
    d10, k10 = netlib.attack_damage(G, gt_order, budget=0.1, alpha=1.0)
    d20, k20 = netlib.attack_damage(G, gt_order, budget=BUDGET, alpha=1.0)
    u20, u20k = netlib.attack_damage(G, gt_order, budget=BUDGET, alpha=0.0)

    rows = []
    for strategy in ("random", "degree", "betweenness"):
        fn = netlib.STRATEGIES[strategy]
        order = fn(G, seed=seed) if strategy == "random" else fn(G)
        metrics, _ = netlib.curve(G, order, alphas=ALPHAS)
        row = dict(family=family, n=n, seed=seed, strategy=strategy,
                   nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                   R0=metrics["R0"], R05=metrics["R0.5"],
                   R1=metrics["R1"], R2=metrics["R2"],
                   q50=metrics["q50_0"], c50=metrics["c50_1"],
                   D10=d10, D20=d20, D_unif=u20, k_cost=k20, k_nodes=u20k,
                   secs=time.time() - t0)
        row.update(feat)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/results.csv")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--sizes", default="500,1000,2000")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--families", default=",".join(netlib.FAMILIES))
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    families = args.families.split(",")
    jobs = [(f, n, s) for f in families for n in sizes for s in range(args.seeds)]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    t0 = time.time()
    rows = []
    with Pool(args.workers) as pool:
        for i, res in enumerate(pool.imap_unordered(one, jobs, chunksize=1), 1):
            rows.extend(res)
            if i % 10 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] {time.time()-t0:.1f}s", flush=True)
    df = pd.DataFrame(rows).sort_values(["family", "n", "seed", "strategy"])
    df.to_csv(args.out, index=False)
    meta = dict(networks=len(jobs), rows=len(df), workers=args.workers, sizes=sizes,
                seeds=args.seeds, families=families, budget=BUDGET,
                alphas=list(ALPHAS), seconds=round(time.time() - t0, 1), out=args.out)
    with open(os.path.splitext(args.out)[0] + "_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    print("DONE", json.dumps(meta), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
