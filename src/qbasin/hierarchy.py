"""Sampled-basin clustering and exact energy-barrier hierarchy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import numpy as np

from qbasin.landscape import IsingLandscape


@dataclass(frozen=True)
class BarrierMerge:
    left_minima: tuple[str, ...]
    right_minima: tuple[str, ...]
    merged_minima: tuple[str, ...]
    saddle_energy_mhz: float
    barrier_above_lower_minimum_mhz: float
    barrier_above_higher_minimum_mhz: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = np.arange(size)
        self.rank = np.zeros(size, dtype=np.int8)
        self.labels: list[set[int]] = [set() for _ in range(size)]

    def find(self, item: int) -> int:
        root = item
        while self.parent[root] != root:
            root = int(self.parent[root])
        while self.parent[item] != item:
            parent = int(self.parent[item])
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: int, right: int) -> tuple[int, set[int], set[int]]:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return left_root, set(), set()
        left_labels = set(self.labels[left_root])
        right_labels = set(self.labels[right_root])
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.labels[left_root] |= self.labels[right_root]
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return left_root, left_labels, right_labels


def exact_barrier_merge_tree(
    landscape: IsingLandscape,
    *,
    max_spins: int = 18,
) -> list[BarrierMerge]:
    """Flood the full hypercube and record when minima components connect.

    The connection energy is the exact minimax saddle energy within the
    one-spin-flip state graph.  This produces a disconnectivity-style hierarchy
    without assuming that Hamming distance is an energy barrier.
    """
    if landscape.n_spins > max_spins:
        raise ValueError(f"exact barrier tree limited to N<={max_spins}")
    energies = landscape.all_energies(max_spins=max_spins)
    minima_strings = landscape.local_minima()
    minima_states = [landscape.bitstring_to_int(state) for state in minima_strings]
    minimum_index = {state: index for index, state in enumerate(minima_states)}
    minimum_energies = {
        index: energies[state] / (2.0 * np.pi)
        for state, index in minimum_index.items()
    }

    order = np.argsort(energies, kind="stable")
    active = np.zeros(len(energies), dtype=bool)
    union_find = _UnionFind(len(energies))
    masks = [1 << (landscape.n_spins - 1 - i) for i in range(landscape.n_spins)]
    events: list[BarrierMerge] = []

    for state_value in order:
        state = int(state_value)
        active[state] = True
        if state in minimum_index:
            union_find.labels[state].add(minimum_index[state])
        for mask in masks:
            neighbour = state ^ mask
            if not active[neighbour]:
                continue
            _, left_labels, right_labels = union_find.union(state, neighbour)
            if not left_labels or not right_labels:
                continue
            # Empty intersection is expected; a nonempty one would be an
            # already-recorded component merge and should not create an event.
            if left_labels.intersection(right_labels):
                continue
            merged = left_labels | right_labels
            saddle = float(energies[state] / (2.0 * np.pi))
            relevant_energies = [minimum_energies[index] for index in merged]
            events.append(
                BarrierMerge(
                    left_minima=tuple(
                        sorted(minima_strings[index] for index in left_labels)
                    ),
                    right_minima=tuple(
                        sorted(minima_strings[index] for index in right_labels)
                    ),
                    merged_minima=tuple(
                        sorted(minima_strings[index] for index in merged)
                    ),
                    saddle_energy_mhz=saddle,
                    barrier_above_lower_minimum_mhz=saddle
                    - min(relevant_energies),
                    barrier_above_higher_minimum_mhz=saddle
                    - max(relevant_energies),
                )
            )
    return events


def hamming_linkage(
    basin_counts: Mapping[str, int | float],
) -> dict[str, Any]:
    """Average-linkage hierarchy of sampled minima in normalized Hamming space."""
    basins = sorted(state for state, count in basin_counts.items() if count > 0)
    if not basins:
        raise ValueError("basin_counts has no positive entries")
    if len(basins) == 1:
        return {"labels": basins, "linkage": [], "metric": "normalized_hamming"}
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import pdist

    matrix = np.asarray([[int(bit) for bit in state] for state in basins])
    distances = pdist(matrix, metric="hamming")
    linkage_matrix = linkage(distances, method="average")
    return {
        "labels": basins,
        "linkage": linkage_matrix.tolist(),
        "metric": "normalized_hamming",
        "method": "average",
    }


def pairwise_basin_relations(
    basin_counts: Mapping[str, int | float],
    landscape: IsingLandscape,
) -> list[dict[str, Any]]:
    """Pair records for overlap, Hamming distance, probability and energy."""
    probabilities = {
        state: float(count) / sum(basin_counts.values())
        for state, count in basin_counts.items()
        if count > 0
    }
    basins = sorted(probabilities)
    records: list[dict[str, Any]] = []
    for i, left in enumerate(basins):
        for right in basins[i + 1 :]:
            distance = sum(a != b for a, b in zip(left, right))
            records.append(
                {
                    "left": left,
                    "right": right,
                    "hamming_distance": distance,
                    "normalized_hamming": distance / landscape.n_spins,
                    "overlap": (landscape.n_spins - 2 * distance)
                    / landscape.n_spins,
                    "left_probability": probabilities[left],
                    "right_probability": probabilities[right],
                    "pair_probability": 2
                    * probabilities[left]
                    * probabilities[right],
                    "left_energy_mhz": landscape.energy(left) / (2.0 * np.pi),
                    "right_energy_mhz": landscape.energy(right) / (2.0 * np.pi),
                }
            )
    return records

