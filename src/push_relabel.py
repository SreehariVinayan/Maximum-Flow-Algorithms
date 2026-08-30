"""Push-Relabel maximum-flow algorithm, implemented from scratch.

Uses the highest-label active-node selection rule (via height buckets)
plus a current-arc pointer per node so that discharge() never rescans
edges that are already known to be inadmissible within the same height.

A gap-heuristic variant was prototyped but produced an under-count on a
hand-checked test graph and was removed rather than shipped with a
suspected correctness bug; the current-arc + highest-label combination
is the one that is verified against Dinic and hand-checked graphs (see
tests/test_push_relabel.py and tests/test_correctness.py).
"""


class PushRelabelResult:
    def __init__(self, max_flow, pushes, relabels, discharges, edge_scans):
        self.max_flow = max_flow
        self.pushes = pushes
        self.relabels = relabels
        self.discharges = discharges
        self.edge_scans = edge_scans


def push_relabel_max_flow(network, s, t):
    """Compute max flow from s to t on `network` (a FlowNetwork) using the
    highest-label push-relabel variant with a current-arc optimization.
    Mutates network.cap in place. Returns a PushRelabelResult.
    """
    n = network.n
    adj = network.adj
    to = network.to
    cap = network.cap

    height = [0] * n
    excess = [0] * n
    cur = [0] * n  # current-arc pointer per node

    pushes = 0
    relabels = 0
    discharges = 0
    edge_scans = 0

    # height buckets for highest-label selection: bucket[h] = list of
    # active nodes (excess > 0, not s/t) currently at height h
    max_height = 2 * n
    bucket = [[] for _ in range(max_height + 1)]
    in_bucket = [False] * n

    def activate(u):
        nonlocal highest
        if u != s and u != t and excess[u] > 0 and not in_bucket[u]:
            bucket[height[u]].append(u)
            in_bucket[u] = True
            if height[u] > highest:
                highest = height[u]

    # --- initialization: preflow saturates all edges out of s ---
    highest = 0
    height[s] = n

    for e in adj[s]:
        v = to[e]
        c = cap[e]
        if c > 0 and v != s:
            cap[e] -= c
            cap[e ^ 1] += c
            excess[s] -= c
            excess[v] += c
            activate(v)

    def discharge(u):
        nonlocal pushes, relabels, discharges, edge_scans, highest
        discharges += 1
        while excess[u] > 0:
            if cur[u] == len(adj[u]):
                # relabel: raise height to 1 + min height among residual
                # neighbors, so at least one admissible edge exists next
                min_h = None
                for e in adj[u]:
                    edge_scans += 1
                    v = to[e]
                    if cap[e] > 0:
                        if min_h is None or height[v] < min_h:
                            min_h = height[v]
                if min_h is None:
                    break
                new_h = min_h + 1
                height[u] = new_h
                relabels += 1
                cur[u] = 0
                if new_h > highest:
                    highest = new_h
            else:
                e = adj[u][cur[u]]
                edge_scans += 1
                v = to[e]
                if cap[e] > 0 and height[u] == height[v] + 1:
                    delta = min(excess[u], cap[e])
                    cap[e] -= delta
                    cap[e ^ 1] += delta
                    excess[u] -= delta
                    excess[v] += delta
                    pushes += 1
                    activate(v)
                    if excess[u] == 0:
                        break
                else:
                    cur[u] += 1

    # --- main loop: repeatedly discharge the highest active node ---
    # Re-reads bucket[highest]/highest each iteration since discharge()
    # (via relabel) may raise `highest` again.
    while highest >= 0:
        if bucket[highest]:
            u = bucket[highest].pop()
            in_bucket[u] = False
            if excess[u] > 0 and u != s and u != t:
                discharge(u)
                if excess[u] > 0:
                    activate(u)
        else:
            highest -= 1

    return PushRelabelResult(excess[t], pushes, relabels, discharges, edge_scans)
