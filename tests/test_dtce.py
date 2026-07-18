import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.dtce import DynamicThresholdCharacterizationEngine
from core.threshold_profiles import (
    BASE_THRESHOLDS_MS,
    ACTUATOR_FACTORS,
    MOTION_FACTORS,
    ENVIRONMENT_FACTORS,
    FREQUENCY_FACTORS,
)


class TestDTCEEngine(unittest.TestCase):
    """Unit tests directly against DynamicThresholdCharacterizationEngine."""

    def setUp(self):
        self.dtce = DynamicThresholdCharacterizationEngine()

    def test_same_inputs_identical_pt(self):
        a1 = self.dtce.compute_threshold("Torso", 180.0, "LRA", "Standard", None, "Walking", "Normal")
        a2 = self.dtce.compute_threshold("Torso", 180.0, "LRA", "Standard", None, "Walking", "Normal")
        self.assertEqual(a1.dynamic_pt_ms, a2.dynamic_pt_ms)

    def test_all_pt_positive(self):
        for zone in BASE_THRESHOLDS_MS:
            for actuator in ACTUATOR_FACTORS:
                audit = self.dtce.compute_threshold(zone, 150.0, actuator)
                self.assertGreater(audit.dynamic_pt_ms, 0.0)

    def test_body_zone_changes_baseline(self):
        audit_torso = self.dtce.compute_threshold("Torso", 150.0, "LRA")
        audit_foot = self.dtce.compute_threshold("Foot", 150.0, "LRA")
        self.assertNotEqual(audit_torso.base_pt_ms, audit_foot.base_pt_ms)
        self.assertEqual(audit_torso.base_pt_ms, BASE_THRESHOLDS_MS["Torso"])
        self.assertEqual(audit_foot.base_pt_ms, BASE_THRESHOLDS_MS["Foot"])

    def test_calibration_changes_pt_predictably(self):
        standard = self.dtce.compute_threshold("Hand", 150.0, "LRA", calibration_profile="Standard")
        high_sens = self.dtce.compute_threshold("Hand", 150.0, "LRA", calibration_profile="High Sensitivity")
        low_sens = self.dtce.compute_threshold("Hand", 150.0, "LRA", calibration_profile="Low Sensitivity")
        self.assertLess(high_sens.dynamic_pt_ms, standard.dynamic_pt_ms)
        self.assertGreater(low_sens.dynamic_pt_ms, standard.dynamic_pt_ms)

    def test_custom_calibration_bounded(self):
        audit_high = self.dtce.compute_threshold(
            "Hand", 150.0, "LRA", calibration_profile="Custom", custom_calibration_factor=5.0
        )
        audit_low = self.dtce.compute_threshold(
            "Hand", 150.0, "LRA", calibration_profile="Custom", custom_calibration_factor=-5.0
        )
        self.assertEqual(audit_high.calibration_factor, 1.20)
        self.assertEqual(audit_low.calibration_factor, 0.80)

    def test_motion_state_updates_pt(self):
        stationary = self.dtce.compute_threshold("Leg", 150.0, "ERM", motion_state="Stationary")
        running = self.dtce.compute_threshold("Leg", 150.0, "ERM", motion_state="Running")
        self.assertNotEqual(stationary.dynamic_pt_ms, running.dynamic_pt_ms)
        self.assertGreater(running.dynamic_pt_ms, stationary.dynamic_pt_ms)

    def test_environment_updates_pt(self):
        low = self.dtce.compute_threshold("Forearm", 150.0, "LRA", environment_state="Low disturbance")
        high = self.dtce.compute_threshold("Forearm", 150.0, "LRA", environment_state="High vibration/noise")
        self.assertNotEqual(low.dynamic_pt_ms, high.dynamic_pt_ms)
        self.assertGreater(high.dynamic_pt_ms, low.dynamic_pt_ms)

    def test_frequency_factor_within_bounds(self):
        low_freq = self.dtce.compute_threshold("Fingertip", 40.0, "LRA")
        nominal_freq = self.dtce.compute_threshold("Fingertip", 150.0, "LRA")
        high_freq = self.dtce.compute_threshold("Fingertip", 400.0, "LRA")
        self.assertEqual(low_freq.frequency_factor, FREQUENCY_FACTORS["low"])
        self.assertEqual(nominal_freq.frequency_factor, FREQUENCY_FACTORS["nominal"])
        self.assertEqual(high_freq.frequency_factor, FREQUENCY_FACTORS["high"])
        for f in (low_freq.frequency_factor, nominal_freq.frequency_factor, high_freq.frequency_factor):
            self.assertGreaterEqual(f, min(FREQUENCY_FACTORS.values()))
            self.assertLessEqual(f, max(FREQUENCY_FACTORS.values()))

    def test_unsupported_values_fail_safely(self):
        with self.assertRaises(ValueError):
            self.dtce.compute_threshold("Elbow", 150.0, "LRA")
        with self.assertRaises(ValueError):
            self.dtce.compute_threshold("Hand", 150.0, "Solenoid")
        with self.assertRaises(ValueError):
            self.dtce.compute_threshold("Hand", 150.0, "LRA", motion_state="Sprinting")
        with self.assertRaises(ValueError):
            self.dtce.compute_threshold("Hand", 150.0, "LRA", environment_state="Loud")
        with self.assertRaises(ValueError):
            self.dtce.compute_threshold("Hand", -10.0, "LRA")

    def test_manual_equation_verification(self):
        # 70.00 (Torso) x 1.00 (nominal freq) x 1.00 (LRA) x 1.00 (Standard)
        # x 1.05 (Walking) x 1.00 (Normal) = 73.5
        audit = self.dtce.compute_threshold(
            body_zone="Torso",
            frequency_hz=180.0,
            actuator_type="LRA",
            calibration_profile="Standard",
            motion_state="Walking",
            environment_state="Normal",
        )
        self.assertAlmostEqual(audit.dynamic_pt_ms, 73.5, places=6)


