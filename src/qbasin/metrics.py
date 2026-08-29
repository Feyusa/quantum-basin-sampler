"""Sampling, quality-diversity and distribution-comparison metrics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from qbasin.basins import overlap_distribution
from qbasin.landscape import IsingLandscape


def _probabilities(counts: Mapping[str, int | float]) -> dict[str, float]:
    total = float(sum(value for value in counts.values() if value > 0))
    if total <= 0:
        raise ValueError("counts must contain positive mass")
    return {key: float(value) / total for key, value in counts.items() if value > 0}


def summarize_basin_distribution(
    basin_counts: Mapping[str, int | float],
    landscape: IsingLandscape,
    *,
    reference_minima: set[str] | None = None,
    low_energy_tolerance_mhz: float = 0.25,
) -> dict[str, Any]:
    """Return interpretable concentration, quality and diversity statistics."""
    probabilities = _probabilities(basin_counts)
    p = np.asarray(list(probabilities.values()), dtype=float)
    energies = np.asarray(
        [landscape.energy(state) / (2.0 * np.pi) for state in probabilities]
    )
    weights = p
    entropy = float(-np.sum(p * np.log(p)))
    collision_probability = float(np.sum(p**2))
    pq = overlap_distribution(basin_counts, landscape.n_spins)
    mean_overlap = float(sum(q * mass for q, mass in pq.items()))
    mean_hamming = 0.5 * landscape.n_spins * (1.0 - mean_overlap)
    global_best = (
        min(landscape.energy(state) / (2.0 * np.pi) for state in reference_minima)
        if reference_minima
        else float(np.min(energies))
    )
    low_energy_states = {
        state
        for state in probabilities
        if landscape.energy(state) / (2.0 * np.pi)
        <= global_best + low_energy_tolerance_mhz
    }
    result: dict[str, Any] = {
        "samples": float(sum(basin_counts.values())),
        "unique_basins": len(probabilities),
        "shannon_entropy_nats": entropy,
        "normalized_entropy": (
            entropy / np.log(len(probabilities)) if len(probabilities) > 1 else 0.0
        ),
        "collision_probability_p_q1": collision_probability,
        "effective_basin_count": 1.0 / collision_probability,
        "top_basin_mass": float(np.max(p)),
        "best_energy_mhz": float(np.min(energies)),
        "mean_energy_mhz": float(np.dot(weights, energies)),
        "energy_std_mhz": float(
            np.sqrt(np.dot(weights, (energies - np.dot(weights, energies)) ** 2))
        ),
        "mean_replica_overlap": mean_overlap,
        "mean_pairwise_hamming": mean_hamming,
        "negative_overlap_mass": float(sum(mass for q, mass in pq.items() if q < 0)),
        "low_energy_threshold_mhz": global_best + low_energy_tolerance_mhz,
        "low_energy_mass": float(
            sum(probabilities[state] for state in low_energy_states)
        ),
        "unique_low_energy_basins": len(low_energy_states),
    }
    if reference_minima is not None:
        result["reference_minima"] = len(reference_minima)
        result["reference_basin_coverage"] = len(
            set(probabilities).intersection(reference_minima)
        ) / len(reference_minima)
    return result


def compare_basin_distributions(
    candidate_counts: Mapping[str, int | float],
    reference_counts: Mapping[str, int | float],
) -> dict[str, float]:
    """Symmetric distances and support complementarity between two samplers."""
    candidate = _probabilities(candidate_counts)
    reference = _probabilities(reference_counts)
    support = sorted(set(candidate) | set(reference))
    p = np.asarray([candidate.get(state, 0.0) for state in support])
    q = np.asarray([reference.get(state, 0.0) for state in support])
    midpoint = 0.5 * (p + q)

    def kl(left: np.ndarray, right: np.ndarray) -> float:
        mask = left > 0
        return float(np.sum(left[mask] * np.log2(left[mask] / right[mask])))

    js = 0.5 * kl(p, midpoint) + 0.5 * kl(q, midpoint)
    shared = set(candidate).intersection(reference)
    union = set(candidate).union(reference)
    return {
        "jensen_shannon_bits": js,
        "total_variation": float(0.5 * np.sum(np.abs(p - q))),
        "hellinger": float(np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(q)) ** 2))),
        "support_jaccard": len(shared) / len(union),
        "candidate_mass_on_reference_support": float(
            sum(candidate[state] for state in shared)
        ),
        "reference_mass_on_candidate_support": float(
            sum(reference[state] for state in shared)
        ),
    }


def bootstrap_metric_intervals(
    basin_counts: Mapping[str, int],
    landscape: IsingLandscape,
    *,
    reference_minima: set[str] | None = None,
    resamples: int = 500,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> dict[str, Any]:
    """Multinomial shot-bootstrap intervals for all numeric basin metrics.

    These intervals quantify finite-shot uncertainty conditional on the
    observed support. Independent run and geometry seeds are still required
    to quantify run-to-run and disorder-realization variation.
    """
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie strictly between 0 and 1")
    states = sorted(state for state, count in basin_counts.items() if count > 0)
    if not states:
        raise ValueError("basin_counts must contain positive counts")
    integer_counts = np.asarray([int(basin_counts[state]) for state in states])
    if np.any(integer_counts <= 0):
        raise ValueError("bootstrap requires positive integer counts")
    shots = int(integer_counts.sum())
    probabilities = integer_counts / shots
    rng = np.random.default_rng(seed)
    sampled_metrics: dict[str, list[float]] = {}
    for _ in range(resamples):
        draw = rng.multinomial(shots, probabilities)
        resampled = {
            state: int(count)
            for state, count in zip(states, draw)
            if count > 0
        }
        metrics = summarize_basin_distribution(
            resampled,
            landscape,
            reference_minima=reference_minima,
        )
        for name, value in metrics.items():
            if isinstance(value, (int, float)) and np.isfinite(value):
                sampled_metrics.setdefault(name, []).append(float(value))

    alpha = 0.5 * (1.0 - confidence_level)
    intervals = {
        name: {
            "lower": float(np.quantile(values, alpha)),
            "median": float(np.quantile(values, 0.5)),
            "upper": float(np.quantile(values, 1.0 - alpha)),
        }
        for name, values in sampled_metrics.items()
    }
    return {
        "method": "multinomial_shot_bootstrap",
        "resamples": resamples,
        "confidence_level": confidence_level,
        "seed": seed,
        "intervals": intervals,
    }
