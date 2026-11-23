"""Second ground truth: damage of a recalculated-betweenness attacker.

A different attack principle than the degree-adaptive attacker used in
run_exp.py, so the metric-versus-truth comparison is not tied to one attack
rule.  Writes out/gt_betweenness.csv keyed by (family, n, seed).
"""
import argparse
import os
import sys
import time
import traceback
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402


def one(job):
    family, n, seed = job
    t0 = time.time()
    G = netlib.make(family, n, seed)
    order = netlib.order_adaptive_betweenness(G, k=50, seed=seed)
    b10, _ = netlib.attack_damage(G, order, budget=0.1, alpha=1.0)
    b20, kb = netlib.attack_damage(G, order, budget=0.2, alpha=1.0)
    return dict(family=family, n=n, seed=seed, B10=b10, B20=b20, kb=kb,
                secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/gt_betweenness.csv")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--sizes", default="500,1000,2000")
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()
    sizes = [int(s) for s in args.sizes.split(",")]
    families = list(netlib.FAMILIES)
    jobs = [(f, n, s) for f in families for n in sizes for s in range(args.seeds)]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    t0 = time.time()
    rows = []
    with Pool(args.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(one, jobs, chunksize=1), 1):
            rows.append(r)
            if i % 10 == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] {time.time()-t0:.1f}s", flush=True)
    pd.DataFrame(rows).sort_values(["family", "n", "seed"]).to_csv(args.out, index=False)
    print("DONE", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
