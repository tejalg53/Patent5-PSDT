PSDT Patent 5 -- Final Evidence Package
=======================================
Generated: 2026-07-25T15:58:49.045236+00:00

Model Version:      PSDT v1.0 Patent 5 Experimental Validation Build
Configuration ID:    PSDT-V1-CFG-B08718D8
Configuration SHA256: B08718D8EDA5BCF6015549CBDAFA026E6E4BA48D60ADFAC2BBEF337A845E9ADB
Frozen at git commit: 358e75805c3fa4b460a8fcbed7fc05f86338e992

What PSDT simulates
-------------------
PSDT (Perceptual Synchronization Digital Twin) is a software simulation of a distributed
wearable haptic network (Patent 5). Each simulated node represents a haptic actuator at a
body zone (Fingertip, Hand, Forearm, Torso, Leg, Foot). The simulation models, per node and
per time step: a Dynamic Threshold Computation Engine (DTCE) estimating a perceptual
threshold PT(t); a Perceptual Error Estimation Engine (PEEE) estimating perceived
synchronization error PE(t); a Perceptual Synchronization Margin Engine (PSME) computing
PSM(t) = PT(t) - PE(t) and its normalized/utilization forms; a State Classification Engine
(SCE) assigning an operational state from PSM with hysteresis; and an Adaptive Resource
Allocation Controller (ARAC) that maps state to synchronization/beacon/wake-up intervals,
transmit power, and trigger offsets, applied via a placeholder Resource Application layer
(PRAP). An energy-accounting model estimates communication energy from radio-active time.

Uniform Baseline vs PSM-Adaptive
---------------------------------
The Uniform Baseline applies one fixed synchronization/resource policy to every node,
regardless of body zone or measured PSM. The PSM-Adaptive ("proposed", full Patent 5) system
drives resource allocation from each node's own body-zone-specific PSM via the SCE/ARAC chain
described above. Both strategies are run with identical seeds, node/body-zone/actuator
distributions, drift and network-disturbance sequences, context/scenario timelines, duration,
and energy coefficients -- only the synchronization/resource-control strategy differs
(see validation/baseline_fairness.csv).

How experiments were paired
---------------------------
For every (scenario, node-count, seed) combination, a Uniform run and a PSM-Adaptive run are
constructed from the same seed and configuration and executed step-by-step in parallel
(paired design), so any difference in outcome is attributable to the control strategy alone.
The frozen final experiment matrix is 3 scenarios x 5 node counts x 10 seeds x 2 strategies
= 300 runs (see raw_data/experiment_runs.csv and this manifest: expected=300,
completed=300, failed=0,
excluded=0).

How to interpret violation rate
--------------------------------
"Violation rate" is the modeled percentage of observed time steps where PSM(t) < 0, i.e. the
estimated perceived synchronization error exceeded the modeled perceptual threshold for that
node at that step. It is a simulation-internal quantity computed from PT(t) and PE(t) as
modeled by DTCE/PEEE -- it is not a measurement of human perception. Both a relative
percentage change and an absolute percentage-point change are reported where relevant, since
absolute pp changes are clearer than relative percentages alone for small baseline rates.

Pre-registered success criterion: success=True,
energy_reduced=True, messages_reduced=True,
violation_diff_pp=-0.13953488372093023, tolerance_pp=5.0.

What is simulated vs experimentally measured
---------------------------------------------
EVERYTHING in this package is produced by a software simulation (PSDT). PT, PE, PSM, states,
resource allocations, and energy are all modeled/estimated quantities computed by the code in
core/ under the frozen configuration in configuration/final_configuration.json. These are
simulation validation results, not physical hardware measurements and not human-subject
clinical or perceptual validation. No claim in this package should be read as a measurement of
real human perception, real radio hardware, or real battery life.

Package contents
----------------
configuration/   final_configuration.json, model_version.txt -- the frozen model/parameter set
raw_data/        experiment_runs.csv (300-run matrix, run-level) plus node_metrics.csv,
                 time_series.csv, state_transitions.csv, resource_allocations.csv (node- and
                 time-step-level detail from one fully-instrumented representative run at the
                 frozen primary configuration: Nodes=30, Duration=300s, dt=1s,
                 Scenario=Moderate, Seed=42, both strategies)
summaries/       core_results.csv, scenario_results.csv, body_zone_results.csv,
                 scalability_results.csv, sensitivity_results.csv, ablation_results.csv
validation/      reproducibility_report.csv, invariant_audit.csv, baseline_fairness.csv,
                 traceability_test.csv
figures/         sync_messages.png, estimated_energy.png, violation_rate.png,
                 body_zone_sync.png, disturbance_response.png, scalability.png (each with a
                 matching *.provenance.json carrying Model Version, Configuration ID,
                 scenario/node-count/seeds/strategies, and generation timestamp)
