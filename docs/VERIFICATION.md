# Verification record

Verified locally on 2026-08-29 with Python 3.12, Pulser 1.9.0, and the ideal
Qutip backend.

## Automated checks

- package and tests compile successfully;
- 16 unit tests pass;
- all six proposal geometries and all configured pulses pass the provisional
  `ruby_proxy` hardware-envelope validator;
- the proposal configuration expands to 432 quantum runs: six geometries,
  24 pulse points, and three independent replicates;
- the disorder screen contains only connected geometries after rejection and
  resampling.

## End-to-end check

`configs/quickstart.json` completed 16 ideal quantum runs (eight pulse points,
two replicates), plus equal-shot uniform-random and simulated-annealing
baselines. It generated run JSON, exact landscapes/barriers, summary and
comparison CSV files, overlap figures, basin dendrograms, and an aggregated
scan plot with replicate error bars. Bootstrap interval columns are populated.

The small clean nine-atom quickstart is a software verification case, not an
advantage result. All tested samplers reach the full nine-basin support. Slower
sweeps concentrate quantum probability in fewer, lower-energy basins; this
confirms controllability of the quality-diversity trade-off but does not show
superiority over strong classical sampling.

## Not yet verified

- deployed RUBY constraints or execution;
- noise, atom loss, readout error, and calibration drift;
- Qadence/Qaptiva submission;
- scalable emulation above 20 atoms;
- hardware or end-to-end sampling advantage.
