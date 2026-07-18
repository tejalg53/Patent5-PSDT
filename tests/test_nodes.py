"""
Sprint 3 - Validation checks for the node factory / HapticNode model.

Run with:
    python3 -m unittest tests.test_nodes -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.constants import ZONE_ORDER, NODE_COUNT_OPTIONS


class TestNodeFactory(unittest.TestCase):
    def test_same_seed_is_reproducible(self):
        a = generate_nodes(30, seed=42)
        b = generate_nodes(30, seed=42)
        self.assertEqual([n.__dict__ for n in a], [n.__dict__ for n in b])

    def test_different_seed_varies(self):
        a = generate_nodes(30, seed=42)
        b = generate_nodes(30, seed=7)
        self.assertNotEqual([n.__dict__ for n in a], [n.__dict__ for n in b])

    def test_node_counts_match_selection(self):
        for n in NODE_COUNT_OPTIONS:
            nodes = generate_nodes(n, seed=1)
            self.assertEqual(len(nodes), n)

    def test_every_node_has_valid_zone(self):
        nodes = generate_nodes(30, seed=1)
        for node in nodes:
            self.assertIn(node.body_zone, ZONE_ORDER)

    def test_battery_within_bounds(self):
        for seed in (1, 2, 3):
            for node in generate_nodes(50, seed=seed):
                self.assertGreaterEqual(node.battery_level, 0)
                self.assertLessEqual(node.battery_level, 100)

    def test_delays_are_non_negative(self):
        for node in generate_nodes(50, seed=5):
            self.assertGreaterEqual(node.clock_drift, 0)
            self.assertGreaterEqual(node.network_delay, 0)
            self.assertGreaterEqual(node.actuator_driver_delay, 0)
            self.assertGreaterEqual(node.mechanical_startup_delay, 0)

    def test_node_ids_are_unique(self):
        for n in NODE_COUNT_OPTIONS:
            nodes = generate_nodes(n, seed=9)
            ids = [node.node_id for node in nodes]
            self.assertEqual(len(ids), len(set(ids)))

    def test_uncomputed_fields_are_not_faked(self):
        nodes = generate_nodes(10, seed=1)
        for node in nodes:
            self.assertIsNone(node.perceptual_threshold)
            self.assertIsNone(node.perceived_error)
            self.assertIsNone(node.psm)
            self.assertEqual(node.sync_state, "Unclassified")


if __name__ == "__main__":
    unittest.main()
