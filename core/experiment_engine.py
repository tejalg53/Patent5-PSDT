"""
Sprint 11: Controlled Experimental Comparison engine.

Configures and invokes the existing Sprint 10 DigitalTwinSimulationEngine
twice per (seed, scenario, node-count) combination: once under the fixed
Uniform Baseline policy, once under the PSM-Adaptive Proposed method,
holding every other configuration input identical (Deliverable 4: paired
design). This module does not duplicate the simulator or any DTCE/PEEE/
PSME/SCE/ARAC mathematics; it only orchestrates core/simulation_engine.py
with two different control_mode settings.
"""

from dataclasses import dataclass
from typing import List, Optional

from core.simulation_engine import DigitalTwinSimulationEngine
from core.experiment_metrics import compute_run_metrics
from config.baseline_policies import (
    MODEL_VERSION,
    DEFAULT_UNIFORM_POLICY,
    DEFAULT_SEED_LIST,
    DEFAULT_SCALABILITY_NODE_COUNTS,
    DEFAULT_SCALABILITY_SEED_COUNT,
    DISTURBANCE_START_FRACTION,
    DISTURBANCE_END_FRACTION,
    RECOVERY_PERSISTENCE_STEPS,
)
from config.simulation_profiles import (
    DEFAULT_DURATION_S,
    DEFAULT_TIME_STEP_S,
    DEFAULT_NETWORK_PROFILE,
    DEFAULT_SCENARIO,
    SCENARIO_OPTIONS,
)

_SCENARIO_CODE = {
    "Scenario A: Stable": "STA",
    "Scenario B: Moderate": "MOD",
    "Scenario C: Dynamic/Challenging": "CHA",
}


def generate_experiment_id(scenario: str, num_nodes: int, seed: int, control_mode: str) -> str:
    code = _SCENARIO_CODE.get(scenario, "SCN")
    strategy = "BASE" if control_mode == "uniform" else "PSM"
    return f"EXP-{code}-{num_nodes}N-S{seed}-{strategy}"


@dataclass
class ControlledExperiment:
    """One paired (Baseline vs Proposed) configuration. Call run_uniform()
    or run_adaptive() or run_pair() to execute it (Deliverable 2)."""

    seed: int
    nodes: int
    duration: float = DEFAULT_DURATION_S
    time_step: float = DEFAULT_TIME_STEP_S
    scenario: str = DEFAULT_SCENARIO
    network_profile: Optional[str] = None
    baseline_policy: str = DEFAULT_UNIFORM_POLICY
    history_mode: str = "experiment"

    def _make_engine(self, control_mode: str) -> DigitalTwinSimulationEngine:
        engine = DigitalTwinSimulationEngine(
            num_nodes=self.nodes,
            duration_s=self.duration,
            time_step_s=self.time_step,
            seed=self.seed,
            network_profile=self.network_profile or DEFAULT_NETWORK_PROFILE,
            scenario=self.scenario,
            history_mode=self.history_mode,
            control_mode=control_mode,
            baseline_policy=self.baseline_policy,
        )
        engine.model_version = MODEL_VERSION
        engine.experiment_id = generate_experiment_id(self.scenario, self.nodes, self.seed, control_mode)
        return engine

    def run_uniform(self) -> DigitalTwinSimulationEngine:
        engine = self._make_engine("uniform")
        engine.initialize()
        engine.run_to_completion()
        return engine

    def run_adaptive(self) -> DigitalTwinSimulationEngine:
        engine = self._make_engine("adaptive")
        engine.initialize()
        engine.run_to_completion()
        return engine

    def run_pair(self):
        """Returns (baseline_engine, proposed_engine), both seeded and
        configured identically apart from control_mode (Deliverable 4)."""
        return self.run_uniform(), self.run_adaptive()


def run_seed_matrix(nodes: int, duration: float, time_step: float, scenario: str,
                     seeds: List[int], baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                     progress_callback=None) -> dict:
    """Deliverable 9: run a paired Baseline/Proposed experiment across
    multiple independent seeds for one (scenario, node-count) config.
    Returns raw per-seed metrics for both strategies."""
    baseline_metrics, proposed_metrics = [], []
    for i, seed in enumerate(seeds):
        exp = ControlledExperiment(
            seed=seed, nodes=nodes, duration=duration, time_step=time_step,
            scenario=scenario, baseline_policy=baseline_policy,
        )
        base_engine, prop_engine = exp.run_pair()
        baseline_metrics.append(compute_run_metrics(base_engine))
        proposed_metrics.append(compute_run_metrics(prop_engine))
        if progress_callback:
            progress_callback(i + 1, len(seeds))
    return {"baseline": baseline_metrics, "proposed": proposed_metrics}


