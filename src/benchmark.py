"""Benchmark runner for the max-flow experiments — single-pass, parallel.

Speed strategy (one run gets you both timing and memory, no second pass):
1. Independent algorithm/trial runs execute in parallel worker processes.
2. tracemalloc is expensive, so it is only attached to a small sample of
   trials per (graph, algorithm) case (default: 1 of N) instead of every
   trial. Sampled rows report real peak_tracemalloc_bytes / rss_delta_bytes;
   the rest report "NA" for those two columns but still get real timing.
   Tune with --memory-trials (0 disables memory measurement entirely).
3. A base network is inherited once per graph by each worker (fork on
   Linux; serialized once per worker on platforms without fork); every job
   still clones its own independent residual-capacity copy before running.
4. Correctness is still checked across every (graph, source, sink) case,
   using every trial's max_flow value (timing-only trials are just as
   valid for the correctness check as memory-sampled ones).
"""

import argparse
import csv
import os
import sys
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

sys.setrecursionlimit(1000000)

import networkx as nx

from src import config
from src.dinic import dinic_max_flow
from src.push_relabel import push_relabel_max_flow
from src.graph_utils import FlowNetwork, assign_deterministic_capacities
from src.memory_utils import measure_call
from src.dataset_loader import (
    load_processed_graph,
    select_source_sink_pairs,
)


CSV_FIELDS = [
    "graph_family", "graph_instance", "num_nodes", "num_edges", "density",
    "source", "sink", "capacity_seed", "capacity_min", "capacity_max",
    "algorithm", "trial", "max_flow", "execution_time_sec",
    "peak_tracemalloc_bytes", "rss_delta_bytes",
    "bfs_phases", "dfs_augmentations", "push_count", "relabel_count",
    "discharge_count", "edge_scans", "correctness_status",
]

# Worker-local state, installed once per worker process rather than once
# per job, so the (potentially large) base network is not re-pickled for
# every job when the platform doesn't support fork.
_WORKER_NETWORK = None


def _init_worker(network):
    global _WORKER_NETWORK
    _WORKER_NETWORK = network


def _run_one_job(job):
    """Run one independent (algorithm, trial) job in a worker process.
    `measure_memory` is decided per-job by the caller (only a sample of
    trials carry the tracemalloc overhead)."""
    algo_name, trial, s, t, measure_memory = job

    if _WORKER_NETWORK is None:
        raise RuntimeError("Worker network was not initialized.")

    # Critical for correctness: every job gets independent residual
    # capacities cloned from the exact same original capacity network.
    net_copy = _WORKER_NETWORK.clone_topology()

    def call():
        if algo_name == "dinic":
            return dinic_max_flow(net_copy, s, t)
        if algo_name == "push_relabel":
            return push_relabel_max_flow(net_copy, s, t)
        raise ValueError(f"Unknown algorithm: {algo_name}")

    if measure_memory:
        start = time.perf_counter()
        result, mem_metrics = measure_call(call)
        elapsed = time.perf_counter() - start
    else:
        start = time.perf_counter()
        result = call()
        elapsed = time.perf_counter() - start
        mem_metrics = {"peak_tracemalloc_bytes": "NA", "rss_delta_bytes": "NA"}

    rss = mem_metrics["rss_delta_bytes"]
    return {
        "algorithm": algo_name,
        "trial": trial,
        "max_flow": result.max_flow,
        "execution_time_sec": elapsed,
        "peak_tracemalloc_bytes": mem_metrics["peak_tracemalloc_bytes"],
        "rss_delta_bytes": rss if rss is not None else "NA",
        "bfs_phases": getattr(result, "bfs_phases", 0),
        "dfs_augmentations": getattr(result, "dfs_augmentations", 0),
        "push_count": getattr(result, "pushes", 0),
        "relabel_count": getattr(result, "relabels", 0),
        "discharge_count": getattr(result, "discharges", 0),
        "edge_scans": getattr(result, "edge_scans", 0),
    }


def _build_jobs(num_trials, memory_trials, s, t):
    """One job per (algorithm, trial); the first `memory_trials` trials of
    each algorithm carry the tracemalloc/psutil measurement."""
    jobs = []
    for algo_name in ("dinic", "push_relabel"):
        for trial in range(1, num_trials + 1):
            measure_memory = trial <= memory_trials
            jobs.append((algo_name, trial, s, t, measure_memory))
    return jobs


def _run_graph_parallel(graph_family, graph_instance, network, n, m, s, t,
                         cap_seed, cap_min, cap_max, num_trials,
                         memory_trials, executor):
    density = m / (n * (n - 1)) if n > 1 else 0.0
    jobs = _build_jobs(num_trials, memory_trials, s, t)

    # executor is pre-initialized with this graph's network (one process
    # pool per graph; workers inherit it once, cheaply, via fork's
    # copy-on-write) -- see _make_executor.
    rows = list(executor.map(_run_one_job, jobs))

    for row in rows:
        row.update({
            "graph_family": graph_family,
            "graph_instance": graph_instance,
            "num_nodes": n,
            "num_edges": m,
            "density": density,
            "source": s,
            "sink": t,
            "capacity_seed": cap_seed,
            "capacity_min": cap_min,
            "capacity_max": cap_max,
        })

    # Correctness check uses every trial's max_flow (memory-sampled or
    # not -- the algorithm result is identical either way).
    flow_values = {"dinic": set(), "push_relabel": set()}
    for row in rows:
        flow_values[row["algorithm"]].add(row["max_flow"])

    dinic_flows = flow_values["dinic"]
    pr_flows = flow_values["push_relabel"]

    if len(dinic_flows) != 1 or len(pr_flows) != 1:
        status = "FAIL_NONDETERMINISTIC"
    elif dinic_flows != pr_flows:
        status = "FAIL_MISMATCH"
    else:
        status = "OK"

    for row in rows:
        row["correctness_status"] = status

    if status != "OK":
        raise RuntimeError(
            f"{status} for {graph_family}/{graph_instance} s={s} t={t}: "
            f"dinic={dinic_flows} push_relabel={pr_flows}"
        )

    algo_order = {"dinic": 0, "push_relabel": 1}
    rows.sort(key=lambda r: (algo_order[r["algorithm"]], r["trial"]))
    return rows


