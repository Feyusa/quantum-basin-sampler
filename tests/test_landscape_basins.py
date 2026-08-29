import unittest
from collections import Counter

import numpy as np

from qbasin.basins import exact_basin_partition, overlap_distribution
from qbasin.landscape import IsingLandscape


class LandscapeAndBasinTests(unittest.TestCase):
    def setUp(self):
        interaction = np.array(
            [
                [0.0, 10.0, 10.0],
                [10.0, 0.0, 10.0],
                [10.0, 10.0, 0.0],
            ]
        )
        self.landscape = IsingLandscape(interaction, 4.0, ("q0", "q1", "q2"))

    def test_energy_and_descent(self):
        self.assertAlmostEqual(self.landscape.energy("110"), 2.0)
        result = self.landscape.descend("111")
        costs = self.landscape.flip_costs(self.landscape.occupations(result.minimum))
        self.assertTrue(np.all(costs >= -1e-10))

    def test_exact_partition_covers_hypercube(self):
        partition = exact_basin_partition(self.landscape, max_spins=6)
        self.assertEqual(sum(partition.basin_counts.values()), 8)
        self.assertGreaterEqual(len(partition.basin_counts), 1)

    def test_overlap_is_exact_and_normalized(self):
        distribution = overlap_distribution(Counter({"000": 3, "011": 1}), 3)
        self.assertEqual(distribution, {-1 / 3: 0.375, 1.0: 0.625})
        self.assertAlmostEqual(sum(distribution.values()), 1.0)


if __name__ == "__main__":
    unittest.main()

