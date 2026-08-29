"""Controlled nonadiabatic Rydberg pulse protocols and systematic grids."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Iterable

import numpy as np

from qbasin.devices import assert_proxy_compatible, pulser_device
from qbasin.geometry import Geometry


@dataclass(frozen=True)
class PulseParameters:
    """A rise–sweep–hold–freeze protocol.

    User-facing frequency values are in MHz.  Pulser receives angular
    frequencies in rad/us and durations in ns.
    """

    omega_mhz: float = 2.0
    delta_initial_mhz: float = -6.0
    delta_target_mhz: float = 6.0
    rise_ns: int = 300
    sweep_ns: int = 1_500
    hold_ns: int = 0
    fall_ns: int = 300

    def __post_init__(self) -> None:
        if self.omega_mhz <= 0:
            raise ValueError("omega_mhz must be positive")
        for name in ("rise_ns", "sweep_ns", "fall_ns"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.hold_ns < 0:
            raise ValueError("hold_ns cannot be negative")

    @property
    def omega_rad_per_us(self) -> float:
        return float(2.0 * np.pi * self.omega_mhz)

    @property
    def delta_initial_rad_per_us(self) -> float:
        return float(2.0 * np.pi * self.delta_initial_mhz)

    @property
    def delta_target_rad_per_us(self) -> float:
        return float(2.0 * np.pi * self.delta_target_mhz)

    @property
    def total_duration_ns(self) -> int:
        return self.rise_ns + self.sweep_ns + self.hold_ns + self.fall_ns

    @property
    def sweep_rate_mhz_per_us(self) -> float:
        duration_us = self.sweep_ns / 1_000.0
        return (self.delta_target_mhz - self.delta_initial_mhz) / duration_us

    @property
    def delta_over_omega(self) -> float:
        return self.delta_target_mhz / self.omega_mhz

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "total_duration_ns": self.total_duration_ns,
                "sweep_rate_mhz_per_us": self.sweep_rate_mhz_per_us,
                "delta_over_omega": self.delta_over_omega,
            }
        )
        return data


def expand_pulse_grid(grid: dict[str, Any]) -> list[PulseParameters]:
    """Expand a JSON pulse grid into a deterministic Cartesian product."""
    field_order = (
        "omega_mhz",
        "delta_initial_mhz",
        "delta_target_mhz",
        "rise_ns",
        "sweep_ns",
        "hold_ns",
        "fall_ns",
    )
    defaults = PulseParameters()
    values: list[Iterable[Any]] = []
    for field_name in field_order:
        value = grid.get(field_name, getattr(defaults, field_name))
        if isinstance(value, list):
            if not value:
                raise ValueError(f"pulse grid field {field_name} cannot be empty")
            values.append(value)
        else:
            values.append([value])
    return [
        PulseParameters(**dict(zip(field_order, combination)))
        for combination in product(*values)
    ]


def build_sequence(
    geometry: Geometry,
    parameters: PulseParameters,
    device_profile: str = "ruby_proxy",
):
    """Create the controlled nonadiabatic Pulser sequence.

    The final fall freezes the occupations by ramping Omega to zero at the
    selected target detuning.  The measured bitstrings are then mapped to the
    classical Omega=0 landscape at that same detuning.
    """
    from pulser import Pulse, Sequence
    from pulser.waveforms import RampWaveform

    if device_profile == "ruby_proxy":
        assert_proxy_compatible(geometry, parameters)
    device = pulser_device(device_profile)
    register = geometry.to_register()
    sequence = Sequence(register, device)
    sequence.declare_channel("rydberg", "rydberg_global")

    omega = parameters.omega_rad_per_us
    delta_initial = parameters.delta_initial_rad_per_us
    delta_target = parameters.delta_target_rad_per_us

    sequence.add(
        Pulse.ConstantDetuning(
            RampWaveform(parameters.rise_ns, 0.0, omega),
            delta_initial,
            0.0,
        ),
        "rydberg",
    )
    sequence.add(
        Pulse.ConstantAmplitude(
            omega,
            RampWaveform(parameters.sweep_ns, delta_initial, delta_target),
            0.0,
        ),
        "rydberg",
    )
    if parameters.hold_ns:
        sequence.add(
            Pulse.ConstantPulse(
                parameters.hold_ns,
                omega,
                delta_target,
                0.0,
            ),
            "rydberg",
        )
    sequence.add(
        Pulse.ConstantDetuning(
            RampWaveform(parameters.fall_ns, omega, 0.0),
            delta_target,
            0.0,
        ),
        "rydberg",
    )
    sequence.measure(basis="ground-rydberg")
    return sequence


def blockade_ratio(
    geometry: Geometry,
    parameters: PulseParameters,
    device_profile: str,
) -> float:
    """Return R_b/a using the median nearest-neighbour spacing as a."""
    device = pulser_device(device_profile)
    radius = float(device.rydberg_blockade_radius(parameters.omega_rad_per_us))
    distances = np.linalg.norm(
        geometry.coordinates[:, None, :] - geometry.coordinates[None, :, :],
        axis=2,
    )
    masked = np.where(np.eye(geometry.n_atoms, dtype=bool), np.inf, distances)
    spacing = float(np.median(masked.min(axis=1)))
    return radius / spacing

