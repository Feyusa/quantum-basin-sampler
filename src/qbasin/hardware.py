"""Optional adapters for the RUBY-facing Pulser/Qadence/Qaptiva stack.

The core package deliberately has no hard dependency on Qadence or myQLM.
Pulser is the source of truth for the ramped waveform used by the experiment.
On TGCC, ``pulser-myqlm`` converts that sequence into a Qaptiva job and the
hosting environment supplies ``qlmaas.qpus.PasqalQPU`` for RUBY submission.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

import numpy as np

from qbasin.geometry import Geometry
from qbasin.pulse import PulseParameters, build_sequence


def pulser_sequence(
    geometry: Geometry,
    pulse: PulseParameters,
    *,
    device_profile: str = "ruby_proxy",
):
    """Build the exact Pulser sequence used by the simulation workflow."""
    return build_sequence(geometry, pulse, device_profile)


def qaptiva_job_from_sequence(
    sequence: Any,
    *,
    shots: int,
    modulation: bool = True,
):
    """Convert a Pulser sequence into a myQLM/Qaptiva analog ``Job``.

    This uses the public ``pulser-myqlm`` binding documented by TGCC.  It does
    not contact a Qaptiva appliance or the RUBY QPU.
    """
    if shots <= 0:
        raise ValueError("shots must be positive")
    try:
        ising_aqpu = import_module("pulser_myqlm").IsingAQPU
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            "Qaptiva conversion requires the optional dependencies; install "
            "with `python -m pip install -e '.[qaptiva]'`."
        ) from exc
    return ising_aqpu.convert_sequence_to_job(
        sequence,
        nbshots=shots,
        modulation=modulation,
    )


def submit_qaptiva_job(job: Any, qpu: Any, *, wait: bool = True) -> Any:
    """Submit through the standard Qaptiva ``qpu.submit(job)`` contract.

    An injected QPU keeps this function testable without credentials.  Remote
    Qaptiva results are asynchronous and expose ``join()`` in the TGCC stack.
    """
    if not hasattr(qpu, "submit"):
        raise TypeError("qpu must expose submit(job)")
    result = qpu.submit(job)
    if wait and hasattr(result, "join"):
        result = result.join()
    return result


def ruby_qpu_from_tgcc_environment() -> Any:
    """Construct TGCC's RUBY QPU handle inside an authenticated Irene session.

    The import is intentionally delayed: importing ``qlmaas`` away from TGCC
    fails when no Qaptiva Access hostname/credentials are configured.
    """
    try:
        qpus = import_module("qlmaas.qpus")
        return qpus.PasqalQPU()
    except Exception as exc:
        raise RuntimeError(
            "RUBY submission is available only after logging into the TGCC "
            "Irene environment with Qaptiva Access configured. The hosting "
            "entity supplies qlmaas.qpus.PasqalQPU and credentials."
        ) from exc


def submit_ruby_sequence(
    sequence: Any,
    *,
    shots: int,
    modulation: bool = True,
    wait: bool = True,
) -> Any:
    """Convert and submit a Pulser sequence to RUBY from the TGCC environment."""
    job = qaptiva_job_from_sequence(
        sequence,
        shots=shots,
        modulation=modulation,
    )
    return submit_qaptiva_job(
        job,
        ruby_qpu_from_tgcc_environment(),
        wait=wait,
    )


def _piecewise_constant_segments(
    pulse: PulseParameters,
    *,
    ramp_steps: int,
) -> list[tuple[float, float, float]]:
    """Return ``(duration_ns, omega, detuning)`` midpoint segments."""
    if ramp_steps <= 0:
        raise ValueError("ramp_steps must be positive")
    omega = pulse.omega_rad_per_us
    delta_initial = pulse.delta_initial_rad_per_us
    delta_target = pulse.delta_target_rad_per_us
    segments: list[tuple[float, float, float]] = []
    midpoint = (np.arange(ramp_steps, dtype=float) + 0.5) / ramp_steps
    for fraction in midpoint:
        segments.append(
            (pulse.rise_ns / ramp_steps, omega * fraction, delta_initial)
        )
    for fraction in midpoint:
        delta = delta_initial + fraction * (delta_target - delta_initial)
        segments.append((pulse.sweep_ns / ramp_steps, omega, delta))
    if pulse.hold_ns:
        segments.append((float(pulse.hold_ns), omega, delta_target))
    for fraction in midpoint:
        segments.append(
            (pulse.fall_ns / ramp_steps, omega * (1.0 - fraction), delta_target)
        )
    return segments


def qadence_circuit(
    geometry: Geometry,
    pulse: PulseParameters,
    *,
    ramp_steps: int = 8,
):
    """Build a minimal Qadence representation of the analog protocol.

    Qadence 1.11 exposes constant analog rotations, so each linear Pulser ramp
    is represented by midpoint, piecewise-constant segments.  This object is a
    portability demonstration, not the production RUBY submission path; the
    exact waveform remains the native Pulser sequence converted by
    ``pulser-myqlm``.
    """
    try:
        qadence = import_module("qadence")
    except ImportError as exc:
        raise RuntimeError(
            "Qadence construction requires the optional dependency; install "
            "with `python -m pip install -e '.[qadence]'`."
        ) from exc

    coordinates = [tuple(map(float, row)) for row in geometry.coordinates]
    register = qadence.Register.from_coordinates(coordinates, spacing=None)
    blocks = [
        qadence.AnalogRot(duration=duration, omega=omega, delta=delta)
        for duration, omega, delta in _piecewise_constant_segments(
            pulse,
            ramp_steps=ramp_steps,
        )
    ]
    return qadence.QuantumCircuit(register, qadence.chain(*blocks))

