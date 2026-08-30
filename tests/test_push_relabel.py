import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph_utils import FlowNetwork
from src.push_relabel import push_relabel_max_flow


def test_simple_two_path_graph():
    g = FlowNetwork(6)
    edges = [(0, 1, 16), (0, 2, 13), (1, 2, 10), (2, 1, 4),
             (1, 3, 12), (3, 2, 9), (2, 4, 14), (4, 3, 7),
             (3, 5, 20), (4, 5, 4)]
    for (u, v, c) in edges:
        g.add_edge(u, v, c)
    result = push_relabel_max_flow(g, 0, 5)
    assert result.max_flow == 23


def test_single_edge():
    g = FlowNetwork(2)
    g.add_edge(0, 1, 7)
    result = push_relabel_max_flow(g, 0, 1)
    assert result.max_flow == 7


def test_disconnected_source_sink():
    g = FlowNetwork(3)
    g.add_edge(0, 1, 5)
    result = push_relabel_max_flow(g, 0, 2)
    assert result.max_flow == 0


def test_no_direct_path_but_reachable():
    g = FlowNetwork(4)
    g.add_edge(0, 1, 3)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 3)
    result = push_relabel_max_flow(g, 0, 3)
    assert result.max_flow == 3


def test_zero_capacity_edge_is_useless():
    g = FlowNetwork(3)
    g.add_edge(0, 1, 0)
    g.add_edge(0, 2, 5)
    g.add_edge(2, 1, 5)
    result = push_relabel_max_flow(g, 0, 1)
    assert result.max_flow == 5


def test_parallel_edges():
    g = FlowNetwork(2)
    g.add_edge(0, 1, 3)
    g.add_edge(0, 1, 4)
    result = push_relabel_max_flow(g, 0, 1)
    assert result.max_flow == 7


def test_diamond_bottleneck():
    g = FlowNetwork(4)
    g.add_edge(0, 1, 10)
    g.add_edge(0, 2, 10)
    g.add_edge(1, 3, 1)
    g.add_edge(2, 3, 10)
    result = push_relabel_max_flow(g, 0, 3)
    assert result.max_flow == 11


if __name__ == "__main__":
    test_simple_two_path_graph()
    test_single_edge()
    test_disconnected_source_sink()
    test_no_direct_path_but_reachable()
    test_zero_capacity_edge_is_useless()
    test_parallel_edges()
    test_diamond_bottleneck()
    print("All test_push_relabel tests passed.")
