"""
Sprint 6 - Validation checks for the Perceived Error Estimation Engine.

Run with:
python3 -m unittest tests.test_peee -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.peee import PerceivedErrorEstimationEngine
from core.error_profiles import (
    DEFAULT_WEIGHTS,
    ACTUATOR_AD_PROFILE_FACTOR,
    ACTUATOR_MD_PROFILE_FACTOR,
)


class TestPEEEEngine(unittest.TestCase):
    """Unit tests directly against PerceivedErrorEstimationEngine."""

    def setUp(self):
        self.peee = PerceivedErrorEstimationEngine(seed=42)

    def test_additive_model_equals_exact_sum(self):
        audit = self.peee.compute_error(2.0, 4.0, 3.0, 12.0, model="additive")
        self.assertEqual(audit.perceived_error_ms, 21.0)
        self.assertEqual(audit.contribution_cd, 2.0)
        self.assertEqual(audit.contribution_nd, 4.0)
        self.assertEqual(audit.contribution_ad, 3.0)
        self.assertEqual(audit.contribution_md, 12.0)
        self.assertEqual(audit.weight_cd, 1.0)
        self.assertEqual(audit.weight_nd, 1.0)
        self.assertEqual(audit.weight_ad, 1.0)
        self.assertEqual(audit.weight_md, 1.0)

    def test_weighted_model_uses_supplied_weights(self):
        weights = {"CD": 2.0, "ND": 0.5, "AD": 1.5, "MD": 0.0}
        audit = self.peee.compute_error(
            2.0, 4.0, 3.0, 12.0, model="weighted", weights=weights
        )
        expected = 2.0 * 2.0 + 4.0 * 0.5 + 3.0 * 1.5 + 12.0 * 0.0
        self.assertAlmostEqual(audit.perceived_error_ms, expected, places=6)
        self.assertEqual(audit.contribution_cd, 4.0)
        self.assertEqual(audit.contribution_nd, 2.0)
        self.assertEqual(audit.contribution_ad, 4.5)
        self.assertEqual(audit.contribution_md, 0.0)

    def test_all_weights_one_matches_additive(self):
        additive = self.peee.compute_error(2.0, 4.0, 3.0, 12.0, model="additive")
        weighted = self.peee.compute_error(
            2.0, 4.0, 3.0, 12.0, model="weighted", weights=dict(DEFAULT_WEIGHTS)
        )
        self.assertEqual(additive.perceived_error_ms, weighted.perceived_error_ms)

    def test_negative_components_rejected(self):
        with self.assertRaises(ValueError):
            self.peee.compute_error(-1.0, 4.0, 3.0, 12.0)
        with self.assertRaises(ValueError):
            self.peee.compute_error(2.0, -4.0, 3.0, 12.0)
        with self.assertRaises(ValueError):
            self.peee.compute_error(2.0, 4.0, -3.0, 12.0)
        with self.assertRaises(ValueError):
            self.peee.compute_error(2.0, 4.0, 3.0, -12.0)

    def test_unsupported_model_rejected(self):
        with self.assertRaises(ValueError):
            self.peee.compute_error(2.0, 4.0, 3.0, 12.0, model="multiplicative")

    def test_manual_equation_verification_hn007(self):
        # HN-007 example from the sprint spec: CD=2.0 ND=4.0 AD=3.0 MD=12.0
        audit = self.peee.compute_error(2.0, 4.0, 3.0, 12.0)
        self.assertEqual(audit.perceived_error_ms, 21.0)

    def test_resolve_clock_drift_is_absolute_value(self):
        self.assertEqual(self.peee.resolve_clock_drift_ms(1.82), 1.82)
        self.assertEqual(self.peee.resolve_clock_drift_ms(-1.82), 1.82)

    def test_resolve_network_residual_is_relative_to_reference(self):
        # measured 8.4 ms vs reference 5.0 ms -> residual 3.4 ms (spec example)
        residual = self.peee.resolve_network_residual_ms(8.4, network_condition="Nominal")
        self.assertAlmostEqual(residual, 3.4, places=6)

    def test_network_residual_never_negative(self):
        residual = self.peee.resolve_network_residual_ms(0.0, network_condition="Optimal")
        self.assertGreaterEqual(residual, 0.0)

    def test_different_network_conditions_modify_nd_predictably(self):
        nominal = self.peee.resolve_network_residual_ms(10.0, network_condition="Nominal")
        congested = self.peee.resolve_network_residual_ms(10.0, network_condition="Congested")
        degraded = self.peee.resolve_network_residual_ms(10.0, network_condition="Degraded")
        optimal = self.peee.resolve_network_residual_ms(10.0, network_condition="Optimal")
        self.assertLess(optimal, nominal)
        self.assertLess(nominal, congested)
        self.assertLess(congested, degraded)

    def test_actuator_profiles_affect_ad_and_md_predictably(self):
        ad_lra = self.peee.resolve_actuator_driver_delay_ms(2.0, "LRA")
        ad_erm = self.peee.resolve_actuator_driver_delay_ms(2.0, "ERM")
        ad_piezo = self.peee.resolve_actuator_driver_delay_ms(2.0, "Piezo")
        self.assertEqual(ad_lra, 2.0 * ACTUATOR_AD_PROFILE_FACTOR["LRA"])
        self.assertEqual(ad_erm, 2.0 * ACTUATOR_AD_PROFILE_FACTOR["ERM"])
        self.assertEqual(ad_piezo, 2.0 * ACTUATOR_AD_PROFILE_FACTOR["Piezo"])
        self.assertNotEqual(ad_lra, ad_erm)
        self.assertNotEqual(ad_erm, ad_piezo)

        md_lra = self.peee.resolve_mechanical_startup_delay_ms(15.0, "LRA")
        md_erm = self.peee.resolve_mechanical_startup_delay_ms(15.0, "ERM")
        md_piezo = self.peee.resolve_mechanical_startup_delay_ms(15.0, "Piezo")
        self.assertEqual(md_lra, 15.0 * ACTUATOR_MD_PROFILE_FACTOR["LRA"])
        self.assertEqual(md_erm, 15.0 * ACTUATOR_MD_PROFILE_FACTOR["ERM"])
        self.assertEqual(md_piezo, 15.0 * ACTUATOR_MD_PROFILE_FACTOR["Piezo"])
        self.assertNotEqual(md_lra, md_erm)
        self.assertNotEqual(md_erm, md_piezo)

    def test_resolved_components_never_negative(self):
        self.assertGreaterEqual(self.peee.resolve_clock_drift_ms(-5.0), 0.0)
        self.assertGreaterEqual(self.peee.resolve_network_residual_ms(0.0), 0.0)
        self.assertGreaterEqual(self.peee.resolve_actuator_driver_delay_ms(0.0, "LRA"), 0.0)
        self.assertGreaterEqual(self.peee.resolve_mechanical_startup_delay_ms(0.0, "ERM"), 0.0)

    def test_update_timing_state_reproducible_with_same_seed(self):
        nodes_a = generate_nodes(10, seed=7)
        nodes_b = generate_nodes(10, seed=7)
        engine_a = PerceivedErrorEstimationEngine(seed=99)
        engine_b = PerceivedErrorEstimationEngine(seed=99)
        for node in nodes_a:
            engine_a.update_timing_state(node, elapsed_seconds=5.0)
        for node in nodes_b:
            engine_b.update_timing_state(node, elapsed_seconds=5.0)
        for na, nb in zip(nodes_a, nodes_b):
            self.assertEqual(na.clock_drift, nb.clock_drift)
            self.assertEqual(na.network_delay, nb.network_delay)
            self.assertEqual(na.actuator_driver_delay, nb.actuator_driver_delay)
            self.assertEqual(na.mechanical_startup_delay, nb.mechanical_startup_delay)

    def test_update_timing_state_keeps_values_non_negative(self):
        nodes = generate_nodes(10, seed=1)
        engine = PerceivedErrorEstimationEngine(seed=1)
        for node in nodes:
            for _ in range(20):
                engine.update_timing_state(node, elapsed_seconds=10.0)
            self.assertGreaterEqual(node.clock_drift, 0.0)
            self.assertGreaterEqual(node.network_delay, 0.0)
            self.assertGreaterEqual(node.actuator_driver_delay, 0.0)
            self.assertGreaterEqual(node.mechanical_startup_delay, 0.0)

    def test_clock_drift_increases_with_elapsed_time(self):
        nodes = generate_nodes(10, seed=3)
        engine = PerceivedErrorEstimationEngine(seed=3)
        node = nodes[0]
        before = node.clock_drift
        engine.update_timing_state(node, elapsed_seconds=100.0)
        self.assertGreater(node.clock_drift, before)


class TestPEEECoordinatorIntegration(unittest.TestCase):
    """Integration tests: PEEE invoked via the coordinator for whole node sets."""

    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator(seed=seed)
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_pe_computed_for_every_node(self):
        nodes, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        self.assertEqual(len(coordinator.peee_audit), len(nodes))
        for node in nodes:
            self.assertIsNotNone(node.perceived_error)
            self.assertGreaterEqual(node.perceived_error, 0.0)

    def test_all_node_count_configurations(self):
        for count in (10, 20, 30, 40, 50):
            _, coordinator = self._build(num_nodes=count)
            coordinator.run_communication_cycle(0.0)
            self.assertEqual(len(coordinator.peee_audit), count)

    def test_coordinator_stores_latest_pe(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        first_pe = {nid: a.perceived_error_ms for nid, a in coordinator.peee_audit.items()}
        coordinator.run_communication_cycle(1.0)
        second_pe = {nid: a.perceived_error_ms for nid, a in coordinator.peee_audit.items()}
        self.assertEqual(set(first_pe.keys()), set(second_pe.keys()))
        for node in coordinator.registry.values():
            self.assertEqual(node.perceived_error, coordinator.peee_audit[node.node_id].perceived_error_ms)

    def test_seed_reproducible_peee_outputs(self):
        _, coord_a = self._build()
        coord_a.run_communication_cycle(0.0)
        _, coord_b = self._build()
        coord_b.run_communication_cycle(0.0)
        for node_id in coord_a.registry:
            self.assertEqual(
                coord_a.peee_audit[node_id].perceived_error_ms,
                coord_b.peee_audit[node_id].perceived_error_ms,
            )

    def test_weighted_model_via_coordinator(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        additive_pe = {nid: a.perceived_error_ms for nid, a in coordinator.peee_audit.items()}

        coordinator.set_error_model_context(
            model="weighted", weights={"CD": 2.0, "ND": 2.0, "AD": 2.0, "MD": 2.0}
        )
        coordinator.run_peee_pass()
        weighted_pe = {nid: a.perceived_error_ms for nid, a in coordinator.peee_audit.items()}

        for node_id in additive_pe:
            self.assertAlmostEqual(weighted_pe[node_id], additive_pe[node_id] * 2.0, places=6)

    def test_network_condition_changes_pe(self):
        _, coordinator = self._build()
        coordinator.set_error_model_context(network_condition="Optimal")
        coordinator.run_communication_cycle(0.0)
        optimal_pe = {nid: a.nd_ms for nid, a in coordinator.peee_audit.items()}

        coordinator.set_error_model_context(network_condition="Degraded")
        coordinator.run_peee_pass()
        degraded_pe = {nid: a.nd_ms for nid, a in coordinator.peee_audit.items()}

        self.assertTrue(any(degraded_pe[nid] >= optimal_pe[nid] for nid in optimal_pe))

    def test_run_communication_cycle_updates_timing_state(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        before = {nid: n.clock_drift for nid, n in coordinator.registry.items()}
        coordinator.run_communication_cycle(100.0)
        after = {nid: n.clock_drift for nid, n in coordinator.registry.items()}
        self.assertTrue(any(after[nid] > before[nid] for nid in before))

    def test_all_ms_units_non_negative_across_audit(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(0.0)
        for audit in coordinator.peee_audit.values():
            for value in (audit.cd_ms, audit.nd_ms, audit.ad_ms, audit.md_ms, audit.perceived_error_ms):
                self.assertGreaterEqual(value, 0.0)


if __name__ == "__main__":
    unittest.main()
