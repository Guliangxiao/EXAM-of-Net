"""Verify every number quoted in the paper against the experiment outputs.

Prints a checklist: what the paper claims, what the data says, and whether they
match.  Run on the server where the results live.
"""
import os
import sys

import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "analysis")


def check(label, claimed, actual, tol=0.0015):
    ok = abs(claimed - actual) <= tol
    print(f"{'OK ' if ok else 'MISMATCH'}  {label:52s} claim={claimed:+.3f} data={actual:+.3f}")
    return ok


def main():
    ok = True

    # ---- figure 1 values quoted in section 3 -------------------------------
    for fam, c_r0, c_r1 in [("ER-k4", 0.259, 0.399), ("BA-m2", 0.108, 0.352)]:
        G = netlib.make(fam, 1000, 0)
        order = netlib.order_degree(G)
        m, _ = netlib.curve(G, order, alphas=(0.0, 1.0))
        ok &= check(f"{fam} R0 (图1, N=1000 seed=0)", c_r0, m["R0"])
        ok &= check(f"{fam} R1 (图1, N=1000 seed=0)", c_r1, m["R1"])

    # ---- table 1 and headline correlations ---------------------------------
    tab = pd.read_csv(os.path.join(OUT, "metrics_vs_truth.csv"))
    deg = tab[tab.strategy == "degree"].set_index(["metric", "truth"])
    claims = [
        ("R0", "D20", -0.259), ("R0", "B20", -0.011), ("R0", "D_unif", -0.953),
        ("R05", "D20", -0.300), ("R05", "B20", -0.069), ("R05", "D_unif", -0.926),
        ("R1", "D20", -0.618), ("R1", "B20", -0.415), ("R1", "D_unif", -0.749),
        ("R2", "D20", -0.455), ("R2", "B20", -0.667), ("R2", "D_unif", 0.640),
    ]
    for m, t, c in claims:
        ok &= check(f"表1 {m} vs {t}", c, deg.loc[(m, t), "rho"])

    # ---- alpha scan --------------------------------------------------------
    scan = pd.read_csv(os.path.join(ROOT, "out", "alpha_scan_rho.csv")).set_index("alpha")
    for a, col, c in [(0.0, "D20", -0.259), (1.5, "D20", -0.769), (1.5, "B20", -0.873),
                      (1.5, "D10", -0.850), (1.5, "B10", -0.803), (3.0, "D_unif", 0.827),
                      (2.0, "D10", -0.708), (2.0, "B10", -0.778)]:
        ok &= check(f"α={a} vs {col}", c, scan.loc[a, col])

    # ---- robustness --------------------------------------------------------
    rob = pd.read_csv(os.path.join(OUT, "robustness.csv"))
    r1 = rob[(rob.metric == "R1") & (rob.truth == "D20")].iloc[0]
    r0 = rob[(rob.metric == "R0") & (rob.truth == "D20")].iloc[0]
    ok &= check("R1 留一族下界", -0.813, r1.loo_min)
    ok &= check("R1 留一族上界", -0.394, r1.loo_max)
    ok &= check("R0 留一族上界", 0.135, r0.loo_max)
    ok &= check("R1 偏相关", -0.227, r1.rho_partial)
    ok &= check("R0 偏相关", 0.287, r0.rho_partial)
    r2 = rob[(rob.metric == "R2") & (rob.truth == "D20")].iloc[0]
    ok &= check("R2 偏相关", -0.362, r2.rho_partial)

    # ---- rank shift and gap ------------------------------------------------
    full = pd.read_csv(os.path.join(ROOT, "out", "full.csv"))
    sub = full[full.strategy == "degree"]
    ok &= check("Kendall τ(R0,R1)", 0.659, stats.kendalltau(sub.R0, sub.R1).statistic)
    ok &= check("Kendall τ(R0,R2)", -0.356, stats.kendalltau(sub.R0, sub.R2).statistic)
    gap = pd.read_csv(os.path.join(OUT, "gap_vs_heterogeneity.csv"))
    ok &= check("gap-CV (degree)", 0.716, float(gap[gap.strategy == "degree"].rho.iloc[0]))
    ok &= check("gap-CV (betweenness)", 0.746, float(gap[gap.strategy == "betweenness"].rho.iloc[0]))

    # ---- within-group consistency -----------------------------------------
    grp = pd.read_csv(os.path.join(OUT, "group_consistency.csv"))
    better = int((grp.R1 < grp.R0).sum())
    print(f"INFO  组内: R1 更负的组数 {better}/{len(grp)} "
          f"(论文写 10/21), 中位 τ R0={grp.R0.median():+.3f} R1={grp.R1.median():+.3f} "
          f"R2={grp.R2.median():+.3f}")

    # ---- table 2: by family ------------------------------------------------
    byfam = pd.read_csv(os.path.join(OUT, "by_family_rho.csv")).set_index("family")
    fam_claims = [("PL-2.5", "R0", 0.357), ("PL-2.5", "R1", -0.746),
                  ("PL-3.0", "R0", 0.204), ("PL-3.0", "R1", -0.839),
                  ("BA-m3", "R0", 0.283), ("BA-m3", "R1", 0.246), ("BA-m3", "R2", -0.355),
                  ("ER-k6", "R1", 0.188), ("ER-k4", "R2", -0.204),
                  ("WS-k6", "R2", -0.165), ("BA-m2", "R0", 0.097)]
    for fam, m, c in fam_claims:
        ok &= check(f"表2 {fam} {m}", c, byfam.loc[fam, m])

    # ---- by size -----------------------------------------------------------
    bysize = pd.read_csv(os.path.join(OUT, "by_size.csv")).set_index("n")
    for n, c0, c1 in [(500, -0.297, -0.640), (1000, -0.252, -0.606), (2000, -0.236, -0.618)]:
        ok &= check(f"分规模 N={n} R0", c0, bysize.loc[n, "R0"])
        ok &= check(f"分规模 N={n} R1", c1, bysize.loc[n, "R1"])

    # ---- table 3: cascade calibration --------------------------------------
    cal = pd.read_csv(os.path.join(OUT, "cascade_calibration.csv")).set_index(["beta", "pct"])
    for (b, p), c in [((0.2, 0.01), 1.00), ((0.5, 0.01), 0.92), ((1.0, 0.01), 0.48),
                      ((1.0, 0.02), 0.57), ((2.0, 0.01), 0.01), ((2.0, 0.05), 0.42)]:
        ok &= check(f"表3 beta={b} pct={p}", c, cal.loc[(b, p), "mean"], tol=0.006)

    # ---- the counterexample in 6.7 ----------------------------------------
    pair = full[(full.family == "PL-3.0") & (full.n == 1000)
                & (full.strategy == "degree") & (full.seed.isin([0, 1]))].set_index("seed")
    for seed, vals in [(0, dict(R0=0.033, R1=0.183, D20=0.678, kmax=115, cv_k=1.78, k_cost=32)),
                       (1, dict(R0=0.046, R1=0.150, D20=0.947, kmax=39, cv_k=0.91, k_cost=70))]:
        for k, c in vals.items():
            ok &= check(f"6.7 seed={seed} {k}", c, pair.loc[seed, k], tol=0.006)

    # ---- network count -----------------------------------------------------
    print(f"INFO  网络数 {len(sub)}, 行数 {len(full)}")
    print("\nRESULT", "ALL MATCH" if ok else "HAS MISMATCHES")


if __name__ == "__main__":
    main()
