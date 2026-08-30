"""Central configuration for dataset, capacity assignment, and benchmarking."""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
RESULTS_CSV_DIR = os.path.join(PROJECT_ROOT, "results", "csv")
RESULTS_FIG_DIR = os.path.join(PROJECT_ROOT, "results", "figures")

# --- Real-world dataset ---
# SNAP p2p-Gnutella08: a directed peer-to-peer file-sharing (communication)
# network topology snapshot from August 8 2002.
# https://snap.stanford.edu/data/p2p-Gnutella08.html
DATASET_NAME = "p2p-Gnutella08"
DATASET_URL = "https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz"
DATASET_RAW_GZ = os.path.join(DATA_RAW_DIR, "p2p-Gnutella08.txt.gz")
DATASET_RAW_TXT = os.path.join(DATA_RAW_DIR, "p2p-Gnutella08.txt")

# --- Graph trimming (real dataset only) ---
# The full largest-weakly-connected-component of p2p-Gnutella08 has several
# thousand nodes and tens of thousands of edges, which makes pure-Python
# from-scratch Dinic/Push-Relabel impractically slow on a laptop (Dinic is
# worst-case O(V^2 * E)). TRIM_MAX_NODES caps the graph to a smaller,
# still-connected "core" subgraph before benchmarking. Set to None to run
# on the full graph instead (slow; only recommended on a capable machine
# or for a final, patient full run).
TRIM_MAX_NODES = 500
# Seed node for the trim's BFS expansion. None picks the highest-degree
# node deterministically; an explicit SNAP-relabeled id also works once
# you know one from a prior run.
TRIM_SEED_NODE = None

# The processed-edgelist filename encodes the trim size so that changing
# TRIM_MAX_NODES doesn't silently reuse a stale cached subgraph.
_trim_tag = f"trim{TRIM_MAX_NODES}" if TRIM_MAX_NODES is not None else "full"
DATASET_PROCESSED_EDGELIST = os.path.join(
    DATA_PROCESSED_DIR, f"p2p-Gnutella08_edges_{_trim_tag}.csv"
)

# --- Capacity assignment methodology ---
# Deterministic pseudo-random capacities drawn with a fixed seed so that the
# same graph + seed always reproduce the same capacity network.
CAPACITY_SEED = 42
CAPACITY_MIN = 1
CAPACITY_MAX = 50

# --- Source/sink selection methodology ---
# We select several deterministic (source, sink) pairs rather than a single
# favorable pair. Pairs are chosen from nodes ranked by out-degree /
# in-degree on the largest weakly-connected component, using fixed rank
# positions so the choice is reproducible and not hand-picked per result.
NUM_SOURCE_SINK_PAIRS = 4

# --- Timing / trials ---
NUM_TRIALS = 3  # repeated trials per (graph, source, sink, algorithm)

# --- Synthetic scalability benchmark ---
# Kept intentionally modest so the benchmark runs on an ordinary laptop.
SYNTHETIC_NODE_SIZES = [50, 100, 200, 400]
SYNTHETIC_DENSITIES = {
    "sparse": 0.02,   # edge probability for G(n, p) style generation
    "dense": 0.08,
}
SYNTHETIC_SEED = 7

for _d in (DATA_RAW_DIR, DATA_PROCESSED_DIR, RESULTS_CSV_DIR, RESULTS_FIG_DIR):
    os.makedirs(_d, exist_ok=True)
