"""Matched classical sampling baselines with explicit computational budgets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np

from qbasin.landscape import IsingLandscape


@dataclass(frozen=True)
class ClassicalSampleResult:
    counts: Counter[str]
    sampler: str
    requested_samples: int
    energy_difference_evaluations: int
    accepted_moves: int
    wall_seconds: float
    seed: int
    parameters: dict[str, Any]

    def metadata(self) -> dict[str, Any]:
        return {
            "sampler": self.sampler,
            "requested_samples": self.requested_samples,
            "energy_difference_evaluations": self.energy_difference_evaluations,
            "accepted_moves": self.accepted_moves,
            "acceptance_rate": (
                self.accepted_moves / self.energy_difference_evaluations
                if self.energy_difference_evaluations
                else None
            ),
            "wall_seconds": self.wall_seconds,
            "seed": self.seed,
            "parameters": self.parameters,
        }


def _random_occupations(rng: np.random.Generator, n_spins: int) -> np.ndarray:
    return rng.integers(0, 2, size=n_spins, dtype=np.int8)


def uniform_random_samples(
    landscape: IsingLandscape,
    *,
    n_samples: int,
    seed: int = 0,
) -> ClassicalSampleResult:
    """Uniform bitstrings: the mandatory zero-search classical baseline."""
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    rng = np.random.default_rng(seed)
    started = perf_counter()
    counts: Counter[str] = Counter()
    for _ in range(n_samples):
        counts[landscape.bitstring(_random_occupations(rng, landscape.n_spins))] += 1
    elapsed = perf_counter() - started
    return ClassicalSampleResult(
        counts=counts,
        sampler="uniform_random",
        requested_samples=n_samples,
        energy_difference_evaluations=0,
        accepted_moves=0,
        wall_seconds=elapsed,
        seed=seed,
        parameters={},
    )


def metropolis_samples(
    landscape: IsingLandscape,
    *,
    n_samples: int,
    temperature_mhz: float,
    burn_in_sweeps: int = 50,
    sweeps_between_samples: int = 5,
    seed: int = 0,
) -> ClassicalSampleResult:
    """Single-spin Metropolis samples from one persistent Markov chain."""
    if n_samples <= 0 or temperature_mhz <= 0:
        raise ValueError("n_samples and temperature_mhz must be positive")
    if burn_in_sweeps < 0 or sweeps_between_samples <= 0:
        raise ValueError("invalid burn-in or thinning")
    rng = np.random.default_rng(seed)
    temperature = 2.0 * np.pi * temperature_mhz
    occupations = _random_occupations(rng, landscape.n_spins)
    counts: Counter[str] = Counter()
    evaluations = 0
    accepted = 0
    total_sweeps = burn_in_sweeps + n_samples * sweeps_between_samples
    started = perf_counter()
    for sweep in range(total_sweeps):
        for _ in range(landscape.n_spins):
            index = int(rng.integers(0, landscape.n_spins))
            delta_energy = float(landscape.flip_costs(occupations)[index])
            evaluations += 1
            if delta_energy <= 0 or rng.random() < np.exp(-delta_energy / temperature):
                occupations[index] ^= 1
                accepted += 1
        if sweep >= burn_in_sweeps:
            offset = sweep - burn_in_sweeps + 1
            if offset % sweeps_between_samples == 0:
                counts[landscape.bitstring(occupations)] += 1
    elapsed = perf_counter() - started
    return ClassicalSampleResult(
        counts=counts,
        sampler="metropolis",
        requested_samples=n_samples,
        energy_difference_evaluations=evaluations,
        accepted_moves=accepted,
        wall_seconds=elapsed,
        seed=seed,
        parameters={
            "temperature_mhz": temperature_mhz,
            "burn_in_sweeps": burn_in_sweeps,
            "sweeps_between_samples": sweeps_between_samples,
        },
    )


def simulated_annealing_samples(
    landscape: IsingLandscape,
    *,
    n_samples: int,
    temperature_start_mhz: float = 20.0,
    temperature_end_mhz: float = 0.05,
    temperature_steps: int = 60,
    sweeps_per_temperature: int = 2,
    seed: int = 0,
) -> ClassicalSampleResult:
    """Independent annealing restarts, returning one terminal state per restart."""
    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    if temperature_start_mhz <= temperature_end_mhz or temperature_end_mhz <= 0:
        raise ValueError("temperatures must satisfy start > end > 0")
    if temperature_steps < 2 or sweeps_per_temperature <= 0:
        raise ValueError("invalid annealing schedule")
    rng = np.random.default_rng(seed)
    temperatures = 2.0 * np.pi * np.geomspace(
        temperature_start_mhz, temperature_end_mhz, temperature_steps
    )
    counts: Counter[str] = Counter()
    evaluations = 0
    accepted = 0
    started = perf_counter()
    for _ in range(n_samples):
        occupations = _random_occupations(rng, landscape.n_spins)
        for temperature in temperatures:
            for _ in range(sweeps_per_temperature * landscape.n_spins):
                index = int(rng.integers(0, landscape.n_spins))
                delta_energy = float(landscape.flip_costs(occupations)[index])
                evaluations += 1
                if delta_energy <= 0 or rng.random() < np.exp(
                    -delta_energy / temperature
                ):
                    occupations[index] ^= 1
                    accepted += 1
        counts[landscape.bitstring(occupations)] += 1
    elapsed = perf_counter() - started
    return ClassicalSampleResult(
        counts=counts,
        sampler="simulated_annealing",
        requested_samples=n_samples,
        energy_difference_evaluations=evaluations,
        accepted_moves=accepted,
        wall_seconds=elapsed,
        seed=seed,
        parameters={
            "temperature_start_mhz": temperature_start_mhz,
            "temperature_end_mhz": temperature_end_mhz,
            "temperature_steps": temperature_steps,
            "sweeps_per_temperature": sweeps_per_temperature,
        },
    )


def parallel_tempering_samples(
    landscape: IsingLandscape,
    *,
    n_samples: int,
    temperature_min_mhz: float = 0.1,
    temperature_max_mhz: float = 20.0,
    replicas: int = 10,
    burn_in_cycles: int = 100,
    cycles_between_samples: int = 5,
    seed: int = 0,
) -> ClassicalSampleResult:
    """Replica-exchange Monte Carlo; samples are taken from the cold replica."""
    if n_samples <= 0 or replicas < 2:
        raise ValueError("n_samples must be positive and replicas >= 2")
    if not 0 < temperature_min_mhz < temperature_max_mhz:
        raise ValueError("temperatures must satisfy 0 < min < max")
    if burn_in_cycles < 0 or cycles_between_samples <= 0:
        raise ValueError("invalid burn-in or sampling interval")

    rng = np.random.default_rng(seed)
    temperatures = 2.0 * np.pi * np.geomspace(
        temperature_min_mhz, temperature_max_mhz, replicas
    )
    betas = 1.0 / temperatures
    states = np.asarray(
        [_random_occupations(rng, landscape.n_spins) for _ in range(replicas)]
    )
    energies = np.asarray(
        [landscape.energy_of_occupations(state) for state in states]
    )
    counts: Counter[str] = Counter()
    evaluations = replicas
    accepted = 0
    attempted_exchanges = 0
    accepted_exchanges = 0
    total_cycles = burn_in_cycles + n_samples * cycles_between_samples
    started = perf_counter()

    for cycle in range(total_cycles):
        for replica in range(replicas):
            for _ in range(landscape.n_spins):
                index = int(rng.integers(0, landscape.n_spins))
                delta_energy = float(landscape.flip_costs(states[replica])[index])
                evaluations += 1
                if delta_energy <= 0 or rng.random() < np.exp(
                    -betas[replica] * delta_energy
                ):
                    states[replica, index] ^= 1
                    energies[replica] += delta_energy
                    accepted += 1

        parity = cycle % 2
        for left in range(parity, replicas - 1, 2):
            right = left + 1
            attempted_exchanges += 1
            exponent = (betas[left] - betas[right]) * (
                energies[left] - energies[right]
            )
            if exponent >= 0 or rng.random() < np.exp(exponent):
                states[[left, right]] = states[[right, left]]
                energies[[left, right]] = energies[[right, left]]
                accepted_exchanges += 1

        if cycle >= burn_in_cycles:
            offset = cycle - burn_in_cycles + 1
            if offset % cycles_between_samples == 0:
                counts[landscape.bitstring(states[0])] += 1

    elapsed = perf_counter() - started
    return ClassicalSampleResult(
        counts=counts,
        sampler="parallel_tempering",
        requested_samples=n_samples,
        energy_difference_evaluations=evaluations,
        accepted_moves=accepted,
        wall_seconds=elapsed,
        seed=seed,
        parameters={
            "temperature_min_mhz": temperature_min_mhz,
            "temperature_max_mhz": temperature_max_mhz,
            "replicas": replicas,
            "burn_in_cycles": burn_in_cycles,
            "cycles_between_samples": cycles_between_samples,
            "attempted_exchanges": attempted_exchanges,
            "accepted_exchanges": accepted_exchanges,
            "exchange_acceptance_rate": (
                accepted_exchanges / attempted_exchanges
                if attempted_exchanges
                else None
            ),
        },
    )


def run_classical_sampler(
    landscape: IsingLandscape,
    specification: dict[str, Any],
    *,
    n_samples: int,
    seed: int,
) -> ClassicalSampleResult:
    """Dispatch a JSON-serializable classical sampler specification."""
    specification = dict(specification)
    name = str(specification.pop("name"))
    functions = {
        "uniform_random": uniform_random_samples,
        "metropolis": metropolis_samples,
        "simulated_annealing": simulated_annealing_samples,
        "parallel_tempering": parallel_tempering_samples,
    }
    if name not in functions:
        raise ValueError(f"unknown sampler {name!r}; choose {sorted(functions)}")
    return functions[name](
        landscape,
        n_samples=n_samples,
        seed=seed,
        **specification,
    )

