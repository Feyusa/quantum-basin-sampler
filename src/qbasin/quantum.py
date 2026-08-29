"""Ideal quantum simulation backend with metadata needed for benchmarking."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

import numpy as np

from qbasin.geometry import Geometry
from qbasin.pulse import PulseParameters, blockade_ratio, build_sequence


@dataclass(frozen=True)
class QuantumSampleResult:
    counts: Counter[str]
    shots: int
    wall_seconds: float
    device_profile: str
    atom_order: tuple[str, ...]
    pulse: PulseParameters
    blockade_ratio: float
    seed: int

    def metadata(self) -> dict[str, Any]:
        return {
            "shots": self.shots,
            "wall_seconds": self.wall_seconds,
            "device_profile": self.device_profile,
            "atom_order": list(self.atom_order),
            "pulse": self.pulse.to_dict(),
            "blockade_ratio": self.blockade_ratio,
            "seed": self.seed,
        }


def simulate_quantum_samples(
    geometry: Geometry,
    pulse: PulseParameters,
    *,
    shots: int,
    device_profile: str = "ruby_proxy",
    seed: int = 0,
) -> QuantumSampleResult:
    """Run a small-system ideal Qutip simulation and sample final bitstrings."""
    if shots <= 0:
        raise ValueError("shots must be positive")
    if geometry.n_atoms > 20:
        raise ValueError(
            "exact state-vector emulation scales exponentially; use N<=20 "
            "or add a scalable backend adapter"
        )
    from pulser_simulation import QutipBackendV2

    np.random.seed(seed)
    sequence = build_sequence(geometry, pulse, device_profile)
    config = QutipBackendV2.default_config.with_changes(default_num_shots=shots)
    backend = QutipBackendV2(sequence, config=config)
    started = perf_counter()
    results = backend.run()
    elapsed = perf_counter() - started
    counts = Counter(results.final_bitstrings)
    if sum(counts.values()) != shots:
        raise RuntimeError("backend returned a different number of shots")
    return QuantumSampleResult(
        counts=counts,
        shots=shots,
        wall_seconds=elapsed,
        device_profile=device_profile,
        atom_order=tuple(results.atom_order),
        pulse=pulse,
        blockade_ratio=blockade_ratio(geometry, pulse, device_profile),
        seed=seed,
    )

