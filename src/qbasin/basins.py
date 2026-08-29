"""Basin mapping, exact partitions and replica-overlap distributions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping

import numpy as np

from qbasin.landscape import IsingLandscape, validate_bitstring


@dataclass(frozen=True)
class BasinMappingResult:
    basin_counts: Counter[str]
    assignments: dict[str, str]
    descent_flip_cost_evaluations: int
    weighted_accepted_flips: int
    input_samples: int
    rule: str

    @property
    def mean_accepted_flips(self) -> float:
        return self.weighted_accepted_flips / self.input_samples

    def metadata(self) -> dict[str, float | int | str]:
        return {
            "input_samples": self.input_samples,
            "unique_input_states": len(self.assignments),
            "unique_basins": len(self.basin_counts),
            "descent_flip_cost_evaluations": self.descent_flip_cost_evaluations,
            "weighted_accepted_flips": self.weighted_accepted_flips,
            "mean_accepted_flips": self.mean_accepted_flips,
            "rule": self.rule,
        }


def map_samples_to_basins(
    state_counts: Mapping[str, int],
    landscape: IsingLandscape,
    *,
    rule: str = "steepest",
    seed: int = 0,
) -> BasinMappingResult:
    """Map each unique sampled state once, preserving its multiplicity."""
    if not state_counts or sum(state_counts.values()) <= 0:
        raise ValueError("state_counts must contain positive samples")
    rng = np.random.default_rng(seed)
    basin_counts: Counter[str] = Counter()
    assignments: dict[str, str] = {}
    evaluations = 0
    weighted_flips = 0
    for state, count in sorted(state_counts.items()):
        if count <= 0:
            continue
        result = landscape.descend(
            state,
            rule=rule,
            seed=int(rng.integers(0, 2**32 - 1)),
        )
        assignments[state] = result.minimum
        basin_counts[result.minimum] += int(count)
        evaluations += result.flip_cost_evaluations
        weighted_flips += int(count) * result.accepted_flips
    return BasinMappingResult(
        basin_counts=basin_counts,
        assignments=assignments,
        descent_flip_cost_evaluations=evaluations,
        weighted_accepted_flips=weighted_flips,
        input_samples=sum(int(count) for count in state_counts.values() if count > 0),
        rule=rule,
    )


def exact_basin_partition(
    landscape: IsingLandscape,
    *,
    rule: str = "steepest",
    max_spins: int = 18,
) -> BasinMappingResult:
    """Map every one of 2**N configurations; recommended for small N."""
    if landscape.n_spins > max_spins:
        raise ValueError(f"exact basin partition limited to N<={max_spins}")
    counts = Counter(
        {landscape.int_to_bitstring(state): 1 for state in range(1 << landscape.n_spins)}
    )
    return map_samples_to_basins(counts, landscape, rule=rule, seed=0)


def overlap_distribution(
    state_counts: Mapping[str, int | float],
    n_spins: int,
    *,
    include_same_state: bool = True,
) -> dict[float, float]:
    """Exact independent-replica probability mass P(q) from weighted states."""
    items = sorted(
        (state, float(count))
        for state, count in state_counts.items()
        if count > 0
    )
    if not items:
        raise ValueError("state_counts has no positive entries")
    for state, _ in items:
        validate_bitstring(state, n_spins)
    total = sum(count for _, count in items)
    distribution: defaultdict[float, float] = defaultdict(float)
    for i, (alpha, count_alpha) in enumerate(items):
        start = i if include_same_state else i + 1
        for j in range(start, len(items)):
            beta, count_beta = items[j]
            distance = sum(a != b for a, b in zip(alpha, beta))
            q = (n_spins - 2 * distance) / n_spins
            weight = (count_alpha / total) * (count_beta / total)
            if i != j:
                weight *= 2.0
            distribution[q] += weight
    normalization = sum(distribution.values())
    if normalization <= 0:
        raise ValueError("different-state overlap requires at least two states")
    return {
        q: mass / normalization for q, mass in sorted(distribution.items())
    }


def basin_table(
    basin_counts: Mapping[str, int],
    landscape: IsingLandscape,
) -> list[dict[str, float | int | str]]:
    total = sum(basin_counts.values())
    rows = []
    for rank, (basin, count) in enumerate(
        sorted(basin_counts.items(), key=lambda item: (-item[1], item[0])), start=1
    ):
        rows.append(
            {
                "rank": rank,
                "bitstring": basin,
                "count": int(count),
                "probability": count / total,
                "energy_rad_per_us": landscape.energy(basin),
                "energy_mhz": landscape.energy(basin) / (2.0 * np.pi),
                "excitations": basin.count("1"),
                "magnetization": (2 * basin.count("1") - landscape.n_spins)
                / landscape.n_spins,
            }
        )
    return rows

