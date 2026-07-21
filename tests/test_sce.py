"""
Sprint 8 - Validation checks for the Synchronization Classification
Engine (SCE) and its integration into the Coordinator pipeline.

Run with:
    python3 -m unittest tests.test_sce -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.sce import (
    SynchronizationClassificationEngine,
    RELAXED,
    NOMINAL,
    ELEVATED,
    IMMEDIATE,
    STATE_ORDER,
)
from config.state_boundaries import (
    RELAXED_MIN,
    NOMINAL_MIN,
    ELEVATED_MIN,
    HYSTERESIS_MARGIN,
    STATE_PERSISTENCE_CYCLES,
)


class TestSCEBoundaryClassification(unittest.TestCase):
    """Deliverable 17: boundary classification tests."""

    def setUp(self):
        self.sce = SynchronizationClassificationEngine()

    def test_high_npsm_is_relaxed(self):
        result = self.sce.classify(npsm=RELAXED_MIN + 0.10)
        self.assertEqual(result.current_state, RELAXED)

    def test_medium_npsm_is_nominal(self):
        midpoint = (NOMINAL_MIN + RELAXED_MIN) / 2
        result = self.sce.classify(npsm=midpoint)
        self.assertEqual(result.current_state, NOMINAL)

    def test_low_positive_npsm_is_elevated(self):
        midpoint = (ELEVATED_MIN + NOMINAL_MIN) / 2
        result = self.sce.classify(npsm=midpoint)
        self.assertEqual(result.current_state, ELEVATED)

    def test_negative_npsm_is_immediate(self):
        result = self.sce.classify(npsm=-0.25)
        self.assertEqual(result.current_state, IMMEDIATE)

    def test_only_four_locked_states_exist(self):
        self.assertEqual(set(STATE_ORDER), {RELAXED, NOMINAL, ELEVATED, IMMEDIATE})


class TestSCEHysteresis(unittest.TestCase):
    """Deliverable 18: hysteresis tests - tiny fluctuations around a
    boundary must not produce repeated state changes."""

    def setUp(self):
        self.sce = SynchronizationClassificationEngine()

    def test_small_fluctuation_around_boundary_does_not_flip_state(self):
        # Start comfortably inside NOMINAL.
        state = NOMINAL
        pending = None
        counter = 0

        just_above = NOMINAL_MIN + (HYSTERESIS_MARGIN / 2)
        just_below = NOMINAL_MIN - (HYSTERESIS_MARGIN / 2)

        for npsm in [just_below, just_above, just_below, just_above, just_below]:
            result = self.sce.classify(
                npsm=npsm, previous_state=state, pending_state=pending,
                persistence_counter=counter,
            )
            state = result.current_state
            pending = result.pending_state
            counter = result.persistence_counter
            # A fluctuation smaller than the hysteresis margin must never
            # commit a transition away from NOMINAL.
            self.assertEqual(state, NOMINAL)


class TestSCEPersistence(unittest.TestCase):
    """Deliverable 19: persistence / dwell-time tests."""

    def setUp(self):
        self.sce = SynchronizationClassificationEngine()

    def test_state_changes_only_after_dwell_time_satisfied(self):
        # Comfortably inside NOMINAL, then a sustained drop well past the
        # hysteresis band into ELEVATED territory.
        state = NOMINAL
        pending = None
        counter = 0
        low_npsm = ELEVATED_MIN + 0.01

        results = []
        for _ in range(STATE_PERSISTENCE_CYCLES):
            result = self.sce.classify(
                npsm=low_npsm, previous_state=state, pending_state=pending,
                persistence_counter=counter,
            )
            results.append(result)
            pending = result.pending_state
            counter = result.persistence_counter
            if result.transition:
                state = result.current_state

        # Every cycle before the last must NOT have committed the change.
        for result in results[:-1]:
            self.assertFalse(result.transition)
            self.assertEqual(result.current_state, NOMINAL)

        # The final cycle (after STATE_PERSISTENCE_CYCLES observations)
        # must commit the transition to ELEVATED.
        self.assertTrue(results[-1].transition)
        self.assertEqual(results[-1].current_state, ELEVATED)


class TestSCETransitionDetection(unittest.TestCase):
    """Deliverable 20: transition flag correctness."""

    def setUp(self):
        self.sce = SynchronizationClassificationEngine()

    def test_transition_true_only_when_state_actually_changes(self):
        result = self.sce.classify(npsm=0.80, previous_state=None)
        self.assertTrue(result.transition)  # first-ever classification

        result2 = self.sce.classify(npsm=0.81, previous_state=result.current_state)
        self.assertFalse(result2.transition)
        self.assertEqual(result2.current_state, result.current_state)


class TestSCEInvalidInput(unittest.TestCase):
    """Deliverable 23: invalid input handling - no operational state is
    ever assigned from malformed data."""

    def setUp(self):
        self.sce = SynchronizationClassificationEngine()

    def test_none_npsm_is_rejected_safely(self):
        result = self.sce.safe_classify(npsm=None, previous_state=NOMINAL)
        self.assertEqual(result.status, "INVALID_INPUT")
        self.assertEqual(result.current_state, NOMINAL)

    def test_nan_npsm_is_rejected_safely(self):
        result = self.sce.safe_classify(npsm=float("nan"), previous_state=RELAXED)
        self.assertEqual(result.status, "INVALID_INPUT")
        self.assertEqual(result.current_state, RELAXED)

    def test_infinite_npsm_is_rejected_safely(self):
        result = self.sce.safe_classify(npsm=float("inf"), previous_state=ELEVATED)
        self.assertEqual(result.status, "INVALID_INPUT")
        self.assertEqual(result.current_state, ELEVATED)

    def test_invalid_previous_state_is_rejected_safely(self):
        result = self.sce.safe_classify(npsm=0.5, previous_state="Warning")
        self.assertEqual(result.status, "INVALID_INPUT")

    def test_strict_classify_raises_on_invalid_input(self):
        with self.assertRaises(ValueError):
            self.sce.classify(npsm=None)
        with self.assertRaises(ValueError):
            self.sce.classify(npsm=float("nan"))


class TestSCECoordinatorIntegration(unittest.TestCase):
    """Deliverables 9, 21, 22: Coordinator wiring, scalability and
    reproducibility."""

    def _build(self, num_nodes=30, seed=42):
        nodes = generate_nodes(num_nodes, seed=seed)
        coordinator = CentralSynchronizationCoordinator()
        coordinator.register_nodes(nodes)
        return nodes, coordinator

    def test_pipeline_runs_dtce_peee_psme_sce_in_order(self):
        _, coordinator = self._build()
        coordinator.run_communication_cycle(simulation_timestamp=1.0)
        for node in coordinator.registry.values():
            self.assertIsNotNone(node.perceptual_threshold)
            self.assertIsNotNone(node.perceived_error)
            self.assertIsNotNone(node.psm)
            self.assertIn(node.sync_state, list(STATE_ORDER) + ["Unclassified"])

    def test_scalability_across_node_counts(self):
        for num_nodes in [10, 20, 30, 40, 50]:
            _, coordinator = self._build(num_nodes=num_nodes)
            coordinator.run_communication_cycle(simulation_timestamp=1.0)
            classified = [
                n for n in coordinator.registry.values()
                if n.sync_state != "Unclassified"
            ]
            self.assertEqual(len(classified), num_nodes)

    def test_reproducibility_same_seed_same_state_sequence(self):
        _, coordinator_a = self._build(num_nodes=20, seed=7)
        _, coordinator_b = self._build(num_nodes=20, seed=7)

        for t in range(1, 6):
            coordinator_a.run_communication_cycle(simulation_timestamp=float(t))
            coordinator_b.run_communication_cycle(simulation_timestamp=float(t))

        states_a = {nid: n.sync_state for nid, n in coordinator_a.registry.items()}
        states_b = {nid: n.sync_state for nid, n in coordinator_b.registry.items()}
        self.assertEqual(states_a, states_b)

        history_a = {nid: n.state_history for nid, n in coordinator_a.registry.items()}
        history_b = {nid: n.state_history for nid, n in coordinator_b.registry.items()}
        self.assertEqual(history_a, history_b)

    def test_state_history_is_bounded_rolling_buffer(self):
        _, coordinator = self._build(num_nodes=5, seed=1)
        from core.node import MAX_STATE_HISTORY_LENGTH
        for t in range(1, MAX_STATE_HISTORY_LENGTH + 20):
            coordinator.run_communication_cycle(simulation_timestamp=float(t))
        for node in coordinator.registry.values():
            self.assertLessEqual(len(node.state_history), MAX_STATE_HISTORY_LENGTH)


if __name__ == "__main__":
    unittest.main()
