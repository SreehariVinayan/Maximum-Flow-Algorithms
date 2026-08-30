"""Shared flow-network representation: paired forward/reverse edge arrays.

Both Dinic and Push-Relabel operate on the same FlowNetwork so that
"equivalent capacity graphs" (same edges, same capacities) are guaranteed
by construction rather than by re-parsing input twice.
"""

import random


class FlowNetwork:
    """Edge-list residual graph. Edge i and edge (i ^ 1) are reverse pairs.

    Attributes:
        n        : number of nodes
        adj      : adj[u] = list of edge indices leaving u
        to       : to[e] = head node of edge e
        cap      : cap[e] = residual capacity of edge e (mutated during flow)
        orig_cap : orig_cap[e] = original capacity of edge e (never mutated)
    """

    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.to = []
        self.cap = []
        self.orig_cap = []

    def add_edge(self, u, v, capacity, reverse_capacity=0):
        """Add directed edge u->v with the given capacity, plus its paired
        reverse edge v->u (capacity 0 unless reverse_capacity given, e.g.
        for undirected edges modeled as two opposite arcs)."""
        self.adj[u].append(len(self.to))
        self.to.append(v)
        self.cap.append(capacity)
        self.orig_cap.append(capacity)

        self.adj[v].append(len(self.to))
        self.to.append(u)
        self.cap.append(reverse_capacity)
        self.orig_cap.append(reverse_capacity)

    def num_edges(self):
        return len(self.to)

    def reset_residual(self):
        """Restore residual capacities to original capacities in-place, so
        the same network object can be reused across algorithms/trials
        without rebuilding it from scratch (keeps benchmarking fast and
        keeps 'equivalent capacity graphs' exact)."""
        self.cap = list(self.orig_cap)

    def clone_topology(self):
        """Return a fresh FlowNetwork with identical nodes/edges/capacities,
        fully independent residual state. Used so Dinic and Push-Relabel
        never share mutable residual arrays across a benchmark trial."""
        g = FlowNetwork(self.n)
        g.adj = [list(edges) for edges in self.adj]
        g.to = list(self.to)
        g.cap = list(self.orig_cap)
        g.orig_cap = list(self.orig_cap)
        return g


def assign_deterministic_capacities(edge_pairs, seed, cap_min, cap_max):
    """Given a list of (u, v) directed edges (no duplicates expected),
    deterministically assign an integer capacity to each edge using a
    seeded PRNG. Same edge_pairs + seed always produce the same capacities.

    Returns a list of (u, v, capacity) in the same order as edge_pairs.
    """
    rng = random.Random(seed)
    out = []
    for (u, v) in edge_pairs:
        c = rng.randint(cap_min, cap_max)
        out.append((u, v, c))
    return out


def build_network_from_weighted_edges(n, weighted_edges):
    """Build a FlowNetwork from a list of (u, v, capacity) directed edges.
    Parallel edges are preserved as distinct arcs (both algorithms handle
    them correctly since each gets its own edge index / reverse pair)."""
    g = FlowNetwork(n)
    for (u, v, c) in weighted_edges:
        g.add_edge(u, v, c)
    return g
