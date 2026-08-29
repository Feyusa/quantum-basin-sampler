"""Pulser device selection and explicitly provisional RUBY constraints."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from qbasin.geometry import Geometry


@dataclass(frozen=True)
class HardwareEnvelope:
    """Public/conservative constraints used before the RUBY device is exposed.

    Only the 100-atom, 2D, neutral-atom nature is public RUBY information.  The
    remaining numerical limits intentionally mirror Pulser's AnalogDevice and
    are conservative engineering assumptions, not certified RUBY limits.
    """

    name: str = "ruby_proxy_v0"
    max_atoms: int = 100
    dimensions: int = 2
    min_distance_um: float = 5.0
    max_radial_distance_um: float = 38.0
    max_sequence_duration_ns: int = 6_000
    max_omega_rad_per_us: float = 4.0 * np.pi
    max_abs_detuning_rad_per_us: float = 40.0 * np.pi

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RUBY_PROXY = HardwareEnvelope()


def pulser_device(profile: str):
    """Return the Pulser device used for sequence validation/emulation."""
    from pulser.devices import AnalogDevice, MockDevice

    normalized = profile.lower().replace("-", "_")
    if normalized == "mock":
        return MockDevice
    if normalized in {"analog", "ruby_proxy"}:
        # ruby_proxy deliberately uses the stricter available Pulser device.
        return AnalogDevice
    raise ValueError("profile must be one of: mock, analog, ruby_proxy")


def geometry_issues(
    geometry: Geometry,
    envelope: HardwareEnvelope = RUBY_PROXY,
) -> list[str]:
    """Return all provisional hardware-envelope violations."""
    issues: list[str] = []
    if geometry.n_atoms > envelope.max_atoms:
        issues.append(
            f"{geometry.n_atoms} atoms exceeds proxy maximum {envelope.max_atoms}"
        )
    coordinates = geometry.coordinates
    distances = np.linalg.norm(
        coordinates[:, None, :] - coordinates[None, :, :], axis=2
    )
    if geometry.n_atoms > 1:
        minimum = float(distances[np.triu_indices(geometry.n_atoms, 1)].min())
        if minimum < envelope.min_distance_um - 1e-8:
            issues.append(
                f"minimum separation {minimum:.4f} um is below "
                f"{envelope.min_distance_um:.4f} um"
            )
    maximum_radius = float(np.linalg.norm(coordinates, axis=1).max())
    if maximum_radius > envelope.max_radial_distance_um + 1e-8:
        issues.append(
            f"radial extent {maximum_radius:.4f} um exceeds "
            f"{envelope.max_radial_distance_um:.4f} um"
        )
    return issues


def pulse_issues(
    pulse_parameters: Any,
    envelope: HardwareEnvelope = RUBY_PROXY,
) -> list[str]:
    """Return provisional pulse-envelope violations using a duck-typed object."""
    issues: list[str] = []
    if pulse_parameters.total_duration_ns > envelope.max_sequence_duration_ns:
        issues.append(
            f"duration {pulse_parameters.total_duration_ns} ns exceeds "
            f"{envelope.max_sequence_duration_ns} ns"
        )
    if pulse_parameters.omega_rad_per_us > envelope.max_omega_rad_per_us + 1e-10:
        issues.append("Rabi amplitude exceeds the proxy envelope")
    if max(
        abs(pulse_parameters.delta_initial_rad_per_us),
        abs(pulse_parameters.delta_target_rad_per_us),
    ) > envelope.max_abs_detuning_rad_per_us + 1e-10:
        issues.append("detuning exceeds the proxy envelope")
    return issues


def assert_proxy_compatible(geometry: Geometry, pulse_parameters: Any) -> None:
    issues = geometry_issues(geometry) + pulse_issues(pulse_parameters)
    if issues:
        raise ValueError("RUBY proxy validation failed: " + "; ".join(issues))

