# Methodology and evaluation plan

## 1. Experimental object

For each geometry and pulse point, the quantum simulator returns measured
occupation bitstrings.  Every measured state is mapped by the same declared
local-descent rule to an `Omega=0` classical minimum at the pulse's target
detuning.  Classical samplers generate states of that same landscape and use
the identical descent implementation.

The pulse protocol is:

1. ramp `Omega` from zero at negative detuning;
2. sweep detuning to a target value at fixed `Omega`;
3. optionally hold at the target;
4. ramp `Omega` rapidly to zero to freeze occupations;
5. measure in the ground–Rydberg basis.

Scans are reported using both laboratory parameters and dimensionless
`delta/Omega` and `R_b/a` values.

## 2. Baselines and resource accounting

The mandatory baseline is uniformly random bitstrings followed by the same
descent.  It measures raw basin volume/accessibility without a search
algorithm.  Additional baselines are Metropolis, simulated annealing, and
parallel tempering.

The repository records separately:

- quantum shots;
- quantum emulator wall time;
- classical energy-difference evaluations;
- classical wall time;
- descent flip-cost evaluations.

These resources are not declared equivalent.  Comparisons should be shown
under at least two conventions: equal returned samples and a separately
defined classical-compute budget.  Hardware QPU time and queue/shot overhead
must be added after RUBY access.

## 3. Metrics

### Distribution concentration

- Shannon entropy;
- normalized entropy;
- collision probability `sum(p_alpha**2) = P(q=1)`;
- effective basin count `1/sum(p_alpha**2)`;
- largest-basin probability.

### Optimization quality

- best and mean energy;
- probability mass within a declared tolerance of the known/reference best;
- number of distinct low-energy basins.

### Diversity

- mean replica overlap;
- mean pairwise Hamming distance;
- negative-overlap mass (diagnostic only);
- basin support and exact-minimum coverage for enumerated landscapes.

### Quantum/classical comparison

- Jensen–Shannon divergence;
- total-variation and Hellinger distances;
- support Jaccard index;
- probability mass each method assigns to the other's support.

A distribution distance is evidence of difference, not advantage.  A
candidate sampling advantage should appear as a Pareto improvement: for
example, greater low-energy basin diversity at no loss of low-energy mass.

## 4. Hierarchical basin structure

Two complementary hierarchies are produced:

1. Average-linkage clustering of sampled minima using normalized Hamming
   distance.  This describes structural families but not transition barriers.
2. For small `N`, an exact flooding calculation on the full one-spin hypercube.
   It records the minimum energy at which components containing local minima
   first merge, yielding a disconnectivity-style energy-barrier tree.

The distinction is essential: nearby bitstrings can be separated by a high
barrier, and distant bitstrings can sometimes be linked through a low barrier.

## 5. Statistical protocol

- `replicates` repeats every selected pulse point with independent quantum and
  classical seeds.
- `bootstrap_resamples` attaches multinomial finite-shot intervals to every
  numeric basin metric; selected bounds are flattened into `summary.csv`.
- Repeat amorphous/jittered results over geometry seeds and average only after
  within-realization replica analysis.
- Predeclare primary metrics and pulse grids before the final hardware run.
- Use multiple-comparison correction or a held-out confirmation scan when a
  large grid is searched.
- Test sensitivity to descent rule and tie-breaking.

Bootstrap intervals are conditional on the observed support and do not replace
independent runs or disorder realizations. Replicate variability and bootstrap
uncertainty must be reported separately.

## 6. Evidence ladder

1. **Different distribution:** statistically nonzero distance from a baseline.
2. **Sampling benefit:** reproducible quality–diversity Pareto improvement.
3. **Hardware-relevant benefit:** persists with noise and RUBY constraints.
4. **Quantum-mechanism evidence:** survives controls against classical rate
   models/dephased dynamics and shows a coherence-sensitive signature.
5. **Advantage claim:** includes a defensible end-to-end resource comparison
   against strong classical algorithms.

The proposal should target levels 1–3.  Levels 4–5 are longer-term goals.
