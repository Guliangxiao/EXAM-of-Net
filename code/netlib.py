"""Core library for the robustness-metric paper.

Contents
--------
* network generators (ER / BA / WS / power-law configuration model, plus real topologies)
* attack orderings (random, degree, betweenness)
* robustness metrics: classic R (equal cost) and the cost-weighted family R_alpha
* Motter-Lai load-redistribution cascade, used as an *independent* ground truth of damage

Everything here is deterministic given (family, n, seed).
"""
from collections import deque

import networkx as nx
import numpy as np

# --------------------------------------------------------------------------
# generators
# --------------------------------------------------------------------------


def _giant(G):
    """Keep the largest connected component and relabel to 0..n-1."""
    if G.number_of_nodes() == 0:
        return G
    if nx.is_connected(G):
        return nx.convert_node_labels_to_integers(G, first_label=0)
    comp = max(nx.connected_components(G), key=len)
    return nx.convert_node_labels_to_integers(G.subgraph(comp).copy(), first_label=0)


def gen_er(n, k, seed):
    return _giant(nx.gnm_random_graph(n, int(round(n * k / 2.0)), seed=seed))


def gen_ba(n, m, seed):
    return _giant(nx.barabasi_albert_graph(n, m, seed=seed))


def gen_ws(n, k, p, seed):
    return _giant(nx.watts_strogatz_graph(n, k, p, seed=seed))


def gen_pl(n, gamma, seed):
    """Configuration model with a power-law degree sequence, min degree 2."""
    rng = np.random.default_rng(seed)
    seq = nx.utils.powerlaw_sequence(n, exponent=gamma, seed=int(rng.integers(1 << 30)))
    seq = [max(2, int(round(x))) for x in seq]
    if sum(seq) % 2:
        seq[0] += 1
    G = nx.configuration_model(seq, seed=seed)
    G = nx.Graph(G)
    G.remove_edges_from(nx.selfloop_edges(G))
    return _giant(G)


GEN = {
    "er": gen_er,
    "ba": gen_ba,
    "ws": gen_ws,
    "pl": gen_pl,
}

FAMILIES = {
    "ER-k4": ("er", dict(k=4)),
    "ER-k6": ("er", dict(k=6)),
    "BA-m2": ("ba", dict(m=2)),
    "BA-m3": ("ba", dict(m=3)),
    "WS-k6": ("ws", dict(k=6, p=0.1)),
    "PL-2.5": ("pl", dict(gamma=2.5)),
    "PL-3.0": ("pl", dict(gamma=3.0)),
}


def make(family, n, seed):
    kind, kw = FAMILIES[family]
    return GEN[kind](n, seed=seed, **kw)


# --------------------------------------------------------------------------
# attack orderings  (a strategy returns the FULL removal sequence)
# --------------------------------------------------------------------------


def order_random(G, seed=0):
    nodes = list(G.nodes())
    np.random.default_rng(seed).shuffle(nodes)
    return nodes


def order_degree(G):
    return [v for v, _ in sorted(G.degree(), key=lambda x: (-x[1], x[0]))]


def order_betweenness(G, k=100, seed=0):
    n = G.number_of_nodes()
    bc = nx.betweenness_centrality(G, k=min(k, n), seed=seed)
    return [v for v, _ in sorted(bc.items(), key=lambda x: (-x[1], x[0]))]


def order_adaptive_degree(G):
    """Recalculated-degree attack (Holme et al. 2002): at every step remove the
    currently highest-degree node.  The attacker adapts and does NOT know any
    metric, so the damage it inflicts is an independent ground truth."""
    H = G.copy()
    order = []
    while H.number_of_nodes():
        v = max(H.nodes(), key=lambda x: (H.degree(x), -x))
        order.append(v)
        H.remove_node(v)
    return order


def order_adaptive_betweenness(G, k=50, seed=0):
    """Recalculated-betweenness attack: a different attack principle from the
    degree-adaptive one, used as a second, independent ground truth."""
    H = G.copy()
    order = []
    while H.number_of_nodes() > 1:
        n = H.number_of_nodes()
        bc = nx.betweenness_centrality(H, k=min(k, n), seed=seed)
        v = max(bc, key=lambda x: (bc[x], -x))
        order.append(v)
        H.remove_node(v)
    order.extend(H.nodes())
    return order


