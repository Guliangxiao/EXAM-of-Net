"""Figures for the paper.

    python figs.py --csv out/full.csv --analysis out/analysis --outdir out/figs

Four figures, single-column width (~3.4 in), 300 dpi, PNG + PDF:
  fig1_curves  largest-component fraction vs normalised attack cost, classic vs
               degree-cost, for one ER and one BA network
  fig2_rank    R_0 vs R_1 across all 105 networks (ranking reshuffle)
  fig3_corr    Spearman rho of each metric against each ground truth
  fig4_alpha   rho of R_alpha against each ground truth as alpha varies
"""
import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlib  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 7.5,
    "legend.fontsize": 6.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.linewidth": 0.6,
})

FAMILY_COLOR = {
    "ER-k4": "#4C78A8", "ER-k6": "#9ECAE9",
    "BA-m2": "#E45756", "BA-m3": "#F2A6A4",
    "WS-k6": "#54A24B", "PL-2.5": "#B279A2", "PL-3.0": "#7B4B94",
}


def curve_with_cost(G, order, alpha):
    n = G.number_of_nodes()
    deg = dict(G.degree())
    H = G.copy()
    frac = np.empty(n + 1)
    frac[0] = 1.0
    for i, v in enumerate(order, start=1):
        H.remove_node(v)
        frac[i] = max(len(c) for c in nx.connected_components(H)) / n if H.number_of_nodes() else 0.0
    w = np.array([max(deg[v], 1) ** alpha for v in order], float)
    return frac, np.concatenate(([0.0], np.cumsum(w))) / w.sum()


def fig_curves(path):
    fig, axes = plt.subplots(2, 1, figsize=(3.3, 4.3), sharex=True)
    for ax, fam in zip(axes, ["ER-k4", "BA-m2"]):
        G = netlib.make(fam, 1000, 0)
        order = netlib.order_degree(G)
        for alpha, style, lab in [(0.0, "--", "Classic $R_0$ (equal cost)"),
                                  (1.0, "-", "Cost-weighted $R_1$ ($w\\propto k$)")]:
            frac, cn = curve_with_cost(G, order, alpha)
            ax.plot(cn, frac, style, lw=1.2, color="#4C78A8" if alpha == 0 else "#E45756", label=lab)
        ax.set_ylabel("Largest component fraction $S$")
        ax.set_title(f"{fam} (N=1000, degree attack)")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.legend(frameon=False, loc="upper right")
        ax.grid(alpha=0.25, lw=0.4)
    axes[1].set_xlabel("Normalized cumulative attack cost")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_rank(sub, path):
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    for fam, g in sub.groupby("family"):
        ax.scatter(g.R0, g.R1, s=12, alpha=0.85, lw=0,
                   color=FAMILY_COLOR.get(fam, "gray"), label=fam)
    ax.set_xlabel("Classic $R_0$")
    ax.set_ylabel("Cost-weighted $R_1$")
    ax.grid(alpha=0.25, lw=0.4)
    ax.legend(frameon=False, fontsize=5.5, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.22), handletextpad=0.3, columnspacing=0.9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_corr(tab, path):
    metrics = ["R0", "R05", "R1", "R2"]
    truths = ["D20", "B20", "D_unif"]
    labels = {"D20": "Adaptive degree (cost 20%)",
              "B20": "Adaptive betweenness (cost 20%)",
              "D_unif": "Equal cost (nodes 20%)"}
    colors = {"D20": "#4C78A8", "B20": "#E45756", "D_unif": "#54A24B"}
    sub = tab[tab.strategy == "degree"]
    x = np.arange(len(metrics))
    w = 0.26
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for i, t in enumerate(truths):
        vals = [sub[(sub.metric == m) & (sub.truth == t)].rho.iloc[0] for m in metrics]
        ax.bar(x + (i - 1) * w, vals, w, label=labels[t], color=colors[t],
               edgecolor="white", lw=0.4)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(["$R_0$", "$R_{0.5}$", "$R_1$", "$R_2$"])
    ax.set_ylabel("Spearman $\\rho$ vs. actual damage")
    ax.set_ylim(-1.05, 1.18)
    ax.legend(frameon=False, fontsize=5.5, loc="upper left", handlelength=1.2,
              borderaxespad=0.2)
    ax.grid(axis="y", alpha=0.25, lw=0.4)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_alpha(path, csv):
    tab = pd.read_csv(csv)
    style = {"D20": ("-o", "#4C78A8", "Adaptive degree (cost 20%)"),
             "B20": ("-s", "#E45756", "Adaptive betweenness (cost 20%)"),
             "D_unif": ("-^", "#54A24B", "Equal cost (nodes 20%)")}
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    for t, (mk, c, lab) in style.items():
        ax.plot(tab.alpha, tab[t], mk, ms=3, lw=1.0, color=c, label=lab)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xlabel("Cost exponent $\\alpha$")
    ax.set_ylabel("与真实损伤的 Spearman $\\rho$")
    ax.set_ylim(-1.0, 1.15)
    ax.grid(alpha=0.25, lw=0.4)
    ax.legend(frameon=False, fontsize=5.5, loc="upper left", handlelength=1.2,
              borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="out/full.csv")
    ap.add_argument("--analysis", default="out/analysis")
    ap.add_argument("--alpha-csv", default="out/alpha_scan_rho.csv")
    ap.add_argument("--outdir", default="out/figs")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.csv)
    sub = df[df.strategy == "degree"]
    tab = pd.read_csv(os.path.join(args.analysis, "metrics_vs_truth.csv"))

    jobs = [("fig1_curves", lambda p: fig_curves(p)),
            ("fig2_rank", lambda p: fig_rank(sub, p)),
            ("fig3_corr", lambda p: fig_corr(tab, p)),
            ("fig4_alpha", lambda p: fig_alpha(p, args.alpha_csv))]
    for name, fn in jobs:
        for ext in ("png", "pdf"):
            fn(os.path.join(args.outdir, f"{name}.{ext}"))
        print("wrote", name, flush=True)


if __name__ == "__main__":
    main()
