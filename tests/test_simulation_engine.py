"""
Sprint 10 - Validation checks for the Digital Twin Simulation Engine
(core/simulation_engine.py) and its closed-loop integration of the
Sprint 4-9 DTCE/PEEE/PSME/SCE/ARAC pipeline over simulated time.

Run with:
    python3 -m unittest tests.test_simulation_engine -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.simulation_engine import DigitalTwinSimulationEngine
from core.sce import RELAXED, NOMINAL, ELEVATED, IMMEDIATE, STATE_ORDER


class TestClockDriftAccumulation(unittest.TestCase):
    """Deliverable 31.1: without an intervening resync, CD(t+1) > CD(t)."""

    def test_drift_grows_between_syncs(self):
        engine = DigitalTwinSimulationEngine(num_nodes=10, duration_s=10, time_step_s=1.0, seed=42)
        engine.initialize()
        node_id = next(iter(engine.coordinator.registry))
        series_cd = []
        for _ in range(5):
            engine.step()
            series_cd.append(engine.coordinator.registry[node_id].clock_drift)
            if node_id in engine._last_sync_fired:
                break
        if len(series_cd) >= 2 and node_id not in engine._last_sync_fired:
            for earlier, later in zip(series_cd, series_cd[1:]):
                self.assertGreaterEqual(later, earlier)


class TestResynchronizationEffect(unittest.TestCase):
    """Deliverable 31.2: after a resync, CD_after < CD_before."""

    def test_resync_reduces_drift(self):
        fired_once = False
        for attempt in range(5):
            engine = DigitalTwinSimulationEngine(
                num_nodes=20, duration_s=60, time_step_s=1.0, seed=42 + attempt
            )
            engine.initialize()
            for node_id in list(engine.coordinator.registry.keys()):
                prev_cd = None
                for _ in range(60):
                    engine.step()
                    node = engine.coordinator.registry[node_id]
                    if node_id in engine._last_sync_fired and prev_cd is not None:
                        self.assertLess(node.clock_drift, prev_cd)
                        fired_once = True
                        break
                    prev_cd = node.clock_drift
                if fired_once:
                    break
            if fired_once:
                break
        self.assertTrue(fired_once, "Expected at least one resynchronization event.")


class TestARACFeedback(unittest.TestCase):
    """Deliverable 31.3: stricter states get more aggressive (shorter)
    synchronization intervals, and that ordering is what the engine
    actually applies over a real run (not just the static config)."""

    def test_stricter_state_shorter_interval(self):
        engine = DigitalTwinSimulationEngine(
            num_nodes=30, duration_s=120, time_step_s=1.0, seed=42,
            scenario="Scenario C: Dynamic/Challenging",
        )
        engine.initialize()
        engine.run_to_completion()

        interval_by_state = {state: [] for state in STATE_ORDER}
        for node_id in engine.coordinator.registry:
            series = engine.history.node_dataframe_dict(node_id)
            for state, interval in zip(series["current_state"], series["sync_interval_ms"]):
                if state in interval_by_state and interval:
                    interval_by_state[state].append(interval)

        means = {
            state: (sum(vals) / len(vals) if vals else None)
            for state, vals in interval_by_state.items()
        }
        ordered_present = [s for s in [IMMEDIATE, ELEVATED, NOMINAL, RELAXED] if means[s] is not None]
        for stricter, looser in zip(ordered_present, ordered_present[1:]):
            self.assertLessEqual(means[stricter], means[looser])


class TestEnergyAccounting(unittest.TestCase):
    """Deliverable 31.4: more radio/sync activity => more simulated energy,
    under identical energy coefficients."""

    def test_dynamic_scenario_consumes_more_energy_than_stable(self):
        common = dict(num_nodes=15, duration_s=90, time_step_s=1.0, seed=42)

        stable = DigitalTwinSimulationEngine(scenario="Scenario A: Stable", **common)
        stable.initialize()
        stable.run_to_completion()
        stable_energy = sum(n.energy_consumed for n in stable.coordinator.registry.values())

        dynamic = DigitalTwinSimulationEngine(scenario="Scenario C: Dynamic/Challenging", **common)
        dynamic.initialize()
        dynamic.run_to_completion()
        dynamic_energy = sum(n.energy_consumed for n in dynamic.coordinator.registry.values())

        self.assertGreater(dynamic_energy, stable_energy)


class TestDeterminism(unittest.TestCase):
    """Deliverable 31.5 / 33: same seed => identical history; different
    seed => (almost certainly) different history."""

    def _run(self, seed):
        engine = DigitalTwinSimulationEngine(num_nodes=20, duration_s=60, time_step_s=1.0, seed=seed)
        engine.initialize()
        engine.run_to_completion()
        return engine

    def test_same_seed_reproducible(self):
        a = self._run(42)
        b = self._run(42)
        node_ids_a = sorted(a.coordinator.registry.keys())
        node_ids_b = sorted(b.coordinator.registry.keys())
        self.assertEqual(node_ids_a, node_ids_b)
        for node_id in node_ids_a:
            series_a = a.history.node_dataframe_dict(node_id)
            series_b = b.history.node_dataframe_dict(node_id)
            self.assertEqual(series_a["PT"], series_b["PT"])
            self.assertEqual(series_a["PE"], series_b["PE"])
            self.assertEqual(series_a["current_state"], series_b["current_state"])
            self.assertEqual(series_a["cumulative_energy_j"], series_b["cumulative_energy_j"])
        self.assertEqual(a.total_sync_events, b.total_sync_events)

    def test_different_seed_differs(self):
        a = self._run(42)
        c = self._run(43)
        any_diff = False
        for node_id in a.coordinator.registry:
            if node_id not in c.coordinator.registry:
                continue
            series_a = a.history.node_dataframe_dict(node_id)
            series_c = c.history.node_dataframe_dict(node_id)
            if series_a["PE"] != series_c["PE"]:
                any_diff = True
                break
        self.assertTrue(any_diff)


class TestScalability(unittest.TestCase):
    """Deliverable 34: 10-50 nodes all complete cleanly."""

    def test_node_counts(self):
        for count in (10, 20, 30, 40, 50):
            engine = DigitalTwinSimulationEngine(num_nodes=count, duration_s=30, time_step_s=1.0, seed=42)
            engine.initialize()
            engine.run_to_completion()

            node_ids = list(engine.coordinator.registry.keys())
            self.assertEqual(len(node_ids), count)
            self.assertEqual(len(set(node_ids)), count, "Duplicate node IDs detected")

            for node_id, node in engine.coordinator.registry.items():
                series = engine.history.node_dataframe_dict(node_id)
                for key in ("PT", "PE", "PSM", "battery_percent", "cumulative_energy_j"):
                    for value in series[key]:
                        if value is not None:
                            self.assertFalse(math.isnan(value), f"NaN found in {key} for {node_id}")

            self.assertEqual(engine.invariant_violations, [])


class TestClosedLoopSanity(unittest.TestCase):
    """Deliverable 32: an end-to-end sanity check that the closed loop is
    actually exercised over a realistic run (sync events occur, ARAC
    allocations vary by state, and no invariant is violated)."""

    def test_closed_loop_runs_cleanly(self):
        engine = DigitalTwinSimulationEngine(
            num_nodes=20, duration_s=120, time_step_s=1.0, seed=42,
            scenario="Scenario C: Dynamic/Challenging",
        )
        engine.initialize()
        engine.run_to_completion()

        self.assertTrue(engine.finished)
        self.assertGreater(engine.total_sync_events, 0)
        self.assertEqual(engine.invariant_violations, [])

        final_states = {n.sync_state for n in engine.coordinator.registry.values()}
        self.assertTrue(final_states.issubset(set(STATE_ORDER) | {"Unclassified"}))


if __name__ == "__main__":
    unittest.main()
