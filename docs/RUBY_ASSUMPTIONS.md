# Provisional RUBY compatibility assumptions

## Public facts used

The proposal targets RUBY as a 100-data-qubit, two-dimensional neutral-atom
analogue/digital simulator integrated with the Joliot-Curie infrastructure and
programmed through Qadence/Qaptiva.

## Simulation profiles

### `mock`

Pulser `MockDevice`.  Useful for software development and deliberately
unconstrained experiments.  A sequence running here is not evidence of
hardware feasibility.

### `analog`

Pulser `AnalogDevice`.  Enforces a realistic, published Pulser envelope and is
the preferred conservative local simulation target.

### `ruby_proxy`

Currently executes with `AnalogDevice` but adds a separately documented proxy
validator.  The proxy uses:

- maximum 100 atoms;
- 2D coordinates;
- 5 um minimum separation;
- 38 um maximum radius;
- 6000 ns sequence duration;
- maximum `Omega = 4*pi rad/us`;
- maximum absolute detuning `40*pi rad/us`.

Only the 100-atom/2D character should be treated as RUBY-specific.  The other
numbers are conservative `AnalogDevice` assumptions and must be replaced when
the hosting entity supplies the actual device object and access documentation.

## Required pre-hardware work

- obtain the deployed RUBY device description and calibration ranges;
- confirm supported geometry/layout construction and atom rearrangement;
- confirm global versus local detuning capabilities;
- confirm allowed waveform shapes, timing granularity, and maximum duration;
- confirm shot limits, batching, readout convention, and failure modes;
- port sequence construction to the required Qadence/Qaptiva submission API;
- reproduce a small emulator benchmark through the official stack;
- add measurement error, atom loss, detuning/Rabi inhomogeneity, and calibration
  drift to the simulation controls;
- estimate QPU minutes using host-provided cycle and batching overheads.

Until these checks are complete, repository output must be described as
“RUBY-oriented ideal simulation,” not “RUBY simulation” or hardware results.