STRATEGIES = {
    "random": order_random,
    "degree": order_degree,
    "betweenness": order_betweenness,
}

GROUND_TRUTH_ATTACK = order_adaptive_degree


# --------------------------------------------------------------------------
# robustness metrics
# --------------------------------------------------------------------------


def curve(G, order, alphas=(0.0, 0.5, 1.0, 2.0)):
    """Largest-component fraction along the removal sequence.

    Returns (metrics, frac) where metrics maps alpha -> R_alpha and also holds
    threshold statistics.  Cost of removing v is w_v = max(deg_v,1)**alpha,
    so alpha = 0 recovers the classic Schneider metric exactly.
    """
    n = G.number_of_nodes()
    deg = dict(G.degree())
    H = G.copy()
    frac = np.empty(n + 1, dtype=float)
    frac[0] = 1.0
    for i, v in enumerate(order, start=1):
        H.remove_node(v)
        if H.number_of_nodes() == 0:
            frac[i] = 0.0
        else:
            frac[i] = max(len(c) for c in nx.connected_components(H)) / n

    metrics = {}
    for a in alphas:
        w = np.array([max(deg[v], 1) ** a for v in order], dtype=float)
        cum = np.concatenate(([0.0], np.cumsum(w)))
        metrics[f"R{a:g}"] = float(np.trapz(frac, cum) / cum[-1])
        # cost fraction and node fraction at which the giant component halves
        idx = int(np.argmax(frac < 0.5)) if np.any(frac < 0.5) else n
        metrics[f"c50_{a:g}"] = float(cum[idx] / cum[-1])
        metrics[f"q50_{a:g}"] = float(idx / n)
    return metrics, frac


# --------------------------------------------------------------------------
# Motter-Lai cascade  (independent ground truth of collateral damage)
# --------------------------------------------------------------------------


def _loads(G, k=100, seed=0):
    n = G.number_of_nodes()
    bc = nx.betweenness_centrality(G, k=min(k, n), seed=seed)
    L = np.array([max(bc[v], 1e-9) for v in G.nodes()], dtype=float)
    return L


def cascade(G, removed, beta=0.2, k=100, seed=0):
    """Capacity = (1+beta) * initial load; overload cascades to neighbours.

    `removed` is the set of nodes knocked out by the attack.  Returns the set
    of all failed nodes (attack plus cascade).
    """
    nodes = list(G.nodes())
    idx = {v: i for i, v in enumerate(nodes)}
    L = _loads(G, k=k, seed=seed)
    cap = (1.0 + beta) * L
    H = G.copy()
    failed = set()

    queue = deque()
    for v in removed:
        if v in G:
            failed.add(v)
            queue.append(v)

    while queue:
        v = queue.popleft()
        if v not in H:
            continue
        nbrs = [u for u in H.neighbors(v) if u not in failed]
        lv = L[idx[v]]
        H.remove_node(v)
        if not nbrs:
            continue
        tot_cap = sum(cap[idx[u]] for u in nbrs)
        for u in nbrs:
            j = idx[u]
            share = cap[j] / tot_cap if tot_cap > 0 else 1.0 / len(nbrs)
            L[j] += lv * share
            if L[j] > cap[j] and u not in failed:
                failed.add(u)
                queue.append(u)
    return failed


def attack_damage(G, order, budget=0.2, alpha=1.0):
    """Fraction of nodes detached from the giant component after an attack that
    spends `budget` of the total cost.  alpha=1 -> cost = degree (hubs are
    expensive), alpha=0 -> every node costs the same (the classic assumption).

    No cascade here: the damage is pure connectivity loss caused by the attack.
    """
    n = G.number_of_nodes()
    deg = dict(G.degree())
    w = {v: max(deg[v], 1) ** alpha for v in G.nodes()}
    total = sum(w.values())
    acc = 0.0
    chosen = []
    for v in order:
        chosen.append(v)
        acc += w[v]
        if acc >= budget * total:
            break
    H = G.copy()
    H.remove_nodes_from(chosen)
    if H.number_of_nodes() == 0:
        s = 0.0
    else:
        s = max(len(c) for c in nx.connected_components(H)) / n
    return 1.0 - s, len(chosen)
