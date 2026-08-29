"""Hardware-aware geometry generation and structural classification.

The names in this module describe geometry families, not thermodynamic phases.
In particular, a non-bipartite or disordered interaction graph is only a
candidate for rugged/glassy behavior; it is not evidence of a spin glass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Geometry:
    """A labelled two-dimensional atom geometry in micrometres."""

    name: str
    coordinates: np.ndarray
    family: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        coordinates = np.asarray(self.coordinates, dtype=float)
        if coordinates.ndim != 2 or coordinates.shape[1] != 2:
            raise ValueError("coordinates must have shape (N, 2)")
        if len(coordinates) == 0:
            raise ValueError("a geometry must contain at least one atom")
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("coordinates must be finite")
        object.__setattr__(self, "coordinates", coordinates)

    @property
    def n_atoms(self) -> int:
        return int(len(self.coordinates))

    @property
    def qubit_ids(self) -> tuple[str, ...]:
        return tuple(f"q{i}" for i in range(self.n_atoms))

    def centered(self) -> "Geometry":
        return Geometry(
            name=self.name,
            coordinates=self.coordinates - self.coordinates.mean(axis=0),
            family=self.family,
            metadata=dict(self.metadata),
        )

    def to_register(self):
        """Create a Pulser Register without importing Pulser at module import."""
        from pulser import Register

        mapping = {
            qid: (float(x), float(y))
            for qid, (x, y) in zip(self.qubit_ids, self.coordinates)
        }
        return Register(mapping)


@dataclass(frozen=True)
class GeometryDescriptors:
    """Graph/position descriptors used to classify geometry candidates."""

    name: str
    family: str
    n_atoms: int
    graph_cutoff_um: float
    min_distance_um: float
    median_nearest_distance_um: float
    nearest_distance_cv: float
    edges: int
    connected_components: int
    mean_degree: float
    max_degree: int
    degree_variance: float
    triangles: int
    cycle_rank: int
    bipartite: bool
    has_odd_cycle: bool
    bond_strength_cv: float
    structural_class: str
    screening_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _select_nearest(points: list[tuple[Any, ...]], n_atoms: int) -> np.ndarray:
    if n_atoms <= 0 or n_atoms > len(points):
        raise ValueError("n_atoms is outside the generated candidate range")
    points.sort(key=lambda item: (round(float(item[0]), 12), *item[1:-1]))
    coordinates = np.asarray([item[-1] for item in points[:n_atoms]], dtype=float)
    return coordinates - coordinates.mean(axis=0)


def kagome_patch(n_atoms: int = 13, spacing: float = 5.0) -> Geometry:
    """Finite patch of a genuine Kagome lattice (corner-sharing triangles)."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    root3 = np.sqrt(3.0)
    a1 = np.array([2.0 * spacing, 0.0])
    a2 = np.array([spacing, root3 * spacing])
    basis = (
        np.array([0.0, 0.0]),
        np.array([spacing, 0.0]),
        np.array([0.5 * spacing, 0.5 * root3 * spacing]),
    )
    extent = max(4, int(np.ceil(np.sqrt(n_atoms))) + 2)
    candidates: list[tuple[Any, ...]] = []
    for m in range(-extent, extent + 1):
        for n in range(-extent, extent + 1):
            for basis_index, offset in enumerate(basis):
                point = m * a1 + n * a2 + offset
                candidates.append((float(point @ point), m, n, basis_index, point))
    coordinates = _select_nearest(candidates, n_atoms)
    return Geometry(
        name=f"kagome_n{n_atoms}",
        coordinates=coordinates,
        family="clean_kagome",
        metadata={"spacing_um": spacing, "disorder": "none"},
    )


