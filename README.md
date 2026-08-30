# Comparative Performance Analysis of Maximum Flow Algorithms

**Course:** PECST595 – Advanced Graph Algorithms

This repository contains the implementation and experimental comparison of **Dinic's Algorithm** and **Push-Relabel Algorithm** for maximum-flow problems.

The experiments evaluate the algorithms using:

- A real-world communication network dataset
- Synthetic graphs with different sizes and densities
- Execution time, memory usage, and algorithmic operation counts

## Dataset

**p2p-Gnutella08** from the Stanford Network Analysis Project (SNAP).

The dataset represents a directed peer-to-peer network topology. It is preprocessed and assigned deterministic edge capacities for reproducible experiments.

## Algorithms

- **Dinic's Algorithm**
- **Push-Relabel Algorithm**

Both algorithms use the same flow-network representation and are evaluated on equivalent graphs.

## Experimental Setup

For the real-world dataset:

- The largest weakly connected component is used.
- Self-loops and duplicate edges are removed.
- Node IDs are relabeled.
- Edge capacities are assigned using a fixed random seed.
- Source-sink pairs are selected based on node degree.

For scalability analysis, directed synthetic graphs are generated at different sizes and densities.

## Running the Project

```bash
pip install -r requirements.txt

# Run tests
pytest

# Prepare the dataset
python -m src.dataset_loader

# Run benchmarks
python -m src.benchmark

# Generate figures
python -m src.plotting \
    --csv results/csv/benchmark_results.csv \
    --out-dir results/figures
```

### Useful benchmark options

```text
--trials N
--memory-trials N
--workers N
--skip-real
--skip-synthetic
--out PATH
```

## Project Structure

```text
maxflow_comparison/
├── src/
│   ├── config.py
│   ├── graph_utils.py
│   ├── dinic.py
│   ├── push_relabel.py
│   ├── dataset_loader.py
│   ├── memory_utils.py
│   ├── benchmark.py
│   └── plotting.py
├── tests/
├── data/
├── results/
├── requirements.txt
└── README.md
```

## Results

The benchmark generates:

- `results/csv/benchmark_results.csv` — experimental results
- `results/figures/` — plots comparing execution time, memory usage, operations, and maximum-flow values

The generated results are used for the comparative analysis presented in the research report.
