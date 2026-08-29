"""End-to-end quantum/classical parameter-scan experiment runner."""

from __future__ import annotations

import hashlib
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from qbasin.basins import (
    basin_table,
    exact_basin_partition,
    map_samples_to_basins,
    overlap_distribution,
)
from qbasin.classical import ClassicalSampleResult, run_classical_sampler
from qbasin.devices import RUBY_PROXY, geometry_issues, pulse_issues
from qbasin.geometry import Geometry, build_geometry, classify_geometry
from qbasin.hierarchy import (
    exact_barrier_merge_tree,
    hamming_linkage,
    pairwise_basin_relations,
)
from qbasin.io import flatten, read_json, write_csv, write_json
from qbasin.landscape import IsingLandscape
from qbasin.metrics import (
    bootstrap_metric_intervals,
    compare_basin_distributions,
    summarize_basin_distribution,
)
from qbasin.plotting import (
    plot_hamming_dendrogram,
    plot_overlap_comparison,
    plot_scan_metrics,
)
from qbasin.pulse import PulseParameters, expand_pulse_grid
from qbasin.quantum import simulate_quantum_samples


def _stable_seed(base_seed: int, *parts: Any) -> int:
    payload = "|".join([str(base_seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def _probabilities(counts: Counter[str]) -> dict[str, float]:
    total = sum(counts.values())
    return {state: count / total for state, count in counts.items()}


def _landscape_key(geometry: Geometry, pulse: PulseParameters) -> str:
    return f"{geometry.name}__delta_{pulse.delta_target_mhz:+.6g}MHz"


_PRIMARY_INTERVAL_METRICS = (
    "effective_basin_count",
    "normalized_entropy",
    "mean_energy_mhz",
    "mean_pairwise_hamming",
    "low_energy_mass",
)


def _interval_columns(bootstrap: dict[str, Any] | None) -> dict[str, float | None]:
    """Flatten selected bootstrap bounds into analysis-friendly CSV columns."""
    columns: dict[str, float | None] = {}
    intervals = bootstrap["intervals"] if bootstrap else {}
    for metric in _PRIMARY_INTERVAL_METRICS:
        interval = intervals.get(metric)
        columns[f"{metric}_ci_lower"] = interval["lower"] if interval else None
        columns[f"{metric}_ci_upper"] = interval["upper"] if interval else None
    return columns


def validate_configuration(config: dict[str, Any]) -> dict[str, Any]:
    """Validate structure and report provisional hardware issues without running."""
    device_profile = str(config.get("device_profile", "ruby_proxy"))
    geometries = [build_geometry(spec) for spec in config["geometries"]]
    pulses = expand_pulse_grid(config["pulse_grid"])
    replicates = int(config.get("replicates", 1))
    if replicates <= 0:
        raise ValueError("replicates must be positive")
    report: dict[str, Any] = {
        "device_profile": device_profile,
        "ruby_proxy": RUBY_PROXY.to_dict(),
        "geometries": [],
        "pulse_points": len(pulses),
        "replicates": replicates,
        "total_quantum_runs": len(geometries) * len(pulses) * replicates,
    }
    for geometry in geometries:
        descriptors = classify_geometry(geometry)
        screening_warnings: list[str] = []
        if descriptors.connected_components > 1:
            screening_warnings.append("first-shell interaction graph is disconnected")
        if not descriptors.has_odd_cycle:
            screening_warnings.append(
                "no odd cycle in first-shell graph; treat as a control"
            )
        report["geometries"].append(
            {
                "name": geometry.name,
                "descriptors": descriptors.to_dict(),
                "ruby_proxy_issues": geometry_issues(geometry),
                "scientific_screening_warnings": screening_warnings,
            }
        )
    report["pulse_issues"] = [
        {"pulse": pulse.to_dict(), "issues": pulse_issues(pulse)}
        for pulse in pulses
        if pulse_issues(pulse)
    ]
    report["valid_for_proxy"] = not any(
        entry["ruby_proxy_issues"] for entry in report["geometries"]
    ) and not report["pulse_issues"]
    return report


def _write_exact_landscape_artifacts(
    output_dir: Path,
    key: str,
    landscape: IsingLandscape,
    exact_partition,
    *,
    compute_barriers: bool,
) -> None:
    reference_counts = exact_partition.basin_counts
    payload: dict[str, Any] = {
        "landscape_key": key,
        "n_spins": landscape.n_spins,
        "delta_rad_per_us": landscape.delta_rad_per_us,
        "delta_mhz": landscape.delta_rad_per_us / (2.0 * np.pi),
        "exact_partition": exact_partition.metadata(),
        "basins": basin_table(reference_counts, landscape),
        "overlap_distribution": overlap_distribution(
            reference_counts, landscape.n_spins
        ),
    }
    if compute_barriers:
        payload["barrier_merge_tree"] = [
            event.to_dict() for event in exact_barrier_merge_tree(landscape)
        ]
    write_json(output_dir / "landscapes" / f"{key}.json", payload)


def run_experiment(config_path: Path, output_dir: Path) -> dict[str, Any]:
    """Execute every configured geometry/pulse point and matched baseline."""
    config = read_json(config_path)
    validation = validate_configuration(config)
    if config.get("require_ruby_proxy", True) and not validation["valid_for_proxy"]:
        raise ValueError(
            "configuration violates the provisional RUBY proxy; run `qbasin "
            "validate` for details or explicitly set require_ruby_proxy=false"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "configuration.json", config)
    write_json(output_dir / "validation.json", validation)
    base_seed = int(config.get("seed", 7))
    shots = int(config.get("shots", 1_000))
    device_profile = str(config.get("device_profile", "ruby_proxy"))
    exact_limit = int(config.get("exact_analysis_max_spins", 16))
    compute_barriers = bool(config.get("compute_exact_barriers", True))
    replicates = int(config.get("replicates", 1))
    bootstrap_resamples = int(config.get("bootstrap_resamples", 0))
    confidence_level = float(config.get("confidence_level", 0.95))
    if bootstrap_resamples < 0:
        raise ValueError("bootstrap_resamples cannot be negative")
    descent_rule = str(config.get("descent_rule", "steepest"))
    classical_specs = list(config.get("classical_baselines", []))
    geometries = [build_geometry(spec) for spec in config["geometries"]]
    pulses = expand_pulse_grid(config["pulse_grid"])

    taxonomy_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    exact_cache: dict[str, Any] = {}
    classical_cache: dict[
        tuple[str, str, int], tuple[ClassicalSampleResult, Any]
    ] = {}

    for geometry_index, geometry in enumerate(geometries):
        descriptors = classify_geometry(geometry)
        taxonomy_rows.append(descriptors.to_dict())
        write_json(
            output_dir / "geometries" / f"{geometry.name}.json",
            {
                "name": geometry.name,
                "family": geometry.family,
                "coordinates_um": geometry.coordinates,
                "metadata": geometry.metadata,
                "descriptors": descriptors.to_dict(),
            },
        )

        run_points = (
            (pulse_index, pulse, replicate_index)
            for pulse_index, pulse in enumerate(pulses)
            for replicate_index in range(replicates)
        )
        for pulse_index, pulse, replicate_index in run_points:
            run_id = f"g{geometry_index:02d}_p{pulse_index:03d}"
            if replicates > 1:
                run_id += f"_r{replicate_index:02d}"
            landscape = IsingLandscape.from_geometry(
                geometry,
                delta_rad_per_us=pulse.delta_target_rad_per_us,
                device_profile=device_profile,
            )
            landscape_key = _landscape_key(geometry, pulse)
            if landscape_key not in exact_cache and geometry.n_atoms <= exact_limit:
                exact_cache[landscape_key] = exact_basin_partition(
                    landscape, rule=descent_rule, max_spins=exact_limit
                )
                _write_exact_landscape_artifacts(
                    output_dir,
                    landscape_key,
                    landscape,
                    exact_cache[landscape_key],
                    compute_barriers=compute_barriers,
                )
            exact_partition = exact_cache.get(landscape_key)
            reference_minima = (
                set(exact_partition.basin_counts) if exact_partition else None
            )

            quantum_seed = _stable_seed(base_seed, run_id, "quantum")
            quantum = simulate_quantum_samples(
                geometry,
                pulse,
                shots=shots,
                device_profile=device_profile,
                seed=quantum_seed,
            )
            quantum_mapping = map_samples_to_basins(
                quantum.counts,
                landscape,
                rule=descent_rule,
                seed=_stable_seed(base_seed, run_id, "quantum_descent"),
            )
            quantum_metrics = summarize_basin_distribution(
                quantum_mapping.basin_counts,
                landscape,
                reference_minima=reference_minima,
            )
            quantum_bootstrap = (
                bootstrap_metric_intervals(
                    quantum_mapping.basin_counts,
                    landscape,
                    reference_minima=reference_minima,
                    resamples=bootstrap_resamples,
                    confidence_level=confidence_level,
                    seed=_stable_seed(base_seed, run_id, "quantum_bootstrap"),
                )
                if bootstrap_resamples
                else None
            )
            quantum_overlap = overlap_distribution(
                quantum_mapping.basin_counts, landscape.n_spins
            )
            quantum_hierarchy = hamming_linkage(quantum_mapping.basin_counts)
            quantum_probabilities = _probabilities(quantum_mapping.basin_counts)

            run_payload: dict[str, Any] = {
                "run_id": run_id,
                "replicate": replicate_index,
                "geometry": geometry.name,
                "geometry_descriptors": descriptors.to_dict(),
                "pulse": pulse.to_dict(),
                "landscape_key": landscape_key,
                "quantum": {
                    "metadata": quantum.metadata(),
                    "raw_counts": quantum.counts,
                    "basin_mapping": quantum_mapping.metadata(),
                    "basin_counts": quantum_mapping.basin_counts,
                    "basin_table": basin_table(
                        quantum_mapping.basin_counts, landscape
                    ),
                    "metrics": quantum_metrics,
                    "bootstrap": quantum_bootstrap,
                    "overlap_distribution": quantum_overlap,
                    "hamming_hierarchy": quantum_hierarchy,
                    "pairwise_relations": pairwise_basin_relations(
                        quantum_mapping.basin_counts, landscape
                    ),
                },
                "classical_baselines": {},
            }

            common = {
                "run_id": run_id,
                "geometry": geometry.name,
                "family": geometry.family,
                "n_atoms": geometry.n_atoms,
                "device_profile": device_profile,
                "replicate": replicate_index,
                "omega_mhz": pulse.omega_mhz,
                "delta_initial_mhz": pulse.delta_initial_mhz,
                "delta_target_mhz": pulse.delta_target_mhz,
                "delta_over_omega": pulse.delta_over_omega,
                "sweep_ns": pulse.sweep_ns,
                "hold_ns": pulse.hold_ns,
                "fall_ns": pulse.fall_ns,
                "sweep_rate_mhz_per_us": pulse.sweep_rate_mhz_per_us,
                "blockade_ratio": quantum.blockade_ratio,
            }
            summary_rows.append(
                {
                    **common,
                    "method": "quantum",
                    **quantum_metrics,
                    **_interval_columns(quantum_bootstrap),
                    "wall_seconds": quantum.wall_seconds,
                    "generation_energy_evaluations": None,
                    "descent_flip_cost_evaluations": quantum_mapping.descent_flip_cost_evaluations,
                }
            )

            overlap_panels: dict[str, dict[float, float]] = {
                "quantum": quantum_overlap
            }
            for baseline_index, baseline_spec in enumerate(classical_specs):
                baseline_name = str(baseline_spec["name"])
                cache_key = (landscape_key, baseline_name, replicate_index)
                if cache_key not in classical_cache:
                    baseline = run_classical_sampler(
                        landscape,
                        deepcopy(baseline_spec),
                        n_samples=shots,
                        seed=_stable_seed(
                            base_seed,
                            landscape_key,
                            baseline_name,
                            baseline_index,
                            replicate_index,
                        ),
                    )
                    mapping = map_samples_to_basins(
                        baseline.counts,
                        landscape,
                        rule=descent_rule,
                        seed=_stable_seed(
                            base_seed,
                            landscape_key,
                            baseline_name,
                            replicate_index,
                            "descent",
                        ),
                    )
                    classical_cache[cache_key] = (baseline, mapping)
                baseline, mapping = classical_cache[cache_key]
                baseline_metrics = summarize_basin_distribution(
                    mapping.basin_counts,
                    landscape,
                    reference_minima=reference_minima,
                )
                baseline_bootstrap = (
                    bootstrap_metric_intervals(
                        mapping.basin_counts,
                        landscape,
                        reference_minima=reference_minima,
                        resamples=bootstrap_resamples,
                        confidence_level=confidence_level,
                        seed=_stable_seed(
                            base_seed,
                            landscape_key,
                            baseline_name,
                            replicate_index,
                            "bootstrap",
                        ),
                    )
                    if bootstrap_resamples
                    else None
                )
                comparison = compare_basin_distributions(
                    quantum_mapping.basin_counts, mapping.basin_counts
                )
                baseline_overlap = overlap_distribution(
                    mapping.basin_counts, landscape.n_spins
                )
                overlap_panels[baseline_name] = baseline_overlap
                run_payload["classical_baselines"][baseline_name] = {
                    "metadata": baseline.metadata(),
                    "raw_counts": baseline.counts,
                    "basin_mapping": mapping.metadata(),
                    "basin_counts": mapping.basin_counts,
                    "basin_table": basin_table(mapping.basin_counts, landscape),
                    "metrics": baseline_metrics,
                    "bootstrap": baseline_bootstrap,
                    "overlap_distribution": baseline_overlap,
                    "comparison_with_quantum": comparison,
                }
                summary_rows.append(
                    {
                        **common,
                        "method": baseline_name,
                        **baseline_metrics,
                        **_interval_columns(baseline_bootstrap),
                        "wall_seconds": baseline.wall_seconds,
                        "generation_energy_evaluations": baseline.energy_difference_evaluations,
                        "descent_flip_cost_evaluations": mapping.descent_flip_cost_evaluations,
                    }
                )
                comparison_rows.append(
                    {
                        **common,
                        "baseline": baseline_name,
                        **comparison,
                        **flatten("quantum_", quantum_metrics),
                        **flatten("baseline_", baseline_metrics),
                    }
                )

            write_json(output_dir / "runs" / f"{run_id}.json", run_payload)
            plot_overlap_comparison(
                overlap_panels,
                n_spins=landscape.n_spins,
                path=output_dir / "plots" / f"{run_id}_overlaps.png",
                title=(
                    f"{geometry.name}: delta={pulse.delta_target_mhz:g} MHz, "
                    f"sweep={pulse.sweep_ns} ns, hold={pulse.hold_ns} ns"
                ),
            )
            plot_hamming_dendrogram(
                quantum_hierarchy,
                probabilities=quantum_probabilities,
                path=output_dir / "plots" / f"{run_id}_quantum_hierarchy.png",
                title=f"Quantum-sampled basin hierarchy: {run_id}",
            )

    write_csv(output_dir / "geometry_taxonomy.csv", taxonomy_rows)
    write_csv(output_dir / "summary.csv", summary_rows)
    write_csv(output_dir / "comparisons.csv", comparison_rows)
    for geometry in geometries:
        plot_scan_metrics(
            summary_rows,
            path=output_dir / "plots" / f"{geometry.name}_scan.png",
            geometry_name=geometry.name,
        )

    manifest = {
        "experiment_name": config.get("experiment_name", config_path.stem),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": str(config_path),
        "output_directory": str(output_dir),
        "device_profile": device_profile,
        "shots_per_method": shots,
        "geometries": [geometry.name for geometry in geometries],
        "pulse_points_per_geometry": len(pulses),
        "replicates": replicates,
        "quantum_runs": len(geometries) * len(pulses) * replicates,
        "bootstrap_resamples": bootstrap_resamples,
        "classical_baselines": [spec["name"] for spec in classical_specs],
        "artifacts": {
            "summary": "summary.csv",
            "comparisons": "comparisons.csv",
            "taxonomy": "geometry_taxonomy.csv",
            "runs": "runs/",
            "landscapes": "landscapes/",
            "plots": "plots/",
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest
