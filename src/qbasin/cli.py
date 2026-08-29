"""Command-line interface for validation, taxonomy and experiment scans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qbasin.experiment import run_experiment, validate_configuration
from qbasin.geometry import build_geometry, classify_geometry
from qbasin.io import read_json, write_csv, write_json
from qbasin.screening import screen_landscapes


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qbasin",
        description="Quantum/classical basin-sampling benchmarks",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate config and provisional RUBY constraints"
    )
    validate.add_argument("--config", type=Path, required=True)
    validate.add_argument("--output", type=Path, default=None)

    taxonomy = subparsers.add_parser(
        "taxonomy", help="classify configured geometry candidates"
    )
    taxonomy.add_argument("--config", type=Path, required=True)
    taxonomy.add_argument("--output", type=Path, required=True)

    screen = subparsers.add_parser(
        "screen", help="exactly screen small classical landscapes before emulation"
    )
    screen.add_argument("--config", type=Path, required=True)
    screen.add_argument("--output", type=Path, required=True)

    scan = subparsers.add_parser(
        "scan", help="run quantum scan, classical baselines and hierarchy analysis"
    )
    scan.add_argument("--config", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        report = validate_configuration(read_json(args.config))
        if args.output:
            write_json(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "taxonomy":
        config = read_json(args.config)
        rows = [
            classify_geometry(build_geometry(spec)).to_dict()
            for spec in config["geometries"]
        ]
        write_csv(args.output, rows)
        print(f"Wrote {len(rows)} geometry classifications to {args.output}")
        return
    if args.command == "screen":
        rows = screen_landscapes(read_json(args.config))
        write_csv(args.output, rows)
        print(f"Wrote {len(rows)} exact landscape screens to {args.output}")
        return
    if args.command == "scan":
        manifest = run_experiment(args.config, args.output)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    main()
