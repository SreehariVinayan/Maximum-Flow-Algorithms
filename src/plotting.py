"""Generate publication-friendly figures from the benchmark CSV output.
Never hard-codes results; everything is read from the CSV produced by
`src.benchmark`.
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src import config

ALGO_LABELS = {"dinic": "Dinic", "push_relabel": "Push-Relabel"}
ALGO_COLORS = {"dinic": "#1f77b4", "push_relabel": "#d62728"}


def _load(csv_path):
    df = pd.read_csv(csv_path)
    return df


def _median_by(df, group_cols, value_col):
    return df.groupby(group_cols, as_index=False)[value_col].median()


def plot_time_vs_nodes(df, out_dir):
    sub = df[df["graph_family"].str.startswith("synthetic:")]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for family in sorted(sub["graph_family"].unique()):
        fam_df = sub[sub["graph_family"] == family]
        for algo in ("dinic", "push_relabel"):
            a_df = fam_df[fam_df["algorithm"] == algo]
            if a_df.empty:
                continue
            med = _median_by(a_df, ["num_nodes"], "execution_time_sec")
            med = med.sort_values("num_nodes")
            ax.plot(med["num_nodes"], med["execution_time_sec"], marker="o",
                    label=f"{ALGO_LABELS[algo]} ({family.split(':')[1]})")
    ax.set_xlabel("Number of nodes")
    ax.set_ylabel("Median execution time (s)")
    ax.set_title("Execution Time vs. Number of Nodes (synthetic graphs)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "time_vs_nodes.png"), dpi=200)
    plt.close(fig)


def plot_time_vs_edges(df, out_dir):
    sub = df[df["graph_family"].str.startswith("synthetic:")]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for algo in ("dinic", "push_relabel"):
        a_df = sub[sub["algorithm"] == algo]
        if a_df.empty:
            continue
        med = _median_by(a_df, ["num_edges"], "execution_time_sec")
        med = med.sort_values("num_edges")
        ax.plot(med["num_edges"], med["execution_time_sec"], marker="o",
                label=ALGO_LABELS[algo], color=ALGO_COLORS[algo])
    ax.set_xlabel("Number of edges")
    ax.set_ylabel("Median execution time (s)")
    ax.set_title("Execution Time vs. Number of Edges (synthetic graphs)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "time_vs_edges.png"), dpi=200)
    plt.close(fig)


def plot_memory_vs_size(df, out_dir):
    sub = df[df["graph_family"].str.startswith("synthetic:")]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for algo in ("dinic", "push_relabel"):
        a_df = sub[sub["algorithm"] == algo]
        if a_df.empty:
            continue
        med = _median_by(a_df, ["num_nodes"], "peak_tracemalloc_bytes")
        med = med.sort_values("num_nodes")
        ax.plot(med["num_nodes"], med["peak_tracemalloc_bytes"] / 1024, marker="o",
                label=ALGO_LABELS[algo], color=ALGO_COLORS[algo])
    ax.set_xlabel("Number of nodes")
    ax.set_ylabel("Median peak Python allocation (KB, tracemalloc)")
    ax.set_title("Peak Memory vs. Graph Size (synthetic graphs)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "memory_vs_size.png"), dpi=200)
    plt.close(fig)


def plot_operations_vs_size(df, out_dir):
    sub = df[df["graph_family"].str.startswith("synthetic:")]
    if sub.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    dinic_df = sub[sub["algorithm"] == "dinic"]
    if not dinic_df.empty:
        med = _median_by(dinic_df, ["num_nodes"], "dfs_augmentations").sort_values("num_nodes")
        axes[0].plot(med["num_nodes"], med["dfs_augmentations"], marker="o", color=ALGO_COLORS["dinic"])
        axes[0].set_title("Dinic: Augmenting-Path Operations")
        axes[0].set_xlabel("Number of nodes")
        axes[0].set_ylabel("Median DFS augmentations")
        axes[0].grid(True, alpha=0.3)

    pr_df = sub[sub["algorithm"] == "push_relabel"]
    if not pr_df.empty:
        med_push = _median_by(pr_df, ["num_nodes"], "push_count").sort_values("num_nodes")
        med_relabel = _median_by(pr_df, ["num_nodes"], "relabel_count").sort_values("num_nodes")
        axes[1].plot(med_push["num_nodes"], med_push["push_count"], marker="o", label="Pushes")
        axes[1].plot(med_relabel["num_nodes"], med_relabel["relabel_count"], marker="s", label="Relabels")
        axes[1].set_title("Push-Relabel: Operation Counts")
        axes[1].set_xlabel("Number of nodes")
        axes[1].set_ylabel("Median operation count")
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "operations_vs_size.png"), dpi=200)
    plt.close(fig)


def plot_maxflow_comparison(df, out_dir):
    real_df = df[df["graph_family"].str.startswith("real:")]
    if real_df.empty:
        return
    piv = real_df.pivot_table(index=["graph_instance", "source", "sink"],
                               columns="algorithm", values="max_flow", aggfunc="median")
    piv = piv.reset_index()
    labels = [f"s={r.source},t={r.sink}" for r in piv.itertuples()]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(piv))
    width = 0.35
    if "dinic" in piv.columns:
        ax.bar([i - width / 2 for i in x], piv["dinic"], width, label="Dinic", color=ALGO_COLORS["dinic"])
    if "push_relabel" in piv.columns:
        ax.bar([i + width / 2 for i in x], piv["push_relabel"], width, label="Push-Relabel", color=ALGO_COLORS["push_relabel"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Maximum flow")
    ax.set_title(f"Maximum Flow Comparison ({config.DATASET_NAME}, real-world dataset)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "maxflow_comparison.png"), dpi=200)
    plt.close(fig)


def plot_scalability_summary(df, out_dir):
    sub = df[df["graph_family"].str.startswith("synthetic:")]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for family in sorted(sub["graph_family"].unique()):
        fam_df = sub[sub["graph_family"] == family]
        for algo in ("dinic", "push_relabel"):
            a_df = fam_df[fam_df["algorithm"] == algo]
            if a_df.empty:
                continue
            med = _median_by(a_df, ["num_edges"], "execution_time_sec").sort_values("num_edges")
            ax.plot(med["num_edges"], med["execution_time_sec"], marker="o",
                    label=f"{ALGO_LABELS[algo]} ({family.split(':')[1]})")
    ax.set_xlabel("Number of edges (graph size)")
    ax.set_ylabel("Median execution time (s)")
    ax.set_yscale("log")
    ax.set_title("Scalability Comparison: Execution Time vs. Graph Size")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "scalability_summary.png"), dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate figures from benchmark CSV output.")
    parser.add_argument("--csv", default=os.path.join(config.RESULTS_CSV_DIR, "benchmark_results.csv"))
    parser.add_argument("--out-dir", default=config.RESULTS_FIG_DIR)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    df = _load(args.csv)

    plot_time_vs_nodes(df, args.out_dir)
    plot_time_vs_edges(df, args.out_dir)
    plot_memory_vs_size(df, args.out_dir)
    plot_operations_vs_size(df, args.out_dir)
    plot_maxflow_comparison(df, args.out_dir)
    plot_scalability_summary(df, args.out_dir)

    print(f"Figures written to {args.out_dir}")


if __name__ == "__main__":
    main()
