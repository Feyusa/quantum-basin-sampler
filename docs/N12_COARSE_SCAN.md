# Verified 12-atom coarse scan

## Purpose and design

This scan is a technical-feasibility bridge between the nine-atom quickstart
and the 432-run proposal design. It uses one connected, bond-disordered
jittered-Kagome geometry with 12 atoms and four first-shell triangles. The
geometry has no provisional `ruby_proxy` violations.

The scan is a predeclared subset of the proposal grid:

- `Omega = 2.0 MHz`;
- target detuning `delta_f = 1.5, 3.0 MHz`;
- sweep duration `200, 900 ns`;
- hold duration `0, 300 ns`;
- two independent replicates;
- 500 samples per method;
- uniform random, simulated annealing and parallel tempering baselines.

This gives eight pulse points and 16 ideal quantum runs. Every run includes an
exact enumeration of the 4,096 classical configurations, exact basin mapping,
barrier hierarchy, 200 finite-shot bootstrap resamples and identical classical
descent postprocessing.

## Classical landscapes

| Target detuning | Exact local minima | Low-energy minima within 0.25 MHz | Interpretation |
|---:|---:|---:|---|
| 1.5 MHz | 31 | 6 | Rugged low-energy multibasin candidate |
| 3.0 MHz | 16 | 1 | Single low-energy funnel control |

This verifies the intended landscape crossover before interpreting the
dynamics.

## Quantum results

Values below are replicate means.

| `delta_f` | Sweep | Hold | Low-energy mass | Effective basins | Mean energy (MHz) |
|---:|---:|---:|---:|---:|---:|
| 1.5 | 200 ns | 0 ns | 0.480 | 11.40 | -6.625 |
| 1.5 | 200 ns | 300 ns | 0.520 | 13.99 | -6.668 |
| 1.5 | 900 ns | 0 ns | 0.658 | 8.85 | -6.888 |
| 1.5 | 900 ns | 300 ns | 0.501 | 15.37 | -6.690 |
| 3.0 | 200 ns | 0 ns | 0.380 | 3.93 | -15.800 |
| 3.0 | 200 ns | 300 ns | 0.239 | 5.95 | -15.331 |
| 3.0 | 900 ns | 0 ns | 0.586 | 2.17 | -16.300 |
| 3.0 | 900 ns | 300 ns | 0.420 | 3.88 | -15.849 |

## Classical comparison

The classical sampler does not depend on sweep or hold, so it is generated
once per detuning and replicate and reused for matched comparisons.

| `delta_f` | Method | Low-energy mass | Effective basins | Mean energy (MHz) |
|---:|---|---:|---:|---:|
| 1.5 | Uniform random | 0.352 | 19.39 | -6.445 |
| 1.5 | Simulated annealing | 0.652 | 9.00 | -6.900 |
| 1.5 | Parallel tempering | 0.954 | 3.78 | -7.178 |
| 3.0 | Uniform random | 0.194 | 7.01 | -15.154 |
| 3.0 | Simulated annealing | 0.684 | 1.96 | -16.317 |
| 3.0 | Parallel tempering | 0.997 | 1.01 | -16.663 |

At `delta_f = 1.5 MHz`, the 900 ns/no-hold quantum point essentially matches
simulated annealing: low-energy mass is 0.658 versus 0.652 and effective basin
count is 8.85 versus 9.00. Both methods find all six declared low-energy
basins. Parallel tempering has much greater low-energy mass but is more
concentrated and observes fewer total basins.

At `delta_f = 3.0 MHz`, the landscape has only one low-energy funnel. Parallel
tempering places 99.7% of its probability there and the quantum sampler does
not outperform the strong classical methods.

## Conclusion

The scan demonstrates all of the following:

- ideal state-vector execution scales from the quickstart to 12 atoms;
- the geometry/detuning screen predicts a real multibasin-to-single-funnel
  crossover;
- sweep and hold controls change the quality-diversity balance reproducibly;
- a hold is not automatically beneficial and can trade quality for diversity;
- the quantum distribution is competitive with simulated annealing at one
  rugged point, but parallel tempering remains the stronger quality sampler.

It does **not** demonstrate quantum advantage, a coherence-specific mechanism,
or hardware robustness. There are only two replicates, 500 shots and one
disorder realization. Its role in the proposal is technical feasibility and
experimental-design validation.

Raw data are in `results/n12_coarse_scan/summary.csv` and
`comparisons.csv`; full counts, bootstrap results and hierarchies are under
`runs/` and `landscapes/`.

