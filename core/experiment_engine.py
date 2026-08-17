"""
Sprint 11: Controlled Experimental Comparison engine.

Configures and invokes the existing Sprint 10 DigitalTwinSimulationEngine
twice per (seed, scenario, node-count) combination: once under the fixed
Uniform Baseline policy, once under the PSM-Adaptive Proposed method,
holding every other configuration input identical (Deliverable 4: paired
design). This module does not duplicate the simulator or any DTCE/PEEE/
PSME/SCE/ARAC mathematics; it only orchestrates core/simulation_engine.py
with two different control_mode settings.

Sprint 14 (Patent strengthening, Changes 3-5) adds:

- ControlledExperiment.run_pe_only() / run_pt_only(): run the two new
  ablation arms (Method B "PE-only adaptive", Method C "PT-only /
  non-stateful adaptive") added to core/simulation_engine.py.
- run_ablation_study(): Change 4, the four-way controlled ablation
  study (Method A "Uniform", Method B "PE-only adaptive", Method C
  "PT-only / non-stateful adaptive", Method D "Full PSM-Adaptive").
- run_adaptation_sweep(): Change 3, runs the full PSM-Adaptive method
  at each adaptation_level (Mild/Moderate/Aggressive) to trace the
  resource-reduction-vs-perceptual-violation-rate trade-off curve.
- run_hysteresis_ablation(): Change 5, compares the full PSM-Adaptive
  method with hysteresis (Method D) against the same method without
  hysteresis (Method C, "PT-only / non-stateful") to quantify the
  effect of hysteresis/persistence on state transitions, resource
  reallocations, synchronization messages, energy, and perceptual
  violation rate.

None of these additions alter the frozen 'uniform' or 'adaptive' code
paths; every new entry point is purely additive.
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
from config.resource_profiles import ADAPTATION_LEVEL_OPTIONS, DEFAULT_ADAPTATION_LEVEL


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
    # Sprint 14 Change 3: forwarded to the Coordinator's ARAC instance
    # for every non-"uniform" control_mode. None reproduces the exact
    # frozen Sprint 9 behavior ("Mild" / scale 1.0).
    adaptation_level: Optional[str] = None

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
            adaptation_level=self.adaptation_level,
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

    def run_generic_adaptive(self) -> DigitalTwinSimulationEngine:
        """Sprint 12 Deliverable 8 (ablation Method B): adaptive resource
        control driven by a single population-mean NPSM instead of each
        node's own body-zone-specific NPSM. See CentralSynchronizationCoordinator
        (generic_control=True) for the exact mechanism. Does not alter the
        frozen 'uniform' or 'adaptive' (full Patent 5 / Method C) code paths."""
        engine = self._make_engine("generic_adaptive")
        engine.initialize()
        engine.run_to_completion()
        return engine

    def run_pe_only(self) -> DigitalTwinSimulationEngine:
        """Sprint 14 Change 4 (ablation Method B, "error-only adaptive"):
        adaptive resource control driven only by each node's raw
        Estimated Perceived Error, ignoring the personalized Dynamic
        Perceptual Threshold entirely. See CentralSynchronizationCoordinator
        (pe_only_control=True) for the exact mechanism."""
        engine = self._make_engine("pe_only_adaptive")
        engine.initialize()
        engine.run_to_completion()
        return engine

    def run_pt_only(self) -> DigitalTwinSimulationEngine:
        """Sprint 14 Change 4 (ablation Method C, "perceptual-threshold-
        only / non-stateful adaptive"): the normal PT/PE-derived NPSM
        classification with hysteresis and dwell-time persistence
        disabled (reacts immediately every cycle). See
        CentralSynchronizationCoordinator (hysteresis_enabled=False)."""
        engine = self._make_engine("pt_only_adaptive")
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


def run_ablation_study(nodes: int, duration: float, time_step: float, scenario: str,
                        seeds: List[int], baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                        progress_callback=None) -> dict:
    """Sprint 14 Change 4: runs the four-way controlled ablation study
    (Method A "Uniform", Method B "PE-only adaptive", Method C "PT-only
    / non-stateful adaptive", Method D "Full PSM-Adaptive") across
    multiple seeds for one (scenario, node-count) configuration, holding
    every other input identical apart from control_mode. Returns raw
    per-seed metrics for all four methods."""
    results = {"uniform": [], "pe_only": [], "pt_only": [], "adaptive": []}
    for i, seed in enumerate(seeds):
        exp = ControlledExperiment(
            seed=seed, nodes=nodes, duration=duration, time_step=time_step,
            scenario=scenario, baseline_policy=baseline_policy,
        )
        results["uniform"].append(compute_run_metrics(exp.run_uniform()))
        results["pe_only"].append(compute_run_metrics(exp.run_pe_only()))
        results["pt_only"].append(compute_run_metrics(exp.run_pt_only()))
        results["adaptive"].append(compute_run_metrics(exp.run_adaptive()))
        if progress_callback:
            progress_callback(i + 1, len(seeds))
    return results


def run_adaptation_sweep(nodes: int, duration: float, time_step: float, scenario: str,
                          seeds: List[int], levels: Optional[List[str]] = None,
                          progress_callback=None) -> dict:
    """Sprint 14 Change 3: runs the full PSM-Adaptive method (Method D)
    at each adaptation_level (Mild/Moderate/Aggressive resource scaling,
    config/resource_profiles.py) across multiple seeds, to trace the
    resource-reduction-vs-perceptual-violation-rate trade-off curve.
    Returns raw per-seed metrics for each level."""
    levels = levels or ADAPTATION_LEVEL_OPTIONS
    results = {}
    total = len(levels) * len(seeds)
    done = 0
    for level in levels:
        level_metrics = []
        for seed in seeds:
            exp = ControlledExperiment(
                seed=seed, nodes=nodes, duration=duration, time_step=time_step,
                scenario=scenario, adaptation_level=level,
            )
            level_metrics.append(compute_run_metrics(exp.run_adaptive()))
            done += 1
            if progress_callback:
                progress_callback(done, total)
        results[level] = level_metrics
    return results


def run_hysteresis_ablation(nodes: int, duration: float, time_step: float, scenario: str,
                             seeds: List[int], baseline_policy: str = DEFAULT_UNIFORM_POLICY,
                             progress_callback=None) -> dict:
    """Sprint 14 Change 5: runs the full PSM-Adaptive method both with
    hysteresis (Method D, the frozen default) and without hysteresis
    (Method C, "PT-only / non-stateful") across multiple seeds, holding
    every other input identical, to compare state transitions, resource
    reallocations, synchronization messages, energy, and perceptual
    violation rate with vs without hysteresis/dwell-time persistence."""
    results = {"without_hysteresis": [], "with_hysteresis": []}
    for i, seed in enumerate(seeds):
        exp = ControlledExperiment(
            seed=seed, nodes=nodes, duration=duration, time_step=time_step,
            scenario=scenario, baseline_policy=baseline_policy,
        )
        results["without_hysteresis"].append(compute_run_metrics(exp.run_pt_only()))
        results["with_hysteresis"].append(compute_run_metrics(exp.run_adaptive()))
        if progress_callback:
            progress_callback(i + 1, len(seeds))
    return results