def run_scenario_matrix(nodes: int, duration: float, time_step: float, seeds: List[int],
                         scenarios: Optional[List[str]] = None,
                         baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                         progress_callback=None) -> dict:
    """Deliverable 7: run the seed matrix for each of the Stable/
    Moderate/Challenging scenarios."""
    scenarios = scenarios or SCENARIO_OPTIONS
    results = {}
    for scenario in scenarios:
        results[scenario] = run_seed_matrix(
            nodes=nodes, duration=duration, time_step=time_step, scenario=scenario,
            seeds=seeds, baseline_policy=baseline_policy, progress_callback=progress_callback,
        )
    return results


def run_scalability_matrix(scenario: str, duration: float, time_step: float,
                            node_counts: Optional[List[int]] = None,
                            seeds: Optional[List[int]] = None,
                            baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                            progress_callback=None) -> dict:
    """Deliverable 10: run the seed matrix at each node count to test
    whether the benefit persists as node count scales."""
    node_counts = node_counts or DEFAULT_SCALABILITY_NODE_COUNTS
    seeds = seeds or DEFAULT_SEED_LIST[:DEFAULT_SCALABILITY_SEED_COUNT]
    results = {}
    for n in node_counts:
        results[n] = run_seed_matrix(
            nodes=n, duration=duration, time_step=time_step, scenario=scenario,
            seeds=seeds, baseline_policy=baseline_policy, progress_callback=progress_callback,
        )
    return results


def run_body_zone_experiment(engine_baseline: DigitalTwinSimulationEngine,
                              engine_proposed: DigitalTwinSimulationEngine) -> dict:
    """Deliverable 11: body-zone resource/quality comparison for one
    already-completed paired run."""
    return {
        "baseline": engine_baseline.body_zone_summary(),
        "proposed": engine_proposed.body_zone_summary(),
    }


def run_disturbance_experiment(seed: int, nodes: int, duration: float, time_step: float,
                                scenario: str, baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                                node_id: Optional[str] = None) -> dict:
    """Deliverable 8: inject an explicit, identically-timed disturbance
    into both a Baseline and a Proposed run, and measure each method's
    PE/PSM/state/sync-interval response and recovery time. The same
    recovery criterion (non-negative PSM sustained for
    RECOVERY_PERSISTENCE_STEPS consecutive steps) is applied to both
    methods (Deliverable 8: do not define recovery differently)."""
    start_t = duration * DISTURBANCE_START_FRACTION
    end_t = duration * DISTURBANCE_END_FRACTION

    def _run_with_disturbance(control_mode: str) -> DigitalTwinSimulationEngine:
        exp = ControlledExperiment(
            seed=seed, nodes=nodes, duration=duration, time_step=time_step,
            scenario=scenario, baseline_policy=baseline_policy,
        )
        engine = exp._make_engine(control_mode)
        engine.initialize()
        disturbed = False
        while not engine.finished:
            engine.step()
            if not disturbed and engine.sim_time >= start_t:
                engine.inject_network_jitter(node_id)
                engine.inject_clock_drift_spike(node_id)
                disturbed = True
        return engine

    baseline_engine = _run_with_disturbance("uniform")
    proposed_engine = _run_with_disturbance("adaptive")

    def _recovery_time(engine, target_node_id):
        if target_node_id:
            series = engine.history.node_series[target_node_id]
            timestamps, psms = series["timestamp"], series["PSM"]
        else:
            g = engine.history.global_dataframe_dict()
            timestamps, psms = g["timestamp"], g["mean_psm"]
        consecutive = 0
        for t, psm in zip(timestamps, psms):
            if t < end_t or psm is None:
                continue
            if psm >= 0:
                consecutive += 1
                if consecutive >= RECOVERY_PERSISTENCE_STEPS:
                    return round(t - end_t, 3)
            else:
                consecutive = 0
        return None

    return {
        "disturbance_start_s": start_t,
        "disturbance_end_s": end_t,
        "baseline_engine": baseline_engine,
        "proposed_engine": proposed_engine,
        "baseline_recovery_s": _recovery_time(baseline_engine, node_id),
        "proposed_recovery_s": _recovery_time(proposed_engine, node_id),
    }
