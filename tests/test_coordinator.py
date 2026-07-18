"""
Sprint 4 - Validation checks for the Central Synchronization Coordinator.

Run with:
    python3 -m unittest tests.test_coordinator -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.packets import PSSP


class TestCoordinator(unittest.TestCase):
    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator()
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_registry_matches_node_count(self):
        nodes, coordinator = self._build()
        self.assertEqual(coordinator.registered_node_count, len(nodes))

    def test_cycle_produces_expected_pssp_count(self):
        _, coordinator = self._build()
        entries = coordinator.run_communication_cycle(simulation_timestamp=0)
        self.assertEqual(len(entries), 30)
        self.assertEqual(coordinator.packets_received, 30)
        self.assertEqual(coordinator.valid_packets, 30)

    def test_every_pssp_maps_to_correct_node(self):
        nodes, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=0)
        for node in nodes:
            pssp = coordinator.status_repository[node.node_id]
            self.assertEqual(pssp.node_id, node.node_id)
            self.assertEqual(pssp.body_zone, node.body_zone)

    def test_packet_ids_unique_within_cycle(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=0)
        ids = [e.packet_id for e in coordinator.log]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seed_still_reproducible_with_coordinator(self):
        nodes_a = generate_nodes(30, seed=42)
        nodes_b = generate_nodes(30, seed=42)
        self.assertEqual([n.__dict__ for n in nodes_a], [n.__dict__ for n in nodes_b])

    def test_invalid_packets_are_rejected_and_counted(self):
        nodes, coordinator = self._build()

        unknown_node = PSSP(
            packet_id="PSSP-BAD-001", node_id="HN-999", body_zone="Fingertip",
            simulation_timestamp=0, clock_drift_ms=1.0, network_delay_ms=1.0,
            actuator_driver_delay_ms=1.0, mechanical_startup_delay_ms=1.0,
            battery_percent=50.0, current_state="Unclassified",
        )
        valid, _ = coordinator.validate_pssp(unknown_node)
        self.assertFalse(valid)

        negative_delay = PSSP(
            packet_id="PSSP-BAD-002", node_id=nodes[0].node_id, body_zone=nodes[0].body_zone,
            simulation_timestamp=0, clock_drift_ms=-5.0, network_delay_ms=1.0,
            actuator_driver_delay_ms=1.0, mechanical_startup_delay_ms=1.0,
            battery_percent=50.0, current_state="Unclassified",
        )
        valid, _ = coordinator.validate_pssp(negative_delay)
        self.assertFalse(valid)

        bad_battery = PSSP(
            packet_id="PSSP-BAD-003", node_id=nodes[0].node_id, body_zone=nodes[0].body_zone,
            simulation_timestamp=0, clock_drift_ms=1.0, network_delay_ms=1.0,
            actuator_driver_delay_ms=1.0, mechanical_startup_delay_ms=1.0,
            battery_percent=150.0, current_state="Unclassified",
        )
        valid, _ = coordinator.validate_pssp(bad_battery)
        self.assertFalse(valid)

        zone_mismatch = PSSP(
            packet_id="PSSP-BAD-004", node_id=nodes[0].node_id, body_zone="WrongZone",
            simulation_timestamp=0, clock_drift_ms=1.0, network_delay_ms=1.0,
            actuator_driver_delay_ms=1.0, mechanical_startup_delay_ms=1.0,
            battery_percent=50.0, current_state="Unclassified",
        )
        valid, _ = coordinator.validate_pssp(zone_mismatch)
        self.assertFalse(valid)

    def test_multiple_cycles_accumulate_counters(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=0)
        coordinator.run_communication_cycle(simulation_timestamp=1)
        self.assertEqual(coordinator.packets_received, 60)
        self.assertEqual(coordinator.valid_packets, 60)
        self.assertEqual(coordinator.cycle_count, 2)

    def test_prap_is_structural_placeholder_only(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=0)
        self.assertEqual(len(coordinator.latest_praps), 30)
        for prap in coordinator.latest_praps.values():
            self.assertTrue(prap.is_baseline)
            self.assertIsNone(prap.target_state)
            self.assertIsNone(prap.sync_interval_ms)
            self.assertIsNone(prap.beacon_interval_ms)
            self.assertIsNone(prap.radio_wakeup_interval_ms)
            self.assertIsNone(prap.transmit_power_level)
            self.assertIsNone(prap.trigger_timing_offset_ms)


if __name__ == "__main__":
    unittest.main()
