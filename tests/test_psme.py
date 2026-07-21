import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.psme import PerceptualSynchronizationMarginEngine


class TestPSMEEngine(unittest.TestCase):
    """Unit tests directly against PerceptualSynchronizationMarginEngine."""

    def setUp(self):
        self.psme = PerceptualSynchronizationMarginEngine()

    def test_psm_equals_pt_minus_pe_exactly(self):
        result = self.psme.compute_margin(pt_ms=57.75, pe_ms=21.00)
        self.assertAlmostEqual(result.psm_ms, 57.75 - 21.00, places=9)
        self.assertAlmostEqual(result.psm_ms, 36.75, places=6)

    def test_positive_margin(self):
        result = self.psme.compute_margin(pt_ms=60.0, pe_ms=30.0)
        self.assertAlmostEqual(result.psm_ms, 30.0, places=6)
        self.assertAlmostEqual(result.normalized_psm, 0.5, places=6)
        self.assertAlmostEqual(result.threshold_utilization_pct, 50.0, places=6)
        self.assertEqual(result.margin_sign, "POSITIVE")
        self.assertEqual(result.status, "OK")

    def test_zero_margin_is_boundary_not_clamped_away(self):
        result = self.psme.compute_margin(pt_ms=60.0, pe_ms=60.0)
        self.assertAlmostEqual(result.psm_ms, 0.0, places=6)
        self.assertAlmostEqual(result.normalized_psm, 0.0, places=6)
        self.assertAlmostEqual(result.threshold_utilization_pct, 100.0, places=6)
        self.assertEqual(result.margin_sign, "BOUNDARY")

    def test_negative_margin_is_preserved_not_clamped_to_zero(self):
        result = self.psme.compute_margin(pt_ms=50.0, pe_ms=54.0)
        self.assertAlmostEqual(result.psm_ms, -4.0, places=6)
        self.assertLess(result.psm_ms, 0.0)
        self.assertNotEqual(result.psm_ms, 0.0)
        self.assertEqual(result.margin_sign, "NEGATIVE")

    def test_negative_margin_second_example(self):
        result = self.psme.compute_margin(pt_ms=60.0, pe_ms=70.0)
        self.assertAlmostEqual(result.psm_ms, -10.0, places=6)
        self.assertAlmostEqual(result.normalized_psm, -10.0 / 60.0, places=6)
        self.assertAlmostEqual(result.threshold_utilization_pct, 70.0 / 60.0 * 100.0, places=6)
        self.assertEqual(result.margin_sign, "NEGATIVE")

    def test_normalized_psm_matches_equal_ratio_example(self):
        # Node A: PT=60, PE=30 -> PSM=30 -> NPSM=0.50
        node_a = self.psme.compute_margin(pt_ms=60.0, pe_ms=30.0)
        # Node B: PT=30, PE=15 -> PSM=15 -> NPSM=0.50
        node_b = self.psme.compute_margin(pt_ms=30.0, pe_ms=15.0)
        self.assertAlmostEqual(node_a.normalized_psm, 0.50, places=6)
        self.assertAlmostEqual(node_b.normalized_psm, 0.50, places=6)
        self.assertNotEqual(node_a.psm_ms, node_b.psm_ms)

    def test_threshold_utilization_matches_example(self):
        result = self.psme.compute_margin(pt_ms=60.0, pe_ms=45.0)
        self.assertAlmostEqual(result.threshold_utilization_pct, 75.0, places=6)

    def test_pt_zero_rejected_by_strict_compute_margin(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=0.0, pe_ms=10.0)

    def test_pt_negative_rejected_by_strict_compute_margin(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=-5.0, pe_ms=10.0)

    def test_pe_negative_rejected_by_strict_compute_margin(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=60.0, pe_ms=-1.0)

    def test_missing_pt_rejected(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=None, pe_ms=10.0)

    def test_missing_pe_rejected(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=60.0, pe_ms=None)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=float("nan"), pe_ms=10.0)
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=60.0, pe_ms=float("nan"))

    def test_infinity_rejected(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=float("inf"), pe_ms=10.0)
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=60.0, pe_ms=float("inf"))

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms="not-a-number", pe_ms=10.0)
        with self.assertRaises(ValueError):
            self.psme.compute_margin(pt_ms=60.0, pe_ms=[1, 2, 3])

    def test_safe_compute_margin_never_raises_on_invalid_input(self):
        cases = [
            (None, 10.0),
            (60.0, None),
            (0.0, 10.0),
            (-5.0, 10.0),
            (60.0, -1.0),
            (float("nan"), 10.0),
            (float("inf"), 10.0),
            ("bad", 10.0),
        ]
        for pt, pe in cases:
            result = self.psme.safe_compute_margin(pt_ms=pt, pe_ms=pe, node_id="HN-000")
            self.assertEqual(result.status, "INVALID_INPUT")
            self.assertIsNotNone(result.error_reason)
            self.assertIsNone(result.psm_ms)
            self.assertIsNone(result.normalized_psm)
            self.assertIsNone(result.threshold_utilization_pct)
            self.assertIsNone(result.margin_sign)

    def test_safe_compute_margin_matches_strict_on_valid_input(self):
        strict = self.psme.compute_margin(pt_ms=57.75, pe_ms=21.00)
        safe = self.psme.safe_compute_margin(pt_ms=57.75, pe_ms=21.00)
        self.assertEqual(strict.psm_ms, safe.psm_ms)
        self.assertEqual(strict.normalized_psm, safe.normalized_psm)
        self.assertEqual(strict.threshold_utilization_pct, safe.threshold_utilization_pct)
        self.assertEqual(strict.margin_sign, safe.margin_sign)
        self.assertEqual(safe.status, "OK")


