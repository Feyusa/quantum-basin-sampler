"""Classical Omega=0 Rydberg/Ising landscape and local descent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from qbasin.devices import pulser_device
from qbasin.geometry import Geometry


def validate_bitstring(bitstring: str, n_spins: int) -> None:
    if len(bitstring) != n_spins or set(bitstring) - {"0", "1"}:
        raise ValueError(
            f"expected a {n_spins}-character binary string, got {bitstring!r}"
        )


@dataclass(frozen=True)
class DescentResult:
    start: str
    minimum: str
    energy: float
    accepted_flips: int
    flip_cost_evaluations: int


@dataclass(frozen=True)
class IsingLandscape:
    """Occupation-basis energy H=-delta sum(n)+sum_{i<j}V_ij n_i n_j."""

    interaction: np.ndarray
    delta_rad_per_us: float
    qubit_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        matrix = np.asarray(self.interaction, dtype=float)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError("interaction must be a square matrix")
        if len(self.qubit_ids) != matrix.shape[0]:
            raise ValueError("qubit_ids length must match interaction")
        if not np.allclose(matrix, matrix.T):
            raise ValueError("interaction must be symmetric")
        if not np.allclose(np.diag(matrix), 0.0):
            raise ValueError("interaction diagonal must be zero")
        object.__setattr__(self, "interaction", matrix)

    @classmethod
    def from_geometry(
        cls,
        geometry: Geometry,
        *,
        delta_rad_per_us: float,
        device_profile: str = "ruby_proxy",
    ) -> "IsingLandscape":
        device = pulser_device(device_profile)
        displacement = (
            geometry.coordinates[:, None, :] - geometry.coordinates[None, :, :]
        )
        distances = np.linalg.norm(displacement, axis=2)
        interaction = np.zeros_like(distances)
        mask = distances > 0
        interaction[mask] = device.interaction_coeff / distances[mask] ** 6
        return cls(interaction, float(delta_rad_per_us), geometry.qubit_ids)

    @property
    def n_spins(self) -> int:
        return int(self.interaction.shape[0])

    def occupations(self, bitstring: str) -> np.ndarray:
        validate_bitstring(bitstring, self.n_spins)
        return np.fromiter((int(bit) for bit in bitstring), dtype=np.int8)

    def bitstring(self, occupations: Iterable[int]) -> str:
        values = np.asarray(list(occupations), dtype=np.int8)
        if values.shape != (self.n_spins,) or np.any((values != 0) & (values != 1)):
            raise ValueError("occupations must be a length-N binary vector")
        return "".join(str(int(value)) for value in values)

    def energy(self, bitstring: str) -> float:
        occupations = self.occupations(bitstring).astype(float)
        return float(
            -self.delta_rad_per_us * occupations.sum()
            + 0.5 * occupations @ self.interaction @ occupations
        )

    def energy_of_occupations(self, occupations: np.ndarray) -> float:
        occupations = np.asarray(occupations, dtype=float)
        return float(
            -self.delta_rad_per_us * occupations.sum()
            + 0.5 * occupations @ self.interaction @ occupations
        )

    def flip_costs(self, occupations: np.ndarray) -> np.ndarray:
        occupations = np.asarray(occupations, dtype=np.int8)
        field = self.interaction @ occupations
        return (1 - 2 * occupations) * (-self.delta_rad_per_us + field)

    def descend(
        self,
        bitstring: str,
        *,
        rule: str = "steepest",
        seed: int | None = None,
        tolerance: float = 1e-10,
    ) -> DescentResult:
        """One-spin descent with reproducible steepest or random-improving moves."""
        occupations = self.occupations(bitstring)
        rng = np.random.default_rng(seed)
        accepted = 0
        evaluations = 0
        while True:
            costs = self.flip_costs(occupations)
            evaluations += self.n_spins
            improving = np.flatnonzero(costs < -tolerance)
            if not len(improving):
                break
            if rule == "steepest":
                index = int(np.argmin(costs))
            elif rule == "random_improving":
                index = int(rng.choice(improving))
            else:
                raise ValueError("rule must be steepest or random_improving")
            occupations[index] ^= 1
            accepted += 1
        minimum = self.bitstring(occupations)
        return DescentResult(
            start=bitstring,
            minimum=minimum,
            energy=self.energy_of_occupations(occupations),
            accepted_flips=accepted,
            flip_cost_evaluations=evaluations,
        )

    def int_to_bitstring(self, state: int) -> str:
        if state < 0 or state >= 1 << self.n_spins:
            raise ValueError("integer state outside landscape")
        return format(state, f"0{self.n_spins}b")

    def bitstring_to_int(self, bitstring: str) -> int:
        validate_bitstring(bitstring, self.n_spins)
        return int(bitstring, 2)

    def all_energies(self, *, max_spins: int = 20) -> np.ndarray:
        if self.n_spins > max_spins:
            raise ValueError(f"exact enumeration limited to N<={max_spins}")
        energies = np.empty(1 << self.n_spins, dtype=float)
        for state in range(len(energies)):
            energies[state] = self.energy(self.int_to_bitstring(state))
        return energies

    def local_minima(self, *, tolerance: float = 1e-10) -> list[str]:
        energies = self.all_energies()
        minima: list[str] = []
        masks = [1 << (self.n_spins - 1 - i) for i in range(self.n_spins)]
        for state, energy in enumerate(energies):
            if all(energies[state ^ mask] >= energy - tolerance for mask in masks):
                minima.append(self.int_to_bitstring(state))
        return minima

