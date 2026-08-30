# Verification record

Verified locally through 2026-08-30 with Python 3.12, Pulser 1.9.0, and the ideal
Qutip backend.

## Automated checks

- package and tests compile successfully;
- 22 unit tests pass after adding the resource and hardware adapters;
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

## Twelve-atom coarse scan

`configs/n12_coarse_scan.json` completed 16 ideal 12-atom quantum runs: eight
pulse points and two replicates with 500 samples per method. Exact enumeration
finds 31 local minima and six low-energy minima at 1.5 MHz, versus 16 local
minima and one low-energy minimum at 3 MHz. At 1.5 MHz, the 900 ns/no-hold
quantum point approximately matches simulated annealing in both low-energy
mass and effective basin count; parallel tempering retains greater low-energy
mass. This is feasibility evidence, not an advantage result. See
`docs/N12_COARSE_SCAN.md`.

## Hardware-stack smoke tests

Verified locally with Pulser 1.9.0, pulser-myQLM 0.8.3, myQLM 1.13.6 and
Qadence 1.11.5:

- the 12-atom Pulser sequence exports to Pulser abstract JSON;
- `IsingAQPU.convert_sequence_to_job` creates a Qaptiva analog job with the
  requested shots and a nonempty schedule;
- the Qadence adapter constructs a 12-qubit piecewise-constant analog circuit;
- no Qaptiva server, credentials or RUBY QPU were contacted.

## Not yet verified

- deployed RUBY constraints or execution;
- noise, atom loss, readout error, and calibration drift;
- authenticated Qaptiva/RUBY submission and result retrieval;
- scalable emulation above 20 atoms;
- hardware or end-to-end sampling advantage.
