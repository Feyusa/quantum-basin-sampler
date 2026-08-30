from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from qbasin.geometry import build_geometry
from qbasin.hardware import (
    _piecewise_constant_segments,
    pulser_sequence,
    qaptiva_job_from_sequence,
    qadence_circuit,
    submit_qaptiva_job,
)
from qbasin.io import read_json
from qbasin.pulse import PulseParameters
from qbasin.resources import calculate_resource_budget


ROOT = Path(__file__).resolve().parents[1]


class ResourceBudgetTests(unittest.TestCase):
    def test_proposal_resource_inventory(self) -> None:
        budget = calculate_resource_budget(
            read_json(ROOT / "configs" / "resource_budget.json")
        )
        self.assertEqual(budget["science_batches"], 432)
        self.assertEqual(budget["science_shots"], 864_000)
        self.assertEqual(budget["additional_batches"], 170)
        self.assertEqual(budget["additional_shots"], 178_000)
        self.assertEqual(budget["total_batches"], 602)
        self.assertEqual(budget["total_shots"], 1_042_000)
        self.assertIsNone(budget["host_verified_estimate"])
        self.assertEqual(
            budget["allocation_status"],
            "pending_host_per_shot_and_per_batch_timing",
        )
        self.assertAlmostEqual(
            budget["timing_sensitivity_models"][1]["total_qpu_hours"],
            31.7805555556,
        )

    def test_expected_science_shots_are_checked(self) -> None:
        config = read_json(ROOT / "configs" / "resource_budget.json")
        config["science_design"]["expected_science_shots"] = 1
        with self.assertRaisesRegex(ValueError, "not expected"):
            calculate_resource_budget(config)


class HardwareAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.geometry = build_geometry(
            {"kind": "kagome", "n_atoms": 9, "spacing": 5.0}
        )
        self.pulse = PulseParameters(
            omega_mhz=2.0,
            delta_initial_mhz=-6.0,
            delta_target_mhz=3.0,
            rise_ns=300,
            sweep_ns=600,
            hold_ns=100,
            fall_ns=300,
        )

    def test_piecewise_qadence_segments_preserve_duration(self) -> None:
        segments = _piecewise_constant_segments(self.pulse, ramp_steps=4)
        self.assertEqual(len(segments), 13)
        self.assertAlmostEqual(
            sum(duration for duration, _, _ in segments),
            self.pulse.total_duration_ns,
        )

    def test_qaptiva_submit_contract_waits_for_async_result(self) -> None:
        class AsyncResult:
            def join(self):
                return "finished"

        class QPU:
            def submit(self, job):
                self.job = job
                return AsyncResult()

        qpu = QPU()
        self.assertEqual(submit_qaptiva_job("job", qpu), "finished")
        self.assertEqual(qpu.job, "job")

    @unittest.skipUnless(
        importlib.util.find_spec("qadence"),
        "optional Qadence dependency is not installed",
    )
    def test_qadence_circuit_uses_custom_twelve_atom_register(self) -> None:
        geometry = build_geometry(
            {
                "kind": "jittered_kagome",
                "n_atoms": 12,
                "spacing": 6.0,
                "jitter_fraction": 0.06,
                "min_distance": 5.0,
                "seed": 19,
                "require_connected": True,
            }
        )
        circuit = qadence_circuit(geometry, self.pulse, ramp_steps=4)
        self.assertEqual(circuit.n_qubits, 12)

    @unittest.skipUnless(
        importlib.util.find_spec("pulser_myqlm"),
        "optional pulser-myqlm dependency is not installed",
    )
    def test_pulser_sequence_converts_to_qaptiva_job(self) -> None:
        sequence = pulser_sequence(self.geometry, self.pulse)
        job = qaptiva_job_from_sequence(sequence, shots=25)
        self.assertEqual(job.nbshots, 25)
        self.assertIsNotNone(job.schedule)


if __name__ == "__main__":
    unittest.main()