class TestDTCECoordinatorIntegration(unittest.TestCase):
    """Integration tests: DTCE invoked via the coordinator for whole node sets."""

    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator()
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_seed_reproducible_dtce_outputs(self):
        nodes_a, coord_a = self._build()
        coord_a.run_communication_cycle(0.0)
        nodes_b, coord_b = self._build()
        coord_b.run_communication_cycle(0.0)
        for node_id in coord_a.registry:
            self.assertEqual(
                coord_a.dtce_audit[node_id].dynamic_pt_ms,
                coord_b.dtce_audit[node_id].dynamic_pt_ms,
            )

    def test_dtce_persists_in_session_state_like_object(self):
        # Simulate a Streamlit rerun by re-fetching the same coordinator
        # instance from a session_state-like dict and confirming the audit
        # trail and node PT values are still present (not recomputed away).
        fake_session_state = {}
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        fake_session_state["coordinator"] = coordinator
        retrieved = fake_session_state["coordinator"]
        self.assertEqual(len(retrieved.dtce_audit), 30)
        for node in retrieved.registry.values():
            self.assertIsNotNone(node.perceptual_threshold)

    def test_all_node_count_configurations(self):
        for count in (10, 20, 30, 40, 50):
            _, coordinator = self._build(num_nodes=count)
            coordinator.run_communication_cycle(0.0)
            self.assertEqual(len(coordinator.dtce_audit), count)
            for node in coordinator.registry.values():
                self.assertIsNotNone(node.perceptual_threshold)
                self.assertGreater(node.perceptual_threshold, 0.0)

    def test_run_dtce_pass_reflects_context_changes(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        before = dict(coordinator.dtce_audit)
        before_pt = {nid: a.dynamic_pt_ms for nid, a in before.items()}

        coordinator.set_perceptual_context(motion_state="Running")
        coordinator.run_dtce_pass()
        after_pt = {nid: a.dynamic_pt_ms for nid, a in coordinator.dtce_audit.items()}

        self.assertTrue(any(after_pt[nid] != before_pt[nid] for nid in before_pt))


if __name__ == "__main__":
    unittest.main()