def _mp_context():
    try:
        return mp.get_context("fork")
    except ValueError:
        return mp.get_context("spawn")


def _make_executor(network, workers):
    """One ProcessPoolExecutor per graph: workers inherit `network` once
    via the initializer (cheap copy-on-write under fork) instead of it
    being pickled per job."""
    return ProcessPoolExecutor(
        max_workers=workers,
        mp_context=_mp_context(),
        initializer=_init_worker,
        initargs=(network,),
    )


def run_real_dataset_benchmark(num_trials, memory_trials, workers):
    n, edges, _ = load_processed_graph()
    weighted_edges = assign_deterministic_capacities(
        edges, config.CAPACITY_SEED, config.CAPACITY_MIN, config.CAPACITY_MAX
    )
    network = FlowNetwork(n)
    for u, v, c in weighted_edges:
        network.add_edge(u, v, c)

    pairs = select_source_sink_pairs(n, edges)
    m = len(edges)
    rows = []

    with _make_executor(network, workers) as executor:
        for pair_number, (s, t) in enumerate(pairs, start=1):
            print(f"  Real pair {pair_number}/{len(pairs)} (s={s}, t={t})...", flush=True)
            rows.extend(_run_graph_parallel(
                f"real:{config.DATASET_NAME}", f"n{n}_m{m}", network,
                n, m, s, t, config.CAPACITY_SEED, config.CAPACITY_MIN,
                config.CAPACITY_MAX, num_trials, memory_trials, executor,
            ))
    return rows


def _generate_synthetic_graph(n, p, seed):
    g = nx.gnp_random_graph(n, p, seed=seed, directed=True)
    return [(u, v) for u, v in g.edges() if u != v]


def run_synthetic_scalability_benchmark(num_trials, memory_trials, workers):
    rows = []
    for density_name, p in config.SYNTHETIC_DENSITIES.items():
        for n in config.SYNTHETIC_NODE_SIZES:
            edges = _generate_synthetic_graph(n, p, config.SYNTHETIC_SEED)
            if not edges:
                continue
            weighted_edges = assign_deterministic_capacities(
                edges, config.CAPACITY_SEED, config.CAPACITY_MIN, config.CAPACITY_MAX
            )
            network = FlowNetwork(n)
            for u, v, c in weighted_edges:
                network.add_edge(u, v, c)

            s, t = 0, n - 1
            if s == t:
                continue

            print(f"  Synthetic {density_name}: n={n}, m={len(edges)}...", flush=True)
            with _make_executor(network, workers) as executor:
                rows.extend(_run_graph_parallel(
                    f"synthetic:{density_name}", f"n{n}_p{p}", network,
                    n, len(edges), s, t, config.CAPACITY_SEED,
                    config.CAPACITY_MIN, config.CAPACITY_MAX,
                    num_trials, memory_trials, executor,
                ))
    return rows


def write_csv(rows, path):
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Run max-flow benchmark suite (parallel, single-pass).")
    parser.add_argument("--trials", type=int, default=config.NUM_TRIALS,
                         help="Number of repeated trials per (graph, algorithm) case.")
    parser.add_argument("--memory-trials", type=int, default=1,
                         help="How many of the trials (per graph/algorithm case) also "
                              "measure tracemalloc/psutil memory. 0 disables memory "
                              "measurement entirely; set equal to --trials to measure "
                              "every trial (slowest, most complete).")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                         help="Number of worker processes. Default: CPU count - 1.")
    parser.add_argument("--skip-real", action="store_true", help="Skip the real-world dataset benchmark.")
    parser.add_argument("--skip-synthetic", action="store_true", help="Skip the synthetic scalability benchmark.")
    parser.add_argument("--out", default=os.path.join(config.RESULTS_CSV_DIR, "benchmark_results.csv"),
                         help="Output CSV path.")
    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if not (0 <= args.memory_trials <= args.trials):
        parser.error("--memory-trials must be between 0 and --trials")

    print(f"Workers: {args.workers}")
    print(f"Trials per case: {args.trials} (memory measured on {args.memory_trials} of them)")

    rows = []
    if not args.skip_real:
        print("Running real-world dataset benchmark...", flush=True)
        rows.extend(run_real_dataset_benchmark(args.trials, args.memory_trials, args.workers))
    if not args.skip_synthetic:
        print("Running synthetic scalability benchmark...", flush=True)
        rows.extend(run_synthetic_scalability_benchmark(args.trials, args.memory_trials, args.workers))

    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