def triangular_patch(n_atoms: int = 13, spacing: float = 5.0) -> Geometry:
    """Finite triangular-lattice patch with abundant odd cycles."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    root3 = np.sqrt(3.0)
    a1 = np.array([spacing, 0.0])
    a2 = np.array([0.5 * spacing, 0.5 * root3 * spacing])
    extent = max(4, int(np.ceil(np.sqrt(n_atoms))) + 2)
    candidates: list[tuple[Any, ...]] = []
    for m in range(-extent, extent + 1):
        for n in range(-extent, extent + 1):
            point = m * a1 + n * a2
            candidates.append((float(point @ point), m, n, point))
    coordinates = _select_nearest(candidates, n_atoms)
    return Geometry(
        name=f"triangular_n{n_atoms}",
        coordinates=coordinates,
        family="clean_triangular",
        metadata={"spacing_um": spacing, "disorder": "none"},
    )


def square_patch(n_atoms: int = 12, spacing: float = 5.0) -> Geometry:
    """Finite square-lattice patch used as a connected bipartite control."""
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    extent = max(4, int(np.ceil(np.sqrt(n_atoms))) + 2)
    candidates: list[tuple[Any, ...]] = []
    for row in range(-extent, extent + 1):
        for column in range(-extent, extent + 1):
            point = spacing * np.array([column, row], dtype=float)
            candidates.append((float(point @ point), row, column, point))
    coordinates = _select_nearest(candidates, n_atoms)
    return Geometry(
        name=f"square_n{n_atoms}",
        coordinates=coordinates,
        family="clean_square_control",
        metadata={"spacing_um": spacing, "disorder": "none"},
    )


def jittered_kagome_patch(
    n_atoms: int = 13,
    spacing: float = 6.0,
    jitter_fraction: float = 0.08,
    min_distance: float = 5.0,
    seed: int = 0,
    max_attempts: int = 500,
    require_connected: bool = False,
) -> Geometry:
    """Kagome-derived bond disorder while preserving a minimum separation."""
    if not 0 <= jitter_fraction < 0.5:
        raise ValueError("jitter_fraction must be in [0, 0.5)")
    if min_distance <= 0:
        raise ValueError("min_distance must be positive")
    base = kagome_patch(n_atoms=n_atoms, spacing=spacing)
    rng = np.random.default_rng(seed)
    scale = jitter_fraction * spacing
    for _ in range(max_attempts):
        candidate = base.coordinates + rng.normal(0.0, scale, base.coordinates.shape)
        candidate -= candidate.mean(axis=0)
        distances = _pair_distances(candidate)
        if np.min(distances[np.triu_indices(n_atoms, 1)]) >= min_distance:
            geometry = Geometry(
                name=f"jittered_kagome_n{n_atoms}_seed{seed}",
                coordinates=candidate,
                family="bond_disordered_kagome",
                metadata={
                    "spacing_um": spacing,
                    "jitter_fraction": jitter_fraction,
                    "min_distance_um": min_distance,
                    "seed": seed,
                    "require_connected": require_connected,
                    "disorder": "positional_correlated",
                },
            )
            if not require_connected or classify_geometry(
                geometry
            ).connected_components == 1:
                return geometry
    raise RuntimeError(
        "could not generate a jittered Kagome patch satisfying min_distance; "
        "increase spacing or reduce jitter_fraction"
    )


def vacancy_kagome_patch(
    n_atoms: int = 12,
    spacing: float = 5.0,
    vacancies: int = 1,
    seed: int = 0,
) -> Geometry:
    """Kagome patch with reproducible site vacancies/defects."""
    if vacancies <= 0:
        raise ValueError("vacancies must be positive")
    parent = kagome_patch(n_atoms=n_atoms + vacancies, spacing=spacing)
    rng = np.random.default_rng(seed)
    radii = np.linalg.norm(parent.coordinates, axis=1)
    # Prefer removing non-boundary sites so the defect changes local constraints.
    interior = np.argsort(radii)[: max(vacancies, len(radii) // 2)]
    removed = set(int(i) for i in rng.choice(interior, size=vacancies, replace=False))
    kept = np.array(
        [point for i, point in enumerate(parent.coordinates) if i not in removed]
    )
    kept -= kept.mean(axis=0)
    return Geometry(
        name=f"vacancy_kagome_n{n_atoms}_v{vacancies}_seed{seed}",
        coordinates=kept,
        family="defected_kagome",
        metadata={
            "spacing_um": spacing,
            "vacancies": vacancies,
            "seed": seed,
            "removed_parent_indices": sorted(removed),
            "disorder": "site_dilution",
        },
    )


def random_geometric_patch(
    n_atoms: int = 13,
    radius: float = 14.0,
    min_distance: float = 5.0,
    seed: int = 0,
    max_attempts: int = 200_000,
    require_connected: bool = False,
) -> Geometry:
    """Poisson-disk-like amorphous candidate in a circular trapping region.

    When ``require_connected`` is true, disconnected first-shell graphs are
    rejected and sampling restarts. This prevents an apparently complicated
    point cloud from being mistaken for one interacting glassy system.
    """
    if n_atoms <= 0 or radius <= 0 or min_distance <= 0:
        raise ValueError("n_atoms, radius and min_distance must be positive")
    rng = np.random.default_rng(seed)
    points: list[np.ndarray] = []
    for _ in range(max_attempts):
        radial = radius * np.sqrt(rng.random())
        angle = 2.0 * np.pi * rng.random()
        point = radial * np.array([np.cos(angle), np.sin(angle)])
        if all(np.linalg.norm(point - old) >= min_distance for old in points):
            points.append(point)
            if len(points) == n_atoms:
                coordinates = np.asarray(points)
                coordinates -= coordinates.mean(axis=0)
                candidate = Geometry(
                    name=f"amorphous_n{n_atoms}_seed{seed}",
                    coordinates=coordinates,
                    family="amorphous_random_geometric",
                    metadata={
                        "radius_um": radius,
                        "min_distance_um": min_distance,
                        "seed": seed,
                        "require_connected": require_connected,
                        "disorder": "positional_amorphous",
                    },
                )
                if not require_connected or classify_geometry(
                    candidate
                ).connected_components == 1:
                    return candidate
                points = []
    raise RuntimeError(
        "failed to pack requested atoms; increase radius or lower min_distance"
    )


def build_geometry(spec: dict[str, Any]) -> Geometry:
    """Build one geometry from a JSON-serializable specification."""
    spec = dict(spec)
    kind = str(spec.pop("kind"))
    factories = {
        "kagome": kagome_patch,
        "triangular": triangular_patch,
        "square": square_patch,
        "jittered_kagome": jittered_kagome_patch,
        "vacancy_kagome": vacancy_kagome_patch,
        "amorphous": random_geometric_patch,
    }
    if kind not in factories:
        raise ValueError(f"unknown geometry kind {kind!r}; choose {sorted(factories)}")
    return factories[kind](**spec)


def _pair_distances(coordinates: np.ndarray) -> np.ndarray:
    displacement = coordinates[:, None, :] - coordinates[None, :, :]
    return np.linalg.norm(displacement, axis=2)


def _components_and_bipartite(adjacency: np.ndarray) -> tuple[int, bool]:
    n_atoms = len(adjacency)
    colors = np.full(n_atoms, -1, dtype=int)
    components = 0
    bipartite = True
    for start in range(n_atoms):
        if colors[start] >= 0:
            continue
        components += 1
        colors[start] = 0
        queue = [start]
        while queue:
            node = queue.pop()
            for neighbour in np.flatnonzero(adjacency[node]):
                neighbour = int(neighbour)
                if colors[neighbour] < 0:
                    colors[neighbour] = 1 - colors[node]
                    queue.append(neighbour)
                elif colors[neighbour] == colors[node]:
                    bipartite = False
    return components, bipartite


def classify_geometry(
    geometry: Geometry,
    graph_cutoff: float | None = None,
) -> GeometryDescriptors:
    """Classify structural ingredients relevant to frustrated sampling.

    The graph is defined by a distance cutoff.  If omitted, the cutoff is 1.2
    times the median nearest-neighbour distance, which usually isolates the
    first coordination shell while remaining tolerant to mild disorder.
    """
    distances = _pair_distances(geometry.coordinates)
    masked = np.where(np.eye(geometry.n_atoms, dtype=bool), np.inf, distances)
    nearest = masked.min(axis=1)
    median_nearest = float(np.median(nearest))
    cutoff = float(graph_cutoff or 1.2 * median_nearest)
    adjacency = (distances <= cutoff) & (~np.eye(geometry.n_atoms, dtype=bool))
    degrees = adjacency.sum(axis=1)
    edges = int(degrees.sum() // 2)
    components, bipartite = _components_and_bipartite(adjacency)
    triangles = int(round(float(np.trace(adjacency.astype(int) @ adjacency.astype(int) @ adjacency.astype(int))) / 6.0))
    cycle_rank = int(max(0, edges - geometry.n_atoms + components))

    upper = np.triu_indices(geometry.n_atoms, 1)
    edge_mask = adjacency[upper]
    edge_distances = distances[upper][edge_mask]
    bond_strengths = 1.0 / edge_distances**6 if len(edge_distances) else np.array([])
    bond_cv = (
        float(np.std(bond_strengths) / np.mean(bond_strengths))
        if len(bond_strengths) and np.mean(bond_strengths) > 0
        else 0.0
    )
    nearest_cv = float(np.std(nearest) / np.mean(nearest))

    if geometry.family.startswith("amorphous"):
        structural_class = "amorphous_positional_disorder"
    elif "disordered" in geometry.family:
        structural_class = "correlated_bond_disorder"
    elif "defected" in geometry.family:
        structural_class = "site_disorder_on_frustrated_parent"
    elif not bipartite:
        structural_class = "clean_geometric_frustration"
    else:
        structural_class = "clean_bipartite_control"

    if components > 1:
        screening_label = "reject_disconnected"
    elif bipartite:
        screening_label = "connected_bipartite_control"
    elif geometry.family.startswith("amorphous") or "disordered" in geometry.family:
        screening_label = "disordered_frustrated_candidate"
    elif "defected" in geometry.family:
        screening_label = "defected_frustrated_candidate"
    else:
        screening_label = "clean_frustrated_candidate"

    return GeometryDescriptors(
        name=geometry.name,
        family=geometry.family,
        n_atoms=geometry.n_atoms,
        graph_cutoff_um=cutoff,
        min_distance_um=float(distances[upper].min()),
        median_nearest_distance_um=median_nearest,
        nearest_distance_cv=nearest_cv,
        edges=edges,
        connected_components=components,
        mean_degree=float(np.mean(degrees)),
        max_degree=int(np.max(degrees)),
        degree_variance=float(np.var(degrees)),
        triangles=triangles,
        cycle_rank=cycle_rank,
        bipartite=bipartite,
        has_odd_cycle=not bipartite,
        bond_strength_cv=bond_cv,
        structural_class=structural_class,
        screening_label=screening_label,
    )
