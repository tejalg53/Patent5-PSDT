"""
Sprint 10 - Digital Twin Simulation Engine.

Orchestrates the existing Sprint 4-9 engines (DTCE, PEEE, PSME, SCE, ARAC,
wired together by CentralSynchronizationCoordinator) into a genuine
closed-loop, time-evolving digital twin:

    Node State(t) -> DTCE -> PEEE -> PSME -> SCE -> ARAC -> Resource Action
        -> Node State(t+dt)

This module does NOT reimplement any of the DTCE/PEEE/PSME/SCE/ARAC
mathematics. It only sequences the existing, already-tested Coordinator
methods in a fixed, documented per-cycle order, and adds the pieces those
earlier sprints explicitly deferred as "infrastructure for Sprint 10":
synchronization-interval-driven resynchronization effects, network-profile
jitter, scenario/context timelines, PRAP-driven resource application over
time, battery/energy bookkeeping, disturbance injection, simulation
invariant checks, and full time-series history recording.

One simulation cycle (fixed, documented order):

    1.  Update environmental/network conditions (scenario timeline)
    2.  Update node physical/technical state           (Coordinator)
    3.  Accumulate clock drift                          (Coordinator/PEEE)
    4.  Determine whether synchronization is due        (this engine)
    5.  Apply synchronization/resync effects if due     (this engine)
    6.  Generate/update PSSP measurements               (Coordinator)
    7.  DTCE  -> PTz(t)                                 (Coordinator)
    8.  PEEE  -> PEz(t)                                 (Coordinator)
    9.  PSME  -> PSMz(t)                                (Coordinator)
    10. SCE   -> synchronization state                  (Coordinator)
    11. ARAC  -> resource allocation                    (Coordinator)
    12. Generate/apply PRAP                             (Coordinator)
    13. Update resource configuration                   (Coordinator)
    14. Calculate communication/energy activity         (Coordinator + engine)
    15. Update battery/energy state                     (this engine)
    16. Record history                                  (this engine)
    17. Advance simulation clock                        (this engine)

Steps 2/3/6 are performed together by one call to the Coordinator's
existing run_communication_cycle(), which already advances every node's
raw timing measurements by elapsed time and generates/validates this
cycle's PSSPs (Sprint 4/6/9 infrastructure). Steps 4/5 (resynchronization)
are applied immediately afterward, using the just-grown clock drift, and
BEFORE step 7 (DTCE) / step 8 (PEEE) consume it: this is what closes the
loop. A synchronization event this cycle changes the clock drift that
PEEE will read this same cycle, which changes PE, PSM, state, and ARAC's
allocation, which changes the synchronization interval that governs when
the NEXT synchronization event fires.
"""

import random
from typing import Dict, List, Optional

from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator
from core.simulation_history import SimulationHistory
from core.error_profiles import NETWORK_DELAY_BOUNDS_MS, CLOCK_DRIFT_BOUNDS_MS

from config.simulation_profiles import (
    DEFAULT_DURATION_S,
    DEFAULT_TIME_STEP_S,
    DEFAULT_SEED,
    NETWORK_PROFILES,
    DEFAULT_NETWORK_PROFILE,
    SCENARIOS,
    DEFAULT_SCENARIO,
    RESYNC_RESIDUAL_MIN_MS,
    RESYNC_RESIDUAL_MAX_MS,
    INTERACTIVE_HISTORY_MAX_STEPS,
    DISTURBANCE_NETWORK_JITTER_SPIKE_MS,
    DISTURBANCE_CLOCK_DRIFT_SPIKE_MS,
    DISTURBANCE_ENVIRONMENT_STATE,
)
from config.energy_model import (
    NODE_BATTERY_CAPACITY_JOULES,
    SYNC_EVENT_ENERGY_J,
    PRAP_APPLY_ENERGY_J,
)


def _clamp(value: float, bounds) -> float:
    lo, hi = bounds
    return max(lo, min(hi, value))


