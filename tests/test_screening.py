import unittest

from qbasin.screening import screen_landscapes


class ScreeningTests(unittest.TestCase):
    def test_exact_screen_returns_one_row_per_geometry_and_detuning(self):
        config = {
            "device_profile": "mock",
            "exact_analysis_max_spins": 8,
            "geometries": [{"kind": "kagome", "n_atoms": 6, "spacing": 5.0}],
            "pulse_grid": {"delta_target_mhz": [2.0, 4.0]},
            "landscape_screen": {"compute_barriers": False},
        }
        rows = screen_landscapes(config)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["delta_target_mhz"] for row in rows}, {2.0, 4.0})
        self.assertTrue(all(row["enumerated_states"] == 64 for row in rows))


if __name__ == "__main__":
    unittest.main()
