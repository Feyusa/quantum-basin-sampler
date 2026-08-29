import unittest

import numpy as np

from qbasin.devices import geometry_issues
from qbasin.geometry import (
    classify_geometry,
    jittered_kagome_patch,
    kagome_patch,
    random_geometric_patch,
    square_patch,
    triangular_patch,
)


class GeometryTests(unittest.TestCase):
    def test_kagome_is_connected_nonbipartite_without_hub(self):
        geometry = kagome_patch(n_atoms=13, spacing=5.0)
        descriptors = classify_geometry(geometry)
        self.assertEqual(descriptors.connected_components, 1)
        self.assertFalse(descriptors.bipartite)
        self.assertGreater(descriptors.triangles, 0)
        self.assertLessEqual(descriptors.max_degree, 4)
        self.assertEqual(geometry_issues(geometry), [])

    def test_triangular_patch_has_geometric_frustration(self):
        descriptors = classify_geometry(triangular_patch(13, 5.0))
        self.assertTrue(descriptors.has_odd_cycle)
        self.assertGreater(descriptors.triangles, 0)
        self.assertEqual(descriptors.structural_class, "clean_geometric_frustration")

    def test_square_patch_is_a_connected_bipartite_control(self):
        descriptors = classify_geometry(square_patch(12, 5.0))
        self.assertEqual(descriptors.connected_components, 1)
        self.assertTrue(descriptors.bipartite)
        self.assertEqual(descriptors.screening_label, "connected_bipartite_control")

    def test_jittered_patch_respects_spacing_and_has_bond_disorder(self):
        geometry = jittered_kagome_patch(
            n_atoms=12,
            spacing=6.0,
            jitter_fraction=0.05,
            min_distance=5.0,
            seed=4,
        )
        descriptors = classify_geometry(geometry)
        self.assertGreaterEqual(descriptors.min_distance_um, 5.0 - 1e-9)
        self.assertGreater(descriptors.bond_strength_cv, 0.0)
        self.assertEqual(descriptors.structural_class, "correlated_bond_disorder")

    def test_amorphous_generation_is_reproducible(self):
        first = random_geometric_patch(10, radius=14.0, min_distance=5.0, seed=2)
        second = random_geometric_patch(10, radius=14.0, min_distance=5.0, seed=2)
        np.testing.assert_allclose(first.coordinates, second.coordinates)

    def test_connected_amorphous_geometry_can_be_required(self):
        geometry = random_geometric_patch(
            12,
            radius=11.0,
            min_distance=5.0,
            seed=33,
            require_connected=True,
        )
        self.assertEqual(classify_geometry(geometry).connected_components, 1)


if __name__ == "__main__":
    unittest.main()