class TestPSMECoordinatorIntegration(unittest.TestCase):
    """Integration tests: PSME invoked via the coordinator for whole node sets."""

    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator(seed=seed)
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_all_node_count_configurations(self):
        for count in (10, 20, 30, 40, 50):
            _, coordinator = self._build(num_nodes=count)
            coordinator.run_communication_cycle(0.0)
            self.assertEqual(len(coordinator.psme_audit), count)
            for node in coordinator.registry.values():
                self.assertIsNotNone(node.psm)
                self.assertIsNotNone(node.normalized_psm)
                self.assertIsNotNone(node.threshold_utilization_pct)
                self.assertIsNotNone(node.margin_sign)

    def test_seed_reproducible_psm_outputs(self):
        _, coord_a = self._build(num_nodes=30, seed=123)
        coord_a.run_communication_cycle(0.0)
        _, coord_b = self._build(num_nodes=30, seed=123)
        coord_b.run_communication_cycle(0.0)
        for node_id in coord_a.registry:
            self.assertEqual(
                coord_a.psme_audit[node_id].psm_ms,
                coord_b.psme_audit[node_id].psm_ms,
            )
            self.assertEqual(
                coord_a.registry[node_id].psm,
                coord_b.registry[node_id].psm,
            )

    def test_every_psm_maps_to_correct_node(self):
        _, coordinator = self._build(num_nodes=30, seed=7)
        coordinator.run_communication_cycle(0.0)
        for node_id, result in coordinator.psme_audit.items():
            node = coordinator.registry[node_id]
            self.assertAlmostEqual(result.pt_ms, node.perceptual_threshold, places=6)
            self.assertAlmostEqual(result.pe_ms, node.perceived_error, places=6)
            self.assertAlmostEqual(result.psm_ms, node.psm, places=6)
            self.assertAlmostEqual(
                result.psm_ms, node.perceptual_threshold - node.perceived_error, places=6
            )

    def test_coordinator_does_not_overwrite_pt_or_pe(self):
        _, coordinator = self._build(num_nodes=20, seed=99)
        coordinator.run_communication_cycle(0.0)
        pt_before = {nid: n.perceptual_threshold for nid, n in coordinator.registry.items()}
        pe_before = {nid: n.perceived_error for nid, n in coordinator.registry.items()}

        coordinator.run_psme_pass()

        for nid, node in coordinator.registry.items():
            self.assertEqual(node.perceptual_threshold, pt_before[nid])
            self.assertEqual(node.perceived_error, pe_before[nid])

    def test_psm_reflects_pt_and_pe_changes(self):
        _, coordinator = self._build(num_nodes=10, seed=5)
        coordinator.set_perceptual_context(motion_state="Stationary", environment_state="Normal")
        coordinator.run_communication_cycle(0.0)
        favorable_psm = {nid: n.psm for nid, n in coordinator.registry.items()}

        coordinator.set_perceptual_context(motion_state="Running", environment_state="High vibration/noise")
        coordinator.run_dtce_pass()
        coordinator.run_psme_pass()
        challenging_psm = {nid: n.psm for nid, n in coordinator.registry.items()}

        self.assertTrue(
            any(challenging_psm[nid] != favorable_psm[nid] for nid in favorable_psm)
        )

    def test_no_node_has_clamped_negative_margin(self):
        _, coordinator = self._build(num_nodes=50, seed=2024)
        coordinator.run_communication_cycle(0.0)
        for result in coordinator.psme_audit.values():
            if result.margin_sign == "NEGATIVE":
                self.assertLess(result.psm_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
