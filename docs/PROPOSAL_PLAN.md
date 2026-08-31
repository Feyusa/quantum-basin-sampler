# Hybrid optimization sampler

## Current verdict

The repository now implements the intended proposal-stage workflow in ideal
small-system simulation. It does not yet demonstrate a quantum sampling
advantage and it does not simulate the deployed RUBY machine. The defensible
present claim is:

> We have a RUBY-oriented, hardware-envelope-checked protocol for testing
> whether controlled nonadiabatic neutral-atom dynamics supplies useful basin
> candidates to a classical optimization workflow.

This is stronger and more testable than asking for a particular U-shaped
`P(q)`. The Rydberg occupation Hamiltonian has a longitudinal detuning term and
normally lacks global spin-flip symmetry, so a symmetric two-peak overlap plot
is not a necessary success condition. Small clean arrays can also be strongly
boundary dominated.

## Workflow

1. A neutral-atom pulse prepares and measures candidate bitstrings.
2. A declared classical one-spin descent maps every bitstring to a local basin.
3. Basin energy, diversity, frequency, novelty, and hierarchy are measured.
4. A classical controller selects pulse regions or geometries for the next
   batch.
5. The final output is a quality-diverse portfolio of minima for downstream
   classical search, not merely one nominal ground-state bitstring.

The possible benefit is therefore useful candidate generation or
complementarity. Merely obtaining a distribution different from a classical
sampler is not an advantage.

## Classification and taxonomy

The design separates four questions:

| Axis | Classes | What it tests |
|---|---|---|
| First-shell topology | square bipartite control; Kagome/triangular odd-cycle graphs | geometric frustration versus a negative control |
| Disorder mechanism | none; vacancy/site; correlated jitter/bond; amorphous positional | whether quenched disorder creates useful ruggedness |
| Classical landscape | simple; single low-energy funnel; rugged low-energy candidate | whether the chosen final detuning has relevant basin multiplicity and barriers |
| Dynamic regime | rapid sweep; intermediate sweep; slow sweep; zero/nonzero hold | controlled departure from adiabatic preparation |

The structural label is assigned before dynamics. The landscape label is
assigned by exact enumeration for small systems. Neither is a thermodynamic
spin-glass diagnosis.

## What the current exact screen says

For the included 12- and 13-atom candidates:

- at `delta_f = 1.5 MHz`, the three connected jittered-Kagome realizations
  contain 6, 7, and 9 low-lying minima in the 0.25 MHz window;
- the three amorphous realizations contain 2, 3, and 8 low-lying minima at
  `1.5 MHz`;
- the jittered examples become single-low-energy-funnel cases at `3 MHz`,
  while two amorphous realizations retain 2 or 3 low-lying minima;
- the triangular control has many local minima but only one in the declared
  low-energy window at both selected detunings;
- clean and vacancy Kagome remain low-energy multibasin candidates in this
  small exact screen.

This makes `1.5 MHz` the main ruggedness target and `3 MHz` a useful crossover
control. These are screening observations, not evidence of quantum benefit.

## Controlled nonadiabatic experiment

`configs/proposal_scan.json` uses a predeclared factorial design:

- two Rabi amplitudes: 1.2 and 2.0 MHz;
- two final detunings: 1.5 and 3.0 MHz;
- three sweep times: 200, 600, and 1500 ns;
- no hold versus a 300 ns hold;
- six structural families/controls;
- three independent run replicates and 2,000 shots per method.

This is 432 ideal-emulator quantum runs. Analyze neighboring pulse points and
factor effects; do not select one visually attractive outlier.

## Classical comparison and success criteria

The mandatory zero-search baseline is uniform random bitstrings followed by
the same descent. Metropolis, simulated annealing, and parallel tempering are
stronger reference samplers. Equal returned samples is the first comparison;
energy-difference and descent evaluation counts remain explicit rather than
being declared equivalent to quantum shots.

Predeclare two primary outcomes:

1. low-energy probability mass;
2. number/effective number of distinct low-energy basins.

A candidate benefit is a reproducible Pareto improvement in these outcomes,
or a hybrid union that discovers valuable basins missed by every individual
classical sampler. Distribution distances and `P(q)` are secondary mechanism
diagnostics.

## New pathways worth adding

1. **Closed-loop geometry and pulse selection.** Use the exact screen and early
   batches to propose new connected geometries, then reserve a held-out batch
   for confirmation.
2. **Hybrid portfolio tests.** Seed a classical large-neighborhood search from
   quantum, classical, and union portfolios; compare final objective value and
   unique solutions at matched downstream budgets.
3. **Mechanism controls.** Add dephasing, atom-loss/readout, Rabi/detuning
   inhomogeneity, and a classical rate-equation control. A difference that
   vanishes under dephasing is more informative than a raw histogram change.
4. **Disorder and size scaling.** Repeat many geometry seeds, then move from
   exactly enumerable arrays to the largest emulator-feasible sizes and later
   to 24/48/72/96-atom RUBY batches.
5. **Hierarchy-aware reward.** Reward discovery of low-energy branches that
   are separated by exact or estimated barriers, rather than rewarding Hamming
   distance alone.

## Before claiming hardware readiness

Replace `ruby_proxy` with the official deployed device constraints and
Qadence/Qaptiva submission adapter; add hardware noise and loss; obtain shot,
batch, and timing limits; and benchmark a small instance through the official
emulator. Until then, say “RUBY-oriented ideal simulation.”
