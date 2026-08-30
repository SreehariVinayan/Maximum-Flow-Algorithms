"""Download, parse, and preprocess the real-world communication-network
dataset (SNAP p2p-Gnutella08), and implement the deterministic
capacity-assignment and source/sink-selection methodology used for the
max-flow experiments.

Dataset: p2p-Gnutella08
Source : https://snap.stanford.edu/data/p2p-Gnutella08.html
Direct download URL: https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz

p2p-Gnutella08 is a directed graph: nodes are Gnutella peers, edges are
peer-to-peer connections captured on August 8, 2002. It is used here
directly as a directed communication-network topology (no direction
symmetrization is applied), which keeps the max-flow problem on it
non-trivial and realistic.
"""

import csv
import gzip
import os
import shutil
import urllib.request

from src import config
from src.graph_utils import (
    FlowNetwork,
    assign_deterministic_capacities,
)

_MISSING = object()  # sentinel so load_processed_graph can distinguish
                      # "use config default" from an explicit max_nodes=None


def download_dataset(force=False):
    """Download the raw dataset gz file if not already present locally."""
    if os.path.exists(config.DATASET_RAW_GZ) and not force:
        return config.DATASET_RAW_GZ
    urllib.request.urlretrieve(config.DATASET_URL, config.DATASET_RAW_GZ)
    return config.DATASET_RAW_GZ


