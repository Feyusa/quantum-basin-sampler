import unittest

import numpy as np

from qbasin.hierarchy import exact_barrier_merge_tree, hamming_linkage
from qbasin.landscape import IsingLandscape
from qbasin.pulse import PulseParameters, expand_pulse_grid


class HierarchyAndPulseTests(unittest.TestCase):
    def test_exact_two_well_barrier(self):
        # E(00)=E(11)=0 and E(01)=E(10)=1 in raw angular-frequency units.
        landscape = IsingLandscape(
            np.array([[0.0, -2.0], [-2.0, 0.0]]),
            -1.0,
            ("q0", "q1"),
        )
        events = exact_barrier_merge_tree(landscape, max_spins=4)
        self.assertEqual(len(events), 1)
        self.assertEqual(set(events[0].merged_minima), {"00", "11"})
        self.assertAlmostEqual(
            events[0].saddle_energy_mhz, 1.0 / (2.0 * np.pi)
        )

    def test_hamming_hierarchy(self):
        hierarchy = hamming_linkage({"000": 3, "011": 2, "111": 1})
        self.assertEqual(len(hierarchy["labels"]), 3)
        self.assertEqual(len(hierarchy["linkage"]), 2)

    def test_pulse_grid_cartesian_product(self):
        pulses = expand_pulse_grid(
            {
                "omega_mhz": [1.0, 2.0],
                "delta_target_mhz": [3.0, 6.0],
                "sweep_ns": [200, 400],
            }
        )
        self.assertEqual(len(pulses), 8)
        self.assertTrue(all(isinstance(pulse, PulseParameters) for pulse in pulses))


if __name__ == "__main__":
    unittest.main()