class DigitalTwinSimulationEngine:
    """A single closed-loop, time-evolving Digital Twin simulation run."""

    def __init__(self, num_nodes: int = 30, duration_s: float = DEFAULT_DURATION_S,
                 time_step_s: float = DEFAULT_TIME_STEP_S, seed: int = DEFAULT_SEED,
                 network_profile: str = DEFAULT_NETWORK_PROFILE,
                 scenario: str = DEFAULT_SCENARIO, history_mode: str = "interactive"):
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario!r}")
        if network_profile not in NETWORK_PROFILES:
            raise ValueError(f"Unknown network profile: {network_profile!r}")

        self.num_nodes = num_nodes
        self.duration_s = float(duration_s)
        self.dt = float(time_step_s)
        self.seed = seed
        self.network_profile_name = network_profile
        self.scenario_name = scenario
        self.history_mode = history_mode

        self.coordinator: Optional[CentralSynchronizationCoordinator] = None
        self.history: Optional[SimulationHistory] = None

        self.sim_time = 0.0
        self.cycle = 0
        self.total_sync_events = 0
        self.total_state_transitions = 0
        self.invariant_violations: List[str] = []

        self._node_rngs: Dict[str, random.Random] = {}
        self._time_since_sync_ms: Dict[str, float] = {}
        self._last_sync_time_s: Dict[str, float] = {}
        self._active_network_profile = network_profile
        self._manual_motion_state: Optional[str] = None
        self._manual_environment_state: Optional[str] = None
        self._last_sync_fired: set = set()
        self._last_step_energy: Dict[str, float] = {}

        self.initialized = False
        self.finished = False

    def initialize(self) -> "DigitalTwinSimulationEngine":
        """Create a fresh Coordinator + node population and establish the
        t=0 state (Deliverables 1, 2)."""
        self.coordinator = CentralSynchronizationCoordinator(seed=self.seed)
        nodes = generate_nodes(self.num_nodes, self.seed)
        self.coordinator.register_nodes(nodes)

        max_steps = None if self.history_mode == "experiment" else INTERACTIVE_HISTORY_MAX_STEPS
        self.history = SimulationHistory(max_steps=max_steps)

        self._node_rngs = {n.node_id: random.Random(f"{self.seed}:{n.node_id}:sim10") for n in nodes}
        self._time_since_sync_ms = {n.node_id: 0.0 for n in nodes}
        self._last_sync_time_s = {n.node_id: 0.0 for n in nodes}

        self.sim_time = 0.0
        self.cycle = 0
        self.total_sync_events = 0
        self.total_state_transitions = 0
        self.invariant_violations = []
        self._manual_motion_state = None
        self._manual_environment_state = None
        self._last_sync_fired = set()
        self._last_step_energy = {}
        self.initialized = True
        self.finished = False

        self._apply_scenario_context(0.0)
        self._apply_network_profile()
        self.coordinator.run_dtce_pass()
        self.coordinator.run_peee_pass()
        self.coordinator.run_sce_pass()
        self.coordinator.run_arac_pass(elapsed_seconds=0.0)
        self._check_invariants()
        self._record_step()
        return self

    def reset(self) -> "DigitalTwinSimulationEngine":
        """Re-initialize with the same configuration (Deliverable 18)."""
        return self.initialize()

    def step(self) -> "DigitalTwinSimulationEngine":
        if not self.initialized or self.finished:
            return self

        self.cycle += 1
        self.sim_time = round(self.sim_time + self.dt, 6)

        self._apply_scenario_context(self.sim_time)
        self._apply_network_profile()

        self.coordinator.run_communication_cycle(simulation_timestamp=self.sim_time)
        self._apply_extra_network_jitter()

        self._last_sync_fired = self._process_synchronization()

        energy_before = {nid: n.energy_consumed for nid, n in self.coordinator.registry.items()}

        self.coordinator.run_dtce_pass()
        self.coordinator.run_peee_pass()
        self.coordinator.run_sce_pass()
        self.coordinator.run_arac_pass(elapsed_seconds=self.dt)

        transitions_this_step = sum(
            1 for n in self.coordinator.registry.values() if n.transition_flag
        )
        self.total_state_transitions += transitions_this_step

        self._apply_event_energy()
        self._deplete_battery(energy_before)

        self._check_invariants()

        self._record_step()

        if self.sim_time >= self.duration_s - 1e-9:
            self.finished = True
        return self

    def run_steps(self, n: int) -> "DigitalTwinSimulationEngine":
        for _ in range(n):
            if self.finished:
                break
            self.step()
        return self

    def run_to_completion(self, max_cycles: int = 100000) -> "DigitalTwinSimulationEngine":
        """Advance until duration_s is reached. Simulated time is decoupled
        from wall-clock time (Deliverable 2)."""
        guard = 0
        while not self.finished and guard < max_cycles:
            self.step()
            guard += 1
        return self

    def _current_scenario_phase(self, t: float):
        timeline = SCENARIOS[self.scenario_name]["timeline"]
        fraction = (t / self.duration_s) if self.duration_s > 0 else 0.0
        phase = timeline[0]
        for entry in timeline:
            if fraction >= entry[0]:
                phase = entry
        return phase

    def _apply_scenario_context(self, t: float) -> None:
        _, motion_state, network_profile, environment_state = self._current_scenario_phase(t)
        motion_state = self._manual_motion_state or motion_state
        environment_state = self._manual_environment_state or environment_state
        self.coordinator.set_perceptual_context(
            motion_state=motion_state, environment_state=environment_state
        )
        self._active_network_profile = network_profile

    def _apply_network_profile(self) -> None:
        profile = NETWORK_PROFILES[self._active_network_profile]
        self.coordinator.set_error_model_context(network_condition=profile["condition"])

    def _apply_extra_network_jitter(self) -> None:
        profile = NETWORK_PROFILES[self._active_network_profile]
        std = profile["extra_jitter_std_ms"]
        for node_id, node in self.coordinator.registry.items():
            rng = self._node_rngs[node_id]
            jitter = rng.gauss(0.0, std)
            node.network_delay = _clamp(node.network_delay + jitter, NETWORK_DELAY_BOUNDS_MS)

    def allocated_sync_interval_ms(self, node) -> float:
        if node.resource_status == "Adaptive" and node.allocated_sync_interval_ms:
            return node.allocated_sync_interval_ms
        return node.sync_interval * 1000.0

    def _process_synchronization(self) -> set:
        fired = set()
        dt_ms = self.dt * 1000.0
        for node_id, node in self.coordinator.registry.items():
            self._time_since_sync_ms[node_id] = self._time_since_sync_ms.get(node_id, 0.0) + dt_ms
            interval_ms = self.allocated_sync_interval_ms(node)
            if interval_ms <= 0:
                continue
            if self._time_since_sync_ms[node_id] >= interval_ms:
                rng = self._node_rngs[node_id]
                residual = rng.uniform(RESYNC_RESIDUAL_MIN_MS, RESYNC_RESIDUAL_MAX_MS)
                drift_before = node.clock_drift
                node.clock_drift = _clamp(residual, CLOCK_DRIFT_BOUNDS_MS)
                self._time_since_sync_ms[node_id] = 0.0
                self._last_sync_time_s[node_id] = self.sim_time
                self.total_sync_events += 1
                fired.add(node_id)
                self.history.log_event(
                    self.sim_time, node_id,
                    f"Synchronization event (CD {drift_before:.3f}ms -> {node.clock_drift:.3f}ms residual)",
                )
        return fired

    def _apply_event_energy(self) -> None:
        for node_id in self._last_sync_fired:
            self.coordinator.registry[node_id].energy_consumed += SYNC_EVENT_ENERGY_J
        for node_id, node in self.coordinator.registry.items():
            if node.sync_state != "Unclassified":
                node.energy_consumed += PRAP_APPLY_ENERGY_J

    def _deplete_battery(self, energy_before: Dict[str, float]) -> None:
        self._last_step_energy = {}
        for node_id, node in self.coordinator.registry.items():
            delta = max(0.0, node.energy_consumed - energy_before.get(node_id, node.energy_consumed))
            self._last_step_energy[node_id] = delta
            if delta > 0:
                battery_drop = (delta / NODE_BATTERY_CAPACITY_JOULES) * 100.0
                node.battery_level = _clamp(node.battery_level - battery_drop, (0.0, 100.0))

    def inject_network_jitter(self, node_id: Optional[str] = None) -> None:
        targets = [self.coordinator.registry[node_id]] if node_id else list(self.coordinator.registry.values())
        for node in targets:
            node.network_delay = _clamp(
                node.network_delay + DISTURBANCE_NETWORK_JITTER_SPIKE_MS, NETWORK_DELAY_BOUNDS_MS
            )
        self.history.log_event(self.sim_time, node_id or "ALL", "Disturbance: network jitter spike injected")

    def inject_clock_drift_spike(self, node_id: Optional[str] = None) -> None:
        targets = [self.coordinator.registry[node_id]] if node_id else list(self.coordinator.registry.values())
        for node in targets:
            node.clock_drift = _clamp(
                node.clock_drift + DISTURBANCE_CLOCK_DRIFT_SPIKE_MS, CLOCK_DRIFT_BOUNDS_MS
            )
        self.history.log_event(self.sim_time, node_id or "ALL", "Disturbance: clock drift spike injected")

    def set_motion_state(self, motion_state: Optional[str]) -> None:
        """Manual override; persists until cleared or reset() (Deliverable 28)."""
        self._manual_motion_state = motion_state
        self.history.log_event(self.sim_time, "ALL", f"Disturbance: motion state manually set to {motion_state}")

    def increase_environmental_disturbance(self) -> None:
        self._manual_environment_state = DISTURBANCE_ENVIRONMENT_STATE
        self.history.log_event(self.sim_time, "ALL", "Disturbance: environmental disturbance increased")

    def clear_manual_overrides(self) -> None:
        self._manual_motion_state = None
        self._manual_environment_state = None

    def _check_invariants(self) -> List[str]:
        violations = []
        for node_id, node in self.coordinator.registry.items():
            pt, pe, psm = node.perceptual_threshold, node.perceived_error, node.psm
            if pt is not None and pt <= 0:
                violations.append(f"{node_id}: PT <= 0 ({pt})")
            if pe is not None and pe < 0:
                violations.append(f"{node_id}: PE < 0 ({pe})")
            if pt is not None and pe is not None and psm is not None:
                if abs(psm - (pt - pe)) > 1e-6:
                    violations.append(f"{node_id}: PSM != PT - PE")
                if node.normalized_psm is not None and pt:
                    if abs(node.normalized_psm - (psm / pt)) > 1e-6:
                        violations.append(f"{node_id}: NPSM != PSM / PT")
                if node.threshold_utilization_pct is not None and pt:
                    if abs(node.threshold_utilization_pct - (pe / pt * 100.0)) > 1e-6:
                        violations.append(f"{node_id}: TU != PE / PT * 100")
            if not (0.0 <= node.battery_level <= 100.0):
                violations.append(f"{node_id}: battery out of range ({node.battery_level})")
            if node.energy_consumed < 0:
                violations.append(f"{node_id}: negative energy_consumed")
            if node.allocated_sync_interval_ms is not None and node.allocated_sync_interval_ms <= 0:
                violations.append(f"{node_id}: sync interval <= 0")
            if node.allocated_beacon_interval_ms is not None and node.allocated_beacon_interval_ms <= 0:
                violations.append(f"{node_id}: beacon interval <= 0")
        if violations:
            self.invariant_violations.extend(violations)
            for v in violations:
                self.history.log_event(self.sim_time, "INVARIANT", v)
        return violations

    def _record_step(self) -> None:
        pts, pes, psms, batteries = [], [], [], []
        state_counts: Dict[str, int] = {}
        step_energy = self._last_step_energy

        for node_id, node in self.coordinator.registry.items():
            self.history.record_node_step(
                node_id,
                step=self.cycle, timestamp=self.sim_time,
                PT=node.perceptual_threshold, CD=node.clock_drift, ND=node.network_delay,
                AD=node.actuator_driver_delay, MD=node.mechanical_startup_delay,
                PE=node.perceived_error, PSM=node.psm, NPSM=node.normalized_psm,
                TU=node.threshold_utilization_pct,
                current_state=node.sync_state, previous_state=node.previous_state,
                sync_interval_ms=self.allocated_sync_interval_ms(node),
                beacon_interval_ms=node.allocated_beacon_interval_ms,
                radio_wakeup_interval_ms=node.allocated_radio_wakeup_interval_ms,
                tx_power_pct=node.allocated_transmit_power_pct,
                trigger_offset_ms=node.allocated_trigger_offset_ms,
                sync_event=node_id in self._last_sync_fired,
                state_transition=bool(node.transition_flag),
                step_energy_j=step_energy.get(node_id, 0.0),
                cumulative_energy_j=node.energy_consumed,
                battery_percent=node.battery_level,
            )
            if node.perceptual_threshold is not None:
                pts.append(node.perceptual_threshold)
            if node.perceived_error is not None:
                pes.append(node.perceived_error)
            if node.psm is not None:
                psms.append(node.psm)
            batteries.append(node.battery_level)
            state_counts[node.sync_state] = state_counts.get(node.sync_state, 0) + 1

        packet_counts = self.coordinator.get_packet_counts()
        messages_cum = (
            packet_counts["generated"] + self.coordinator.prap_generated + self.total_sync_events
        )
        self.history.record_global_step(
            step=self.cycle, timestamp=self.sim_time, state_counts=state_counts,
            mean_pt=sum(pts) / len(pts) if pts else None,
            mean_pe=sum(pes) / len(pes) if pes else None,
            mean_psm=sum(psms) / len(psms) if psms else None,
            sync_events_cum=self.total_sync_events,
            state_transitions_cum=self.total_state_transitions,
            messages_cum=messages_cum,
            energy_cum_j=sum(n.energy_consumed for n in self.coordinator.registry.values()),
            mean_battery_percent=sum(batteries) / len(batteries) if batteries else None,
        )

    def status(self) -> dict:
        state_counts: Dict[str, int] = {}
        for node in self.coordinator.registry.values():
            state_counts[node.sync_state] = state_counts.get(node.sync_state, 0) + 1
        return {
            "sim_time": self.sim_time,
            "duration_s": self.duration_s,
            "cycle": self.cycle,
            "active_nodes": len(self.coordinator.registry),
            "sync_events": self.total_sync_events,
            "state_transitions": self.total_state_transitions,
            "prap_applied": self.coordinator.prap_generated,
            "energy_consumed_j": sum(n.energy_consumed for n in self.coordinator.registry.values()),
            "finished": self.finished,
            "state_counts": state_counts,
            "invariant_violations": len(self.invariant_violations),
        }

    def node_inspector(self, node_id: str, recent: int = 20) -> dict:
        node = self.coordinator.registry[node_id]
        series = self.history.node_dataframe_dict(node_id)
        recent_events = [e for e in self.history.recent_events(200) if e["node_id"] == node_id][:recent]
        return {
            "node": node,
            "time_since_last_sync_ms": self._time_since_sync_ms.get(node_id),
            "last_sync_time_s": self._last_sync_time_s.get(node_id),
            "next_sync_due_s": (
                self._last_sync_time_s.get(node_id, 0.0)
                + self.allocated_sync_interval_ms(node) / 1000.0
            ),
            "series": series,
            "recent_events": recent_events,
        }

    def body_zone_summary(self) -> dict:
        zones: Dict[str, dict] = {}
        for node in self.coordinator.registry.values():
            z = zones.setdefault(node.body_zone, {
                "count": 0, "pt": [], "pe": [], "psm": [], "sync_interval_ms": [],
                "sync_events": 0, "energy_j": 0.0,
            })
            z["count"] += 1
            if node.perceptual_threshold is not None:
                z["pt"].append(node.perceptual_threshold)
            if node.perceived_error is not None:
                z["pe"].append(node.perceived_error)
            if node.psm is not None:
                z["psm"].append(node.psm)
            z["sync_interval_ms"].append(self.allocated_sync_interval_ms(node))
            z["energy_j"] += node.energy_consumed

        for node_id in self._last_sync_fired:
            zone = self.coordinator.registry[node_id].body_zone
            zones[zone]["sync_events"] += 1

        summary = {}
        for zone, z in zones.items():
            summary[zone] = {
                "count": z["count"],
                "mean_pt": sum(z["pt"]) / len(z["pt"]) if z["pt"] else None,
                "mean_pe": sum(z["pe"]) / len(z["pe"]) if z["pe"] else None,
                "mean_psm": sum(z["psm"]) / len(z["psm"]) if z["psm"] else None,
                "mean_sync_interval_ms": sum(z["sync_interval_ms"]) / len(z["sync_interval_ms"]),
                "sync_events_this_step": z["sync_events"],
                "energy_j": z["energy_j"],
            }
        return summary
