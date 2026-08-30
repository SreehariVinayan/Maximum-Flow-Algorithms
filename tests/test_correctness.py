import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph_utils import FlowNetwork
from src.dinic import dinic_max_flow
from src.push_relabel import push_relabel_max_flow


def _make_random_network(n, m, seed, cap_min=1, cap_max=20):
    rng = random.Random(seed)
    g = FlowNetwork(n)
    edges = set()
    attempts = 0
    while len(edges) < m and attempts < m * 20:
        attempts += 1
        u = rng.randrange(n)
        v = rng.randrange(n)
        if u == v:
            continue
        edges.add((u, v))
    for (u, v) in edges:
        g.add_edge(u, v, rng.randint(cap_min, cap_max))
    return g


def test_agreement_on_random_graphs():
    for seed in range(10):
        n = random.Random(seed).randint(5, 25)
        m = random.Random(seed + 1000).randint(n, n * 3)
        g1 = _make_random_network(n, m, seed)
        g2 = g1.clone_topology()
        s, t = 0, n - 1
        r1 = dinic_max_flow(g1, s, t)
        r2 = push_relabel_max_flow(g2, s, t)
        assert r1.max_flow == r2.max_flow, (
            f"Mismatch on seed={seed}: dinic={r1.max_flow} "
            f"push_relabel={r2.max_flow}"
        )


def test_agreement_on_hand_checkable_graph():
    # s -> a -> t and s -> b -> t, both capacity-3 paths => max flow 6
    g1 = FlowNetwork(4)
    for (u, v, c) in [(0, 1, 3), (1, 3, 3), (0, 2, 3), (2, 3, 3)]:
        g1.add_edge(u, v, c)
    g2 = g1.clone_topology()

    r1 = dinic_max_flow(g1, 0, 3)
    r2 = push_relabel_max_flow(g2, 0, 3)
    assert r1.max_flow == 6
    assert r2.max_flow == 6


def test_agreement_disconnected():
    g1 = FlowNetwork(5)
    g1.add_edge(0, 1, 10)
    g1.add_edge(3, 4, 10)  # unrelated component
    g2 = g1.clone_topology()
    r1 = dinic_max_flow(g1, 0, 4)
    r2 = push_relabel_max_flow(g2, 0, 4)
    assert r1.max_flow == 0
    assert r2.max_flow == 0


def test_residual_capacities_conserve_flow():
    """Sanity check: after running Dinic, for every edge, forward + reverse
    residual capacity equals the edge's original total capacity (flow
    conservation on the residual graph)."""
    g = _make_random_network(12, 30, seed=99)
    orig = list(g.orig_cap)
    dinic_max_flow(g, 0, 11)
    for e in range(0, len(orig), 2):
        assert g.cap[e] + g.cap[e ^ 1] == orig[e] + orig[e ^ 1]


if __name__ == "__main__":
    test_agreement_on_random_graphs()
    test_agreement_on_hand_checkable_graph()
    test_agreement_disconnected()
    test_residual_capacities_conserve_flow()
    print("All test_correctness tests passed.")
