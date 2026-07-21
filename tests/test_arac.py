"""
Sprint 9 - Validation checks for the Adaptive Resource Allocation
Controller (ARAC) and its integration into the Coordinator pipeline.

Run with:
    python3 -m unittest tests.test_arac -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.arac import AdaptiveResourceAllocationController
from core.sce import RELAXED, NOMINAL, ELEVATED, IMMEDIATE, STATE_ORDER
from config.resource_profiles import (
    SYNC_INTERVAL_MS_BY_STATE,
    BEACON_INTERVAL_MS_BY_STATE,
    RADIO_WAKEUP_INTERVAL_MS_BY_STATE,
    TRANSMIT_POWER_PCT_BY_STATE,
    ZONE_SYNC_SCALE,
)


class TestARACStateResourceMapping(unittest.TestCase):
    """Deliverables 3, 4, 5, 7, 20: state-driven resource mapping and its
    ordering (Relaxed = longest intervals/lowest power, Immediate =
    shortest intervals/highest power)."""

    def setUp(self):
        self.arac = AdaptiveResourceAllocationController()

    def test_relaxed_has_longest_sync_interval(self):
        result = self.arac.allocate(state=RELAXED)
        self.assertEqual(result.sync_interval_ms, SYNC_INTERVAL_MS_BY_STATE[RELAXED])

    def test_immediate_has_shortest_sync_interval(self):
        result = self.arac.allocate(state=IMMEDIATE)
        self.assertEqual(result.sync_interval_ms, SYNC_INTERVAL_MS_BY_STATE[IMMEDIATE])

    def test_sync_interval_ordering_relaxed_to_immediate(self):
        intervals = [self.arac.allocate(state=s).sync_interval_ms for s in STATE_ORDER]
        # STATE_ORDER is [IMMEDIATE, ELEVATED, NOMINAL, RELAXED] - intervals
        # should be non-decreasing along that order.
        self.assertEqual(intervals, sorted(intervals))

    def test_beacon_frequency_increases_as_margin_shrinks(self):
        # Lower beacon interval = higher frequency. IMMEDIATE should have
        # the lowest (i.e. most frequent) beacon interval.
        relaxed = self.arac.allocate(state=RELAXED).beacon_interval_ms
        immediate = self.arac.allocate(state=IMMEDIATE).beacon_interval_ms
        self.assertLess(immediate, relaxed)

    def test_radio_wakeup_interval_shortens_toward_immediate(self):
        relaxed = self.arac.allocate(state=RELAXED).radio_wakeup_interval_ms
        immediate = self.arac.allocate(state=IMMEDIATE).radio_wakeup_interval_ms
        self.assertLess(immediate, relaxed)

    def test_transmit_power_increases_toward_immediate(self):
        relaxed = self.arac.allocate(state=RELAXED).transmit_power_pct
        immediate = self.arac.allocate(state=IMMEDIATE).transmit_power_pct
        self.assertGreater(immediate, relaxed)
        self.assertEqual(relaxed, TRANSMIT_POWER_PCT_BY_STATE[RELAXED])
        self.assertEqual(immediate, TRANSMIT_POWER_PCT_BY_STATE[IMMEDIATE])

    def test_unrecognized_state_raises_in_strict_allocate(self):
        with self.assertRaises(ValueError):
            self.arac.allocate(state="Warning")


class TestARACTriggerOffsetCompensation(unittest.TestCase):
    """Deliverable 6: trigger-timing offset compensates known mechanical
    and actuator-driver delay by firing that many ms earlier."""

    def setUp(self):
        self.arac = AdaptiveResourceAllocationController()

    def test_offset_is_negative_sum_of_delays(self):
        result = self.arac.allocate(
            state=NOMINAL, mechanical_delay_ms=12.0, actuator_driver_delay_ms=2.0
        )
        self.assertAlmostEqual(result.trigger_timing_offset_ms, -14.0)

    def test_zero_delay_gives_zero_offset(self):
        result = self.arac.allocate(state=NOMINAL)
        self.assertAlmostEqual(result.trigger_timing_offset_ms, 0.0)


class TestARACBodyZoneAllocation(unittest.TestCase):
    """Deliverables 14, 17: differentiated resource allocation across
    body zones for the same synchronization state."""

    def setUp(self):
        self.arac = AdaptiveResourceAllocationController()

    def test_different_zones_yield_different_sync_intervals(self):
        fingertip = self.arac.allocate(state=NOMINAL, body_zone="Fingertip").sync_interval_ms
        torso = self.arac.allocate(state=NOMINAL, body_zone="Torso").sync_interval_ms
        self.assertNotEqual(fingertip, torso)
        self.assertLess(fingertip, torso)

    def test_unknown_zone_falls_back_to_default_scale(self):
        result = self.arac.allocate(state=NOMINAL, body_zone="Unknown-Zone")
        self.assertEqual(result.sync_interval_ms, SYNC_INTERVAL_MS_BY_STATE[NOMINAL])


class TestARACInvalidInput(unittest.TestCase):
    """Deliverable 23: safe fallback (retain previous / documented
    defaults) rather than an undefined allocation."""

    def setUp(self):
        self.arac = AdaptiveResourceAllocationController()

    def test_missing_state_falls_back_to_default(self):
        result = self.arac.safe_allocate(state=None, battery=90.0, pt=50.0)
        self.assertEqual(result.status, "INVALID_INPUT")
        self.assertIsNotNone(result.sync_interval_ms)

    def test_invalid_state_falls_back_to_default(self):
        result = self.arac.safe_allocate(state="Warning", battery=90.0, pt=50.0)
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_missing_battery_falls_back(self):
        result = self.arac.safe_allocate(state=NOMINAL, battery=None, pt=50.0)
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_missing_pt_falls_back(self):
        result = self.arac.safe_allocate(state=NOMINAL, battery=90.0, pt=None)
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_nan_battery_falls_back(self):
        result = self.arac.safe_allocate(state=NOMINAL, battery=float("nan"), pt=50.0)
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_infinite_pt_falls_back(self):
        result = self.arac.safe_allocate(state=NOMINAL, battery=90.0, pt=float("inf"))
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_invalid_input_retains_previous_resources(self):
        previous = {
            "sync_interval_ms": 1234.0,
            "beacon_interval_ms": 77.0,
            "radio_wakeup_interval_ms": 33.0,
            "transmit_power_level": "High",
            "transmit_power_pct": 80.0,
            "trigger_timing_offset_ms": -5.0,
        }
        result = self.arac.safe_allocate(
            state=NOMINAL, battery=None, pt=50.0, previous_resources=previous
        )
        self.assertEqual(result.status, "INVALID_INPUT")
        self.assertEqual(result.sync_interval_ms, 1234.0)
        self.assertEqual(result.transmit_power_level, "High")

    def test_valid_input_never_returns_invalid_status(self):
        result = self.arac.safe_allocate(state=RELAXED, battery=95.0, pt=45.0, pe=20.0, psm=25.0)
        self.assertEqual(result.status, "OK")


class TestARACCoordinatorIntegration(unittest.TestCase):
    """Deliverables 1, 8, 9, 10, 21, 22: end-to-end pipeline wiring,
    PRAP packets, node resource fields, scalability, and reproducibility."""

    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator()
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_pipeline_runs_dtce_peee_psme_sce_arac_in_order(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=1.0)
        for node in coordinator.registry.values():
            if node.sync_state == "Unclassified":
                continue
            self.assertEqual(node.resource_status, "Adaptive")
            self.assertIsNotNone(node.allocated_sync_interval_ms)
            self.assertIsNotNone(node.allocated_beacon_interval_ms)
            self.assertIsNotNone(node.allocated_radio_wakeup_interval_ms)
            self.assertIsNotNone(node.allocated_transmit_power_level)
            self.assertIsNotNone(node.allocated_trigger_offset_ms)

    def test_prap_packets_carry_updated_resource_settings(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=1.0)
        for node_id, node in coordinator.registry.items():
            if node.sync_state == "Unclassified":
                continue
            prap = coordinator.latest_praps[node_id]
            self.assertFalse(prap.is_baseline)
            self.assertEqual(prap.sync_interval_ms, node.allocated_sync_interval_ms)
            self.assertEqual(prap.transmit_power_level, node.allocated_transmit_power_level)

    def test_scalability_across_node_counts(self):
        for num_nodes in [10, 20, 30, 40, 50]:
            _, coordinator = self._build(num_nodes=num_nodes)
            coordinator.run_communication_cycle(simulation_timestamp=1.0)
            self.assertEqual(coordinator.registered_node_count, num_nodes)
            for node in coordinator.registry.values():
                if node.sync_state != "Unclassified":
                    self.assertIsNotNone(node.allocated_sync_interval_ms)

    def test_reproducibility_same_seed_same_allocations(self):
        _, coord_a = self._build(num_nodes=20, seed=7)
        _, coord_b = self._build(num_nodes=20, seed=7)
        for t in (1.0, 2.0, 3.0):
            coord_a.run_communication_cycle(simulation_timestamp=t)
            coord_b.run_communication_cycle(simulation_timestamp=t)

        for node_id in coord_a.registry:
            node_a = coord_a.registry[node_id]
            node_b = coord_b.registry[node_id]
            self.assertEqual(node_a.allocated_sync_interval_ms, node_b.allocated_sync_interval_ms)
            self.assertEqual(node_a.allocated_transmit_power_level, node_b.allocated_transmit_power_level)
            self.assertEqual(node_a.resource_history, node_b.resource_history)

    def test_resource_history_is_bounded(self):
        _, coordinator = self._build(num_nodes=10, seed=1)
        for step in range(60):
            coordinator.run_communication_cycle(simulation_timestamp=float(step))
        for node in coordinator.registry.values():
            self.assertLessEqual(len(node.resource_history), 50)

    def test_unclassified_nodes_keep_baseline_resources(self):
        # Immediately after registration (before any cycle), nodes are
        # still Unclassified and must not have been given a fabricated
        # adaptive allocation.
        _, coordinator = self._build(num_nodes=10, seed=3)
        for node in coordinator.registry.values():
            self.assertEqual(node.resource_status, "Baseline")
            self.assertIsNone(node.allocated_sync_interval_ms)


if __name__ == "__main__":
    unittest.main()
