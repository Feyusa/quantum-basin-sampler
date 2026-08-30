"""Shot inventory and host-timing conversion for a RUBY allocation request."""

from __future__ import annotations

from typing import Any


def _positive_int(value: Any, name: str) -> int:
    result = int(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _timing_estimate(
    *,
    shots: int,
    batches: int,
    timing: dict[str, Any],
) -> dict[str, Any]:
    cycle = float(timing["per_shot_cycle_seconds"])
    batch_overhead = float(timing["per_batch_overhead_seconds"])
    setup_hours = float(timing.get("setup_calibration_hours", 0.0))
    if min(cycle, batch_overhead, setup_hours) < 0:
        raise ValueError("timing values cannot be negative")
    shot_hours = shots * cycle / 3600.0
    batch_hours = batches * batch_overhead / 3600.0
    total = shot_hours + batch_hours + setup_hours
    return {
        "name": str(timing["name"]),
        "status": str(timing.get("status", "unspecified")),
        "source": timing.get("source"),
        "per_shot_cycle_seconds": cycle,
        "per_batch_overhead_seconds": batch_overhead,
        "setup_calibration_hours": setup_hours,
        "shot_cycle_hours": shot_hours,
        "batch_overhead_hours": batch_hours,
        "total_qpu_hours": total,
    }


def calculate_resource_budget(config: dict[str, Any]) -> dict[str, Any]:
    """Calculate shots/batches and convert them under supplied timing models."""
    design = config["science_design"]
    geometries = _positive_int(design["geometries"], "geometries")
    pulse_points = _positive_int(
        design["pulse_points_per_geometry"], "pulse_points_per_geometry"
    )
    replicates = _positive_int(design["replicates"], "replicates")
    shots_per_run = _positive_int(design["shots_per_run"], "shots_per_run")
    science_batches = geometries * pulse_points * replicates
    science_shots = science_batches * shots_per_run
    expected = design.get("expected_science_shots")
    if expected is not None and int(expected) != science_shots:
        raise ValueError(
            f"science design gives {science_shots} shots, not expected {expected}"
        )

    items = [
        {
            "name": "predeclared_science_grid",
            "purpose": "primary controlled nonadiabatic experiment",
            "batches": science_batches,
            "shots_per_batch": shots_per_run,
            "shots": science_shots,
        }
    ]
    for raw in config.get("additional_batches", []):
        batches = _positive_int(raw["batches"], f"{raw['name']}.batches")
        per_batch = _positive_int(
            raw["shots_per_batch"], f"{raw['name']}.shots_per_batch"
        )
        items.append(
            {
                "name": str(raw["name"]),
                "purpose": str(raw["purpose"]),
                "batches": batches,
                "shots_per_batch": per_batch,
                "shots": batches * per_batch,
            }
        )

    total_batches = sum(item["batches"] for item in items)
    total_shots = sum(item["shots"] for item in items)
    additional_shots = total_shots - science_shots
    timing_models = [
        _timing_estimate(shots=total_shots, batches=total_batches, timing=model)
        for model in config.get("timing_sensitivity_models", [])
    ]

    host = config.get("host_verified_timing_model", {})
    host_fields = (
        host.get("per_shot_cycle_seconds"),
        host.get("per_batch_overhead_seconds"),
        host.get("setup_calibration_hours"),
    )
    host_estimate = None
    if all(value is not None for value in host_fields):
        host_estimate = _timing_estimate(
            shots=total_shots,
            batches=total_batches,
            timing={"name": "host_verified", "status": "host_verified", **host},
        )

    return {
        "experiment": str(config.get("experiment", "ruby_resource_budget")),
        "inventory": items,
        "science_batches": science_batches,
        "science_shots": science_shots,
        "additional_batches": total_batches - science_batches,
        "additional_shots": additional_shots,
        "additional_shot_fraction": additional_shots / science_shots,
        "total_batches": total_batches,
        "total_shots": total_shots,
        "qpu_hour_formula": (
            "(total_shots * per_shot_cycle_seconds + total_batches * "
            "per_batch_overhead_seconds) / 3600 + setup_calibration_hours"
        ),
        "host_verified_estimate": host_estimate,
        "allocation_status": (
            "ready_from_host_verified_model"
            if host_estimate
            else "pending_host_per_shot_and_per_batch_timing"
        ),
        "timing_sensitivity_models": timing_models,
        "notes": list(config.get("notes", [])),
    }

