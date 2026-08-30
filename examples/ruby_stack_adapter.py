"""Minimal Pulser/Qadence/Qaptiva adapter demonstration.

Examples:

  python examples/ruby_stack_adapter.py pulser-json --output sequence.json
  python examples/ruby_stack_adapter.py qaptiva-job --output sequence.job
  python examples/ruby_stack_adapter.py qadence

The ``ruby`` command is intentionally usable only inside an authenticated TGCC
Irene/Qaptiva session. It can consume real QPU time.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from qbasin.geometry import build_geometry
from qbasin.hardware import (
    qadence_circuit,
    qaptiva_job_from_sequence,
    pulser_sequence,
    submit_ruby_sequence,
)
from qbasin.io import read_json
from qbasin.pulse import expand_pulse_grid


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("pulser-json", "qaptiva-job", "qadence", "ruby")
    )
    parser.add_argument("--config", type=Path, default=Path("configs/n12_coarse_scan.json"))
    parser.add_argument("--geometry-index", type=int, default=0)
    parser.add_argument("--pulse-index", type=int, default=0)
    parser.add_argument("--shots", type=int, default=100)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ramp-steps", type=int, default=8)
    return parser


def main() -> None:
    args = _parser().parse_args()
    config = read_json(args.config)
    geometry = build_geometry(config["geometries"][args.geometry_index])
    pulse = expand_pulse_grid(config["pulse_grid"])[args.pulse_index]
    sequence = pulser_sequence(
        geometry,
        pulse,
        device_profile=str(config.get("device_profile", "ruby_proxy")),
    )

    if args.mode == "pulser-json":
        if args.output is None:
            raise SystemExit("pulser-json requires --output")
        args.output.write_text(sequence.to_abstract_repr(), encoding="utf-8")
        print(f"Wrote Pulser abstract representation to {args.output}")
        return

    if args.mode == "qaptiva-job":
        if args.output is None:
            raise SystemExit("qaptiva-job requires --output")
        job = qaptiva_job_from_sequence(sequence, shots=args.shots)
        job.dump(str(args.output))
        print(
            f"Wrote Qaptiva job with {job.nbshots} shots and an analog schedule "
            f"to {args.output}"
        )
        return

    if args.mode == "qadence":
        circuit = qadence_circuit(geometry, pulse, ramp_steps=args.ramp_steps)
        print(
            f"Built Qadence circuit with {circuit.n_qubits} qubits using "
            f"{args.ramp_steps} midpoint segments per linear ramp."
        )
        return

    result = submit_ruby_sequence(sequence, shots=args.shots)
    print(result)


if __name__ == "__main__":
    main()

