# Quantum Basin Sampler

Research code for comparing quantum-induced and classical sampling of basins
in frustrated neutral-atom Ising landscapes.  The immediate target is a
EuroHPC Quantum Pilot Access proposal for the 100-atom RUBY neutral-atom
processor.  This repository currently runs simulations only; it does **not**
claim to reproduce the final RUBY control stack or calibration.

## Scientific question

Does controlled nonadiabatic Rydberg dynamics produce a reproducible
quality–diversity trade-off that differs from matched classical samplers?

The project does not assume that a useful result must have a U-shaped overlap
distribution, and a distributional difference alone is not called an
advantage.  A candidate sampling benefit requires better low-energy mass,
basin coverage, solution diversity, rare-basin discovery, or downstream
classical performance at a clearly stated resource budget.

## What is implemented

- Conservative `ruby_proxy`, Pulser `AnalogDevice`, and permissive
  `MockDevice` simulation profiles.
- Controlled rise–sweep–hold–freeze pulse protocol and Cartesian parameter
  scans over `Omega`, target detuning, sweep time, and hold time.
- Clean Kagome and triangular patches, a square-lattice negative control,
  vacancy defects, jittered Kagome bond disorder, and connected amorphous
  random-geometric arrays.
- Structural taxonomy: degree statistics, components, triangles, cycle rank,
  bipartiteness, and geometric/bond disorder.
- Exact Qutip sampling for small systems using Pulser's current
  `QutipBackendV2` API.
- Uniform-random, Metropolis, simulated-annealing, and parallel-tempering
  baselines with explicit energy-difference evaluation counts.
- Common one-spin descent for every method.
- Basin entropy, effective basin count, overlap, Hamming diversity,
  low-energy mass, coverage, and distribution distances.
- Hamming dendrograms for sampled basins.
- Exact enumeration, basin volumes, and one-spin minimax barrier merge trees
  for small landscapes.
- Exact pre-emulation landscape screening, independent run replicates, and
  multinomial finite-shot bootstrap intervals.
- Reproducible JSON/CSV/PNG experiment artifacts.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Pulser and exact state-vector emulation can be computationally expensive.  The
included quickstart uses nine atoms; larger proposal scans should be staged.

## Quickstart

Validate all provisional hardware assumptions:

```bash
qbasin validate --config configs/quickstart.json
```

Generate the geometry taxonomy without running a quantum simulation:

```bash
qbasin taxonomy \
  --config configs/proposal_scan.json \
  --output results/geometry_taxonomy.csv
```

Screen geometry/detuning pairs by exact basin and barrier structure before
spending time on quantum evolution:

```bash
qbasin screen \
  --config configs/proposal_scan.json \
  --output results/proposal_landscape_screen.csv
```

Run the small end-to-end experiment:

```bash
qbasin scan \
  --config configs/quickstart.json \
  --output results/quickstart
```

Important artifacts are:

- `summary.csv`: one row per quantum or classical method and pulse point;
- `comparisons.csv`: quantum-versus-baseline distances and paired metrics;
- `geometry_taxonomy.csv`: structural descriptors of every geometry;
- `runs/*.json`: complete counts, basin tables, metrics, and hierarchy;
- `landscapes/*.json`: exact small-system basin/barrier analysis;
- `plots/*`: overlap, hierarchy, and controlled-scan diagnostics.

A curated verified example and the exact proposal/disorder screening tables
are versioned under [`results/`](results/README.md). Large future scans remain
ignored by default and should be archived as release assets or research data.

The configured proposal scan is a replicated 2 x 2 x 3 x 2 factorial over
Rabi amplitude, final detuning, sweep duration, and hold duration. Across six
geometries and three run replicates it contains 432 ideal-emulator runs. Use
the exact screen first and run the quantum design in batches.

## Recommended staged workflow

1. Run the taxonomy and exact classical landscape analysis on many candidates.
2. Reject disconnected, hardware-incompatible, or trivially concentrated
   geometries before quantum emulation.
3. Use `quickstart.json` to test code changes.
4. Run a coarse quantum scan on shortlisted small geometries.
5. Refine only around reproducible quality–diversity crossovers.
6. Add noise/dephasing controls.
7. Replace `ruby_proxy` with the actual RUBY device/backend adapter when it is
   made available by the hosting entity.

## Interpretation rules

- Non-bipartiteness and positional disorder are candidate ingredients, not
  proof of glassiness.
- A large `collision_probability_p_q1` means sampling concentration.
- Jensen–Shannon distance establishes difference, not superiority.
- A quantum benefit must be stated relative to a named classical sampler and
  resource convention.
- Exact state enumeration is preferred over stochastic claims whenever the
  system is small enough.
- Do not symmetrize data unless the implemented Hamiltonian has the required
  global spin-flip symmetry.

See [Geometry taxonomy](docs/GEOMETRY_TAXONOMY.md),
[Methodology](docs/METHODOLOGY.md), and
[RUBY assumptions](docs/RUBY_ASSUMPTIONS.md) before interpreting results. The
[proposal plan](docs/PROPOSAL_PLAN.md) explains the Path D claim and the next
hardware-facing work packages; [verification](docs/VERIFICATION.md) records
what was actually executed locally.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Repository status

This is a proposal-stage research prototype.  Before public release, choose a
license, add author/institution information, pin a validated dependency lock,
and archive the exact configuration used for every reported figure.
