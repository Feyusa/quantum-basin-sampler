# Geometry and structure taxonomy

The taxonomy separates how frustration/ruggedness is introduced from what is
later observed dynamically.  “Glassy candidate” is therefore a screening
label, never a phase diagnosis.

| Family | Generator | Main ingredient | Role | Main risk |
|---|---|---|---|---|
| Clean Kagome | `kagome` | Corner-sharing triangles, odd cycles | Canonical geometric-frustration target | Finite open patches can order or have strong boundary bias |
| Clean triangular | `triangular` | Dense odd cycles, higher coordination | Frustrated control with stronger local constraints | May form simple ordered sublattices rather than a rugged ensemble |
| Clean square | `square` | Connected bipartite first-shell graph | Negative control for odd-cycle frustration | Long-range Rydberg tails still extend beyond the bipartite first shell |
| Defected Kagome | `vacancy_kagome` | Site dilution on a frustrated parent | Tests rare regions and defect-induced basins | A vacancy can disconnect a small patch |
| Jittered Kagome | `jittered_kagome` | Correlated positional/bond disorder | Intermediate step between clean and amorphous arrays | Disorder may be too weak, or hardware spacing may be violated |
| Amorphous | `amorphous` | Positional disorder plus random interaction graph | Strongest native candidate for rugged sampling | Connectivity and coordination vary; requires ensemble averaging |

## Computed descriptors

- `min_distance_um`: immediate hardware filter.
- `connected_components`: reject unintended disconnected problems.
- `mean_degree`, `max_degree`, `degree_variance`: constraint density and hubs.
- `triangles`: local odd-cycle frustration indicator.
- `cycle_rank = E-N+C`: number of independent graph cycles.
- `bipartite` / `has_odd_cycle`: whether every antiferromagnetic edge can be
  satisfied by a two-sublattice assignment.
- `nearest_distance_cv`: positional disorder proxy.
- `bond_strength_cv`: variation of the first-shell `1/r^6` couplings.
- `screening_label`: transparent structural role/rejection label; never a
  thermodynamic phase label.

These graph descriptors use a first-shell distance cutoff.  Rydberg
interactions are long-ranged, so all energy calculations still retain every
pairwise `C6/r^6` interaction.

## Candidate selection stages

### Stage 1 — hardware and graph filters

- one connected component;
- no spacing/radial violations;
- no unintended super-connected hub;
- reproducible coordinates and seed;
- at least one odd cycle for geometric-frustration studies.

### Stage 2 — exact small-system landscape filters

- number of one-spin local minima;
- exact basin volumes and their concentration;
- energy spread of low-lying minima;
- zero-energy connectivity between degenerate minima;
- minimax one-spin barrier hierarchy;
- sensitivity to deterministic versus randomized descent.

Run this stage with `qbasin screen`. Its `rugged_low_energy_candidate` label
requires at least two minima in the configured low-energy window and a
configurable minimax barrier between low-energy branches. The thresholds are
selection rules, not proof of a spin-glass phase.

### Stage 3 — sampling filters

- nontrivial effective basin count;
- meaningful low-energy/diversity trade-off;
- robustness across shot bootstrap and random seeds;
- quantum/classical complementarity not explained by a trivial density bias;
- persistence across neighboring pulse points rather than a single outlier.

## Clean versus disordered claims

A clean non-bipartite geometry can be frustrated without being a spin glass.
Amorphous arrays add quenched positional disorder, but a spin-glass claim still
requires replica observables, disorder averaging, and size scaling.  The
optimization-sampler project can use all of these families without claiming a
thermodynamic glass phase.
