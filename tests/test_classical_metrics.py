import unittest

import numpy as np

from qbasin.basins import map_samples_to_basins
from qbasin.classical import (
    metropolis_samples,
    parallel_tempering_samples,
    simulated_annealing_samples,
    uniform_random_samples,
)
from qbasin.landscape import IsingLandscape
from qbasin.metrics import (
    bootstrap_metric_intervals,
    compare_basin_distributions,
    summarize_basin_distribution,
)


class ClassicalAndMetricTests(unittest.TestCase):
    def setUp(self):
        interaction = np.array(
            [
                [0.0, 2.0, 0.5, 0.2],
                [2.0, 0.0, 2.0, 0.5],
                [0.5, 2.0, 0.0, 2.0],
                [0.2, 0.5, 2.0, 0.0],
            ]
        )
        self.landscape = IsingLandscape(
            interaction, 1.0, ("q0", "q1", "q2", "q3")
        )

    def test_all_samplers_return_requested_samples(self):
        results = [
            uniform_random_samples(self.landscape, n_samples=20, seed=1),
            metropolis_samples(
                self.landscape,
                n_samples=20,
                temperature_mhz=1.0,
                burn_in_sweeps=2,
                sweeps_between_samples=1,
                seed=2,
            ),
            simulated_annealing_samples(
                self.landscape,
                n_samples=20,
                temperature_start_mhz=2.0,
                temperature_end_mhz=0.1,
                temperature_steps=4,
                sweeps_per_temperature=1,
                seed=3,
            ),
            parallel_tempering_samples(
                self.landscape,
                n_samples=20,
                temperature_min_mhz=0.1,
                temperature_max_mhz=2.0,
                replicas=4,
                burn_in_cycles=2,
                cycles_between_samples=1,
                seed=4,
            ),
        ]
        for result in results:
            self.assertEqual(sum(result.counts.values()), 20)

    def test_metrics_and_identical_comparison(self):
        raw = uniform_random_samples(self.landscape, n_samples=100, seed=8)
        mapped = map_samples_to_basins(raw.counts, self.landscape)
        metrics = summarize_basin_distribution(
            mapped.basin_counts, self.landscape
        )
        self.assertGreaterEqual(metrics["effective_basin_count"], 1.0)
        comparison = compare_basin_distributions(
            mapped.basin_counts, mapped.basin_counts
        )
        self.assertAlmostEqual(comparison["jensen_shannon_bits"], 0.0)
        self.assertAlmostEqual(comparison["total_variation"], 0.0)

    def test_bootstrap_intervals_are_ordered_and_reproducible(self):
        counts = {"0101": 70, "1010": 30}
        first = bootstrap_metric_intervals(
            counts, self.landscape, resamples=40, seed=9
        )
        second = bootstrap_metric_intervals(
            counts, self.landscape, resamples=40, seed=9
        )
        self.assertEqual(first, second)
        interval = first["intervals"]["effective_basin_count"]
        self.assertLessEqual(interval["lower"], interval["median"])
        self.assertLessEqual(interval["median"], interval["upper"])


if __name__ == "__main__":
    unittest.main()
