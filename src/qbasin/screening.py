"""Exact small-system screening for rugged multibasin landscape candidates."""

from __future__ import annotations

from typing import Any

import numpy as np

from qbasin.basins import exact_basin_partition
from qbasin.geometry import build_geometry, classify_geometry
from qbasin.hierarchy import exact_barrier_merge_tree
from qbasin.landscape import IsingLandscape
from qbasin.metrics import summarize_basin_distribution
from qbasin.pulse import expand_pulse_grid


def screen_landscapes(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate basin and barrier diagnostics without quantum evolution.

    The returned label is a transparent engineering filter. It is not a
    thermodynamic spin-glass classifier.
    """
    max_spins = int(config.get("exact_analysis_max_spins", 16))
    device_profile = str(config.get("device_profile", "ruby_proxy"))
    screen_options = dict(config.get("landscape_screen", {}))
    low_energy_tolerance = float(
        screen_options.get("low_energy_tolerance_mhz", 0.25)
    )
    barrier_threshold = float(
        screen_options.get("barrier_threshold_mhz", 0.25)
    )
    minimum_effective_basins = float(
        screen_options.get("minimum_effective_basins", 2.0)
    )
    compute_barriers = bool(screen_options.get("compute_barriers", True))
    target_detunings = sorted(
        {pulse.delta_target_mhz for pulse in expand_pulse_grid(config["pulse_grid"])}
    )

    rows: list[dict[str, Any]] = []
    for specification in config["geometries"]:
        geometry = build_geometry(specification)
        descriptors = classify_geometry(geometry)
        for delta_mhz in target_detunings:
            common = {
                "geometry": geometry.name,
                "family": geometry.family,
                "n_atoms": geometry.n_atoms,
                "screening_label_geometry": descriptors.screening_label,
                "connected_components": descriptors.connected_components,
                "has_odd_cycle": descriptors.has_odd_cycle,
                "triangles": descriptors.triangles,
                "cycle_rank": descriptors.cycle_rank,
                "nearest_distance_cv": descriptors.nearest_distance_cv,
                "bond_strength_cv": descriptors.bond_strength_cv,
                "delta_target_mhz": delta_mhz,
            }
            if geometry.n_atoms > max_spins:
                rows.append(
                    {
                        **common,
                        "landscape_screen_label": "not_exactly_enumerated",
                        "screening_note": f"N exceeds exact limit {max_spins}",
                    }
                )
                continue

            landscape = IsingLandscape.from_geometry(
                geometry,
                delta_rad_per_us=2.0 * np.pi * delta_mhz,
                device_profile=device_profile,
            )
            partition = exact_basin_partition(
                landscape,
                rule=str(config.get("descent_rule", "steepest")),
                max_spins=max_spins,
            )
            minima = sorted(partition.basin_counts)
            energies = np.asarray(
                [landscape.energy(state) / (2.0 * np.pi) for state in minima]
            )
            ground_energy = float(np.min(energies))
            ground_degeneracy = int(np.sum(np.isclose(energies, ground_energy)))
            low_lying_minima = int(
                np.sum(energies <= ground_energy + low_energy_tolerance)
            )
            energy_by_minimum = dict(zip(minima, energies))
            low_lying_set = {
                state
                for state, energy in energy_by_minimum.items()
                if energy <= ground_energy + low_energy_tolerance
            }
            metrics = summarize_basin_distribution(
                partition.basin_counts,
                landscape,
                reference_minima=set(minima),
                low_energy_tolerance_mhz=low_energy_tolerance,
            )
            barriers = (
                exact_barrier_merge_tree(landscape, max_spins=max_spins)
                if compute_barriers and len(minima) > 1
                else []
            )
            above_higher = [
                event.barrier_above_higher_minimum_mhz for event in barriers
            ]
            above_lower = [
                event.barrier_above_lower_minimum_mhz for event in barriers
            ]
            max_above_higher = max(above_higher, default=0.0)
            max_above_lower = max(above_lower, default=0.0)
            low_energy_barriers: list[float] = []
            for event in barriers:
                left_low = low_lying_set.intersection(event.left_minima)
                right_low = low_lying_set.intersection(event.right_minima)
                if not left_low or not right_low:
                    continue
                left_floor = min(energy_by_minimum[state] for state in left_low)
                right_floor = min(energy_by_minimum[state] for state in right_low)
                low_energy_barriers.append(
                    event.saddle_energy_mhz - max(left_floor, right_floor)
                )
            max_low_energy_barrier = max(low_energy_barriers, default=0.0)

            if descriptors.connected_components > 1:
                label = "reject_disconnected"
                note = "multiple first-shell components"
            elif len(minima) < 3:
                label = "simple_landscape"
                note = "fewer than three one-spin local minima"
            elif low_lying_minima < 2:
                label = "multibasin_single_low_energy_funnel"
                note = "multiple minima but only one lies in the low-energy window"
            elif (
                metrics["effective_basin_count"] >= minimum_effective_basins
                and max_low_energy_barrier >= barrier_threshold
            ):
                label = "rugged_low_energy_candidate"
                note = "passes low-energy multiplicity and barrier filters"
            else:
                label = "multibasin_candidate"
                note = "multiple minima, but not both screening thresholds"

            rows.append(
                {
                    **common,
                    "landscape_screen_label": label,
                    "screening_note": note,
                    "enumerated_states": 1 << geometry.n_atoms,
                    "local_minima": len(minima),
                    "ground_energy_mhz": ground_energy,
                    "ground_state_degeneracy": ground_degeneracy,
                    "low_lying_minima": low_lying_minima,
                    "local_minimum_energy_span_mhz": float(np.ptp(energies)),
                    "exact_basin_entropy_nats": metrics["shannon_entropy_nats"],
                    "exact_effective_basin_count": metrics[
                        "effective_basin_count"
                    ],
                    "largest_exact_basin_fraction": metrics["top_basin_mass"],
                    "exact_low_energy_basin_volume_fraction": metrics[
                        "low_energy_mass"
                    ],
                    "barrier_merges": len(barriers),
                    "low_energy_barrier_merges": len(low_energy_barriers),
                    "max_low_energy_barrier_mhz": max_low_energy_barrier,
                    "max_barrier_above_higher_minimum_mhz": max_above_higher,
                    "max_barrier_above_lower_minimum_mhz": max_above_lower,
                    "barrier_threshold_mhz": barrier_threshold,
                    "minimum_effective_basins_threshold": minimum_effective_basins,
                }
            )
    return rows
