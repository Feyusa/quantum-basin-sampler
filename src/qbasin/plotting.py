"""Plots intended for diagnosis and proposal figures, not phase claims."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def plot_overlap_comparison(
    distributions: Mapping[str, Mapping[float, float]],
    *,
    n_spins: int,
    path: Path,
    title: str,
) -> None:
    names = list(distributions)
    figure, axes = plt.subplots(
        1, len(names), figsize=(5.2 * len(names), 4.2), squeeze=False
    )
    for axis, name in zip(axes[0], names):
        distribution = distributions[name]
        q = np.asarray(list(distribution), dtype=float)
        mass = np.asarray(list(distribution.values()), dtype=float)
        axis.bar(
            q,
            mass,
            width=1.2 / n_spins,
            color="teal",
            alpha=0.82,
            edgecolor="black",
        )
        axis.set_title(name)
        axis.set_xlabel(r"Replica overlap $q$")
        axis.set_ylabel(r"Probability mass $P(q)$")
        axis.set_xlim(-1.08, 1.08)
        axis.axvline(0.0, color="firebrick", linestyle="--", alpha=0.45)
        axis.grid(axis="y", linestyle="--", alpha=0.4)
    figure.suptitle(title)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)


def plot_hamming_dendrogram(
    hierarchy: Mapping[str, Any],
    *,
    probabilities: Mapping[str, float],
    path: Path,
    title: str,
) -> None:
    labels = list(hierarchy["labels"])
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(max(7.0, 0.42 * len(labels)), 5.2))
    if len(labels) == 1:
        axis.text(0.5, 0.5, f"Only one basin: {labels[0]}", ha="center", va="center")
        axis.set_axis_off()
    else:
        from scipy.cluster.hierarchy import dendrogram

        display_labels = [f"{state}\np={probabilities[state]:.3f}" for state in labels]
        dendrogram(
            np.asarray(hierarchy["linkage"], dtype=float),
            labels=display_labels,
            leaf_rotation=90,
            ax=axis,
        )
        axis.set_ylabel("Normalized Hamming distance")
        axis.grid(axis="y", linestyle="--", alpha=0.35)
    axis.set_title(title)
    figure.tight_layout()
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)


def plot_scan_metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    path: Path,
    geometry_name: str,
) -> None:
    """Plot diversity and low-energy mass versus sweep time by target detuning."""
    quantum_rows = [
        row for row in rows if row.get("geometry") == geometry_name and row.get("method") == "quantum"
    ]
    if not quantum_rows:
        return
    hold_values = sorted({int(row["hold_ns"]) for row in quantum_rows})
    figure, axes = plt.subplots(
        2,
        len(hold_values),
        figsize=(5.4 * len(hold_values), 8.0),
        squeeze=False,
        sharex="col",
    )
    for column, hold_ns in enumerate(hold_values):
        selected = [row for row in quantum_rows if int(row["hold_ns"]) == hold_ns]
        conditions = sorted(
            {
                (float(row["omega_mhz"]), float(row["delta_target_mhz"]))
                for row in selected
            }
        )
        for omega, detuning in conditions:
            condition_rows = [
                row
                for row in selected
                if float(row["omega_mhz"]) == omega
                and float(row["delta_target_mhz"]) == detuning
            ]
            sweep_values = sorted(
                {float(row["sweep_ns"]) for row in condition_rows}
            )
            label = rf"$\Omega$={omega:g}, $\delta_f$={detuning:g} MHz"
            for axis, metric in zip(
                axes[:, column],
                ("effective_basin_count", "low_energy_mass"),
            ):
                grouped = [
                    [
                        float(row[metric])
                        for row in condition_rows
                        if float(row["sweep_ns"]) == sweep
                    ]
                    for sweep in sweep_values
                ]
                means = np.asarray([np.mean(values) for values in grouped])
                standard_deviations = np.asarray(
                    [np.std(values, ddof=1) if len(values) > 1 else 0.0 for values in grouped]
                )
                axis.errorbar(
                    sweep_values,
                    means,
                    yerr=standard_deviations,
                    marker="o",
                    capsize=3,
                    label=label,
                )
        axes[0, column].set_title(f"hold={hold_ns} ns")
        axes[0, column].set_ylabel("Effective basin count")
        axes[1, column].set_ylabel("Low-energy probability mass")
        axes[1, column].set_xlabel("Sweep duration (ns)")
        for row in range(2):
            axes[row, column].grid(linestyle="--", alpha=0.35)
            axes[row, column].legend(fontsize=8)
    figure.suptitle(f"Controlled nonadiabatic scan: {geometry_name}")
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
