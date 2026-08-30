"""Dinic's maximum-flow algorithm, implemented from scratch.

Uses BFS level graphs plus blocking-flow DFS with a current-arc pointer
(iter array) to avoid re-scanning dead edges within a phase.
"""

from collections import deque


class DinicResult:
    def __init__(self, max_flow, bfs_phases, dfs_augmentations, edge_scans):
        self.max_flow = max_flow
        self.bfs_phases = bfs_phases
        self.dfs_augmentations = dfs_augmentations
        self.edge_scans = edge_scans


def dinic_max_flow(network, s, t):
    """Compute max flow from s to t on `network` (a FlowNetwork).
    Mutates network.cap in place (residual capacities after the run).
    Returns a DinicResult with flow value and instrumentation counters.
    """
    n = network.n
    adj = network.adj
    to = network.to
    cap = network.cap

    level = [-1] * n
    it = [0] * n

    bfs_phases = 0
    dfs_augmentations = 0
    edge_scans = 0

    def bfs():
        nonlocal edge_scans
        for i in range(n):
            level[i] = -1
        level[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for e in adj[u]:
                edge_scans += 1
                v = to[e]
                if cap[e] > 0 and level[v] < 0:
                    level[v] = level[u] + 1
                    q.append(v)
        return level[t] >= 0

    def dfs(u, pushed):
        nonlocal edge_scans
        if u == t:
            return pushed
        while it[u] < len(adj[u]):
            e = adj[u][it[u]]
            edge_scans += 1
            v = to[e]
            if cap[e] > 0 and level[v] == level[u] + 1:
                d = dfs(v, min(pushed, cap[e]))
                if d > 0:
                    cap[e] -= d
                    cap[e ^ 1] += d
                    return d
            it[u] += 1
        return 0

    max_flow = 0
    while bfs():
        bfs_phases += 1
        for i in range(n):
            it[i] = 0
        while True:
            pushed = dfs(s, float("inf"))
            if pushed == 0:
                break
            dfs_augmentations += 1
            max_flow += pushed

    return DinicResult(max_flow, bfs_phases, dfs_augmentations, edge_scans)
