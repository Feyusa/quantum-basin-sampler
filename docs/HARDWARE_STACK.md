# RUBY software-stack adapter

## What is implemented

The repository now contains a minimal, explicit boundary between three layers:

1. **Pulser** constructs the exact rise-sweep-hold-freeze waveform used by the
   simulations.
2. **Qadence** can construct a portable, piecewise-constant representation of
   the same analog Hamiltonian for a custom-coordinate register.
3. **Pulser-myQLM/Qaptiva** converts the native Pulser sequence into an analog
   myQLM `Job`; inside TGCC, `qlmaas.qpus.PasqalQPU` submits that job to RUBY.

The production-facing route follows TGCC's public documentation:

```python
job = pulser_myqlm.IsingAQPU.convert_sequence_to_job(
    sequence,
    nbshots=shots,
    modulation=True,
)
result = qlmaas.qpus.PasqalQPU().submit(job)
```

TGCC states that physical RUBY jobs can only be dispatched through myQLM after
logging into the Irene supercomputer. Consequently, this repository does not
contain or request credentials, and local execution stops at job construction.

Public references:

- [TGCC quantum software stack and RUBY submission](https://www-dcc.extra.cea.fr/tgcc-public/en/html/toc/QuantumSoftwareStack.html)
- [myQLM QPU `submit()` contract](https://myqlm.github.io/02_user_guide/02_execute/03_qpu.html)
- [Qadence Pulser interface](https://pasqal-io.github.io/qadence/v1.11.5/tutorials/digital_analog_qc/pulser-basic/)

## Installation

Core Pulser simulation:

```bash
python -m pip install -e .
```

Pulser-to-Qaptiva job conversion:

```bash
python -m pip install -e '.[qaptiva]'
```

Qadence program construction is a separate optional install because Qadence
has a large PyTorch dependency:

```bash
python -m pip install 'torch==2.13.0+cpu' \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[qadence]'
```

At the time of verification, Qadence 1.11.5's optional `pulser` extra pins
Pulser 1.4.0, whereas the core repository is validated with Pulser 1.9.0.
Therefore, do not install `qadence[pulser]` into the core environment. The
Qadence example constructs the abstract circuit; native RUBY job generation
uses the separately verified Pulser 1.9 -> pulser-myQLM 0.8 path.

The Qadence 1.11.5 construction example was locally executed successfully
with the CPU build of PyTorch 2.13.0.

## Examples

Export the exact Pulser abstract representation:

```bash
python examples/ruby_stack_adapter.py pulser-json \
  --config configs/n12_coarse_scan.json \
  --output n12_sequence.json
```

Construct and serialize a Qaptiva analog job without contacting a server:

```bash
python examples/ruby_stack_adapter.py qaptiva-job \
  --config configs/n12_coarse_scan.json \
  --shots 100 \
  --output n12_sequence.job
```

Construct the Qadence representation:

```bash
python examples/ruby_stack_adapter.py qadence \
  --config configs/n12_coarse_scan.json \
  --ramp-steps 8
```

The `ruby` mode must only be run inside an authenticated TGCC allocation. It
can consume QPU time and is not part of continuous integration.

## Remaining hosting-entity checks

- confirm the exact deployed device/channel object and accepted modulation
  flag;
- confirm atom-layout validation and rearrangement policy;
- confirm maximum shots per job and batch queue limits;
- confirm result endianness and atom-loss encoding;
- obtain cycle, batch and allocation-accounting times;
- execute the serialized small job first, before the proposal-scale scan.
