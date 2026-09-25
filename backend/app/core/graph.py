"""Small graph helpers (no scipy dependency)."""

from __future__ import annotations

import networkx as nx


def pagerank(
    g: nx.Graph, alpha: float = 0.85, weight: str = "weight", iters: int = 100, tol: float = 1e-8
) -> dict:
    """Weighted PageRank by power iteration (undirected graphs: edges count both ways)."""
    nodes = list(g.nodes)
    n = len(nodes)
    if n == 0:
        return {}
    rank = dict.fromkeys(nodes, 1.0 / n)
    out_weight = {u: sum(d.get(weight, 1.0) for _, _, d in g.edges(u, data=True)) for u in nodes}
    for _ in range(iters):
        nxt = dict.fromkeys(nodes, (1.0 - alpha) / n)
        dangling = alpha * sum(rank[u] for u in nodes if out_weight[u] == 0) / n
        for u in nodes:
            if out_weight[u] == 0:
                continue
            share = alpha * rank[u] / out_weight[u]
            for _, v, d in g.edges(u, data=True):
                nxt[v] += share * d.get(weight, 1.0)
        for u in nodes:
            nxt[u] += dangling
        err = sum(abs(nxt[u] - rank[u]) for u in nodes)
        rank = nxt
        if err < tol * n:
            break
    return rank