def extract_dataset(force=False):
    """Extract the .gz into a plain-text edge list, if not already done."""
    if os.path.exists(config.DATASET_RAW_TXT) and not force:
        return config.DATASET_RAW_TXT
    download_dataset(force=force)
    with gzip.open(config.DATASET_RAW_GZ, "rb") as f_in:
        with open(config.DATASET_RAW_TXT, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    return config.DATASET_RAW_TXT


def parse_raw_edges():
    """Parse the SNAP edge-list text file into a list of (u, v) directed
    edges using the original SNAP node ids (comment lines starting with
    '#' are skipped)."""
    path = extract_dataset()
    edges = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            u, v = int(parts[0]), int(parts[1])
            edges.append((u, v))
    return edges


def _largest_weakly_connected_component(n, edges):
    """Return the node set of the largest weakly connected component,
    computed via union-find on the undirected version of the edges."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for (u, v) in edges:
        union(u, v)

    from collections import defaultdict
    comps = defaultdict(list)
    for node in range(n):
        comps[find(node)].append(node)

    largest = max(comps.values(), key=len)
    return set(largest)


def _bfs_trim(node_set, edges, max_nodes, seed_node=None):
    """Return a connected subset of `node_set` of size at most `max_nodes`,
    grown by BFS (undirected sense) from a seed node. BFS guarantees every
    collected node is reachable from the seed, so the trimmed subgraph
    stays connected without a second connectivity pass.

    If `seed_node` is None, the highest-total-degree node in `node_set` is
    used, which keeps the trim deterministic and tends to produce a dense,
    well-connected core rather than a thin peripheral sliver.
    """
    from collections import defaultdict, deque

    if len(node_set) <= max_nodes:
        return set(node_set)

    undirected_adj = defaultdict(set)
    degree = defaultdict(int)
    for (u, v) in edges:
        if u in node_set and v in node_set:
            undirected_adj[u].add(v)
            undirected_adj[v].add(u)
            degree[u] += 1
            degree[v] += 1

    if seed_node is None or seed_node not in node_set:
        seed_node = max(node_set, key=lambda node: (degree[node], -node))

    collected = {seed_node}
    queue = deque([seed_node])
    while queue and len(collected) < max_nodes:
        u = queue.popleft()
        for v in sorted(undirected_adj[u]):  # sorted -> deterministic order
            if v not in collected:
                collected.add(v)
                queue.append(v)
                if len(collected) >= max_nodes:
                    break

    return collected


def load_processed_graph(force_reprocess=False, max_nodes=_MISSING):
    """Load the dataset, restrict it to its largest weakly connected
    component, optionally trim it down to a smaller connected "core"
    subgraph via BFS from a high-degree seed node (see
    `config.TRIM_MAX_NODES`), relabel node ids to a contiguous 0..n-1
    range, and cache the processed edge list as CSV.

    Args:
        max_nodes: cap on node count after trimming. Defaults to
            `config.TRIM_MAX_NODES`; pass None explicitly to force the
            full (untrimmed) largest weakly connected component.

    Returns:
        n            : number of nodes in the processed graph
        edges        : list of (u, v) directed edges, relabeled ids
        id_map       : dict original_snap_id -> relabeled_id (None when
                        loaded from cache)
    """
    if max_nodes is _MISSING:
        max_nodes = config.TRIM_MAX_NODES

    if os.path.exists(config.DATASET_PROCESSED_EDGELIST) and not force_reprocess:
        edges = []
        max_id = -1
        with open(config.DATASET_PROCESSED_EDGELIST, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            for row in reader:
                u, v = int(row[0]), int(row[1])
                edges.append((u, v))
                max_id = max(max_id, u, v)
        n = max_id + 1
        return n, edges, None

    raw_edges = parse_raw_edges()
    node_ids = set()
    for (u, v) in raw_edges:
        node_ids.add(u)
        node_ids.add(v)
    n_raw = max(node_ids) + 1

    lwcc = _largest_weakly_connected_component(n_raw, raw_edges)

    if max_nodes is not None:
        keep = _bfs_trim(lwcc, raw_edges, max_nodes, seed_node=config.TRIM_SEED_NODE)
    else:
        keep = lwcc

    sorted_nodes = sorted(keep)
    id_map = {orig: idx for idx, orig in enumerate(sorted_nodes)}

    processed_edges = []
    seen = set()
    for (u, v) in raw_edges:
        if u in id_map and v in id_map:
            uu, vv = id_map[u], id_map[v]
            if uu != vv and (uu, vv) not in seen:
                seen.add((uu, vv))
                processed_edges.append((uu, vv))

    n = len(sorted_nodes)
    with open(config.DATASET_PROCESSED_EDGELIST, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["u", "v"])
        writer.writerows(processed_edges)

    return n, processed_edges, id_map


def build_capacity_network(n, edges, seed=None, cap_min=None, cap_max=None):
    """Apply the deterministic capacity-assignment methodology to a plain
    edge list and return (FlowNetwork, weighted_edges)."""
    seed = config.CAPACITY_SEED if seed is None else seed
    cap_min = config.CAPACITY_MIN if cap_min is None else cap_min
    cap_max = config.CAPACITY_MAX if cap_max is None else cap_max

    weighted_edges = assign_deterministic_capacities(edges, seed, cap_min, cap_max)
    network = FlowNetwork(n)
    for (u, v, c) in weighted_edges:
        network.add_edge(u, v, c)
    return network, weighted_edges


def select_source_sink_pairs(n, edges, num_pairs=None):
    """Deterministically select (source, sink) pairs from the processed
    graph, filtered to pairs with an actual **directed** path from source
    to sink, and diversified so pairs don't collapse onto the same sink
    (or the same tight bottleneck) repeatedly.

    Methodology: rank nodes by (out-degree + in-degree) descending, ties
    broken by node id ascending. Walk that ranking as source candidates,
    highest degree first; for each candidate source, BFS the directed
    graph from it and, among reachable nodes (sorted lowest-degree
    first), pick the first one that hasn't already been used as a sink
    in this selection. This is fully deterministic, avoids hand-picking
    a single favorable pair, guarantees every returned pair has
    max_flow > 0 potential (a directed path exists), and avoids all
    pairs converging on one shared sink/bottleneck.
    """
    num_pairs = config.NUM_SOURCE_SINK_PAIRS if num_pairs is None else num_pairs

    out_deg = [0] * n
    in_deg = [0] * n
    adj = [[] for _ in range(n)]
    for (u, v) in edges:
        out_deg[u] += 1
        in_deg[v] += 1
        adj[u].append(v)
    total_deg = [out_deg[i] + in_deg[i] for i in range(n)]

    ranked = sorted(range(n), key=lambda i: (-total_deg[i], i))
    rank_of = {node: idx for idx, node in enumerate(ranked)}

    def directed_reachable_set(source):
        from collections import deque
        seen = {source}
        q = deque([source])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        seen.discard(source)
        return seen

    pairs = []
    used_sources = set()
    used_sinks = set()
    used_pairs = set()

    # Pass 1: prefer sinks not yet used by any earlier pair, so the
    # selection doesn't repeatedly bottleneck on one shared sink.
    # Pass 2: if a source has no unused reachable sink left (e.g. very
    # few pairs requested from a small reachable set), fall back to
    # allowing sink reuse rather than dropping the source entirely.
    for allow_sink_reuse in (False, True):
        for s in ranked:
            if len(pairs) >= num_pairs:
                break
            if s in used_sources:
                continue
            reachable = directed_reachable_set(s)
            if not reachable:
                continue
            # candidates sorted lowest-degree first (largest rank index)
            candidates = sorted(reachable, key=lambda node: -rank_of[node])
            t = None
            for cand in candidates:
                if (not allow_sink_reuse) and cand in used_sinks:
                    continue
                if (s, cand) in used_pairs:
                    continue
                t = cand
                break
            if t is None:
                continue
            used_sources.add(s)
            used_sinks.add(t)
            used_pairs.add((s, t))
            pairs.append((s, t))
        if len(pairs) >= num_pairs:
            break

    return pairs


if __name__ == "__main__":
    n, edges, _ = load_processed_graph()
    trim_note = (f"trimmed to {config.TRIM_MAX_NODES} nodes"
                 if config.TRIM_MAX_NODES is not None else "full LWCC, untrimmed")
    print(f"Processed graph: {n} nodes, {len(edges)} edges "
          f"({trim_note} of {config.DATASET_NAME})")
    pairs = select_source_sink_pairs(n, edges)
    print("Selected source/sink pairs:", pairs)
