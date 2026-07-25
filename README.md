# Perceptual Synchronization Digital Twin (PSDT)

This project implements the Digital Twin platform for Patent 5: "A Perceptual Synchronization
Margin-Based Adaptive Resource Allocation Method and System for Distributed Wearable Haptic
Systems." The platform simulates a distributed wearable haptic node network, adaptive
synchronization control, perceptual-synchronization-margin computation, and energy-aware
resource allocation, and produces the experimental evidence used to support the patent's
technical-effect claims.

**Model version:** `PSDT v1.0 Patent 5 Experimental Validation Build` (frozen; see
`results/configuration/final_configuration.json` for the exact parameter set and hash).

**Important:** everything described below is produced by a software simulation. PT, PE, PSM,
operational states, resource allocations, and energy figures are all *modeled/estimated*
quantities computed by the code in `core/`. These are simulation validation results, not
physical hardware measurements, and not human-subject clinical or perceptual validation.

## What PSDT simulates

Each simulated node represents a haptic actuator worn at a body zone (Fingertip, Hand,
Forearm, Torso, Leg, Foot). At every discrete time step, for every node, the simulation runs
the patent's processing chain:

`Raw technical inputs -> DTCE -> PT(t) -> PEEE -> PE(t) -> PSME -> PSM(t)/NPSM(t)/TU(t) -> SCE
-> Operational State -> ARAC -> Resource Allocation -> PRAP -> Node Configuration`

## How PT is modeled (DTCE)

The Dynamic Threshold Computation Engine estimates a per-node perceptual threshold
`PT(t)` as a body-zone base threshold scaled by multiplicative factors: a frequency factor
(vibration frequency), an actuator-type factor, a user-calibration factor, a motion-state
factor, and an environment-state factor:
`PT = base_threshold[body_zone] * frequency_factor * actuator_factor * calibration_factor *
motion_factor * environment_factor`.

## How PE is modeled (PEEE)

The Perceptual Error Estimation Engine estimates the perceived synchronization error `PE(t)`
from four timing-degradation sources -- clock drift (CD), network delay (ND), actuator-driver
delay (AD), and mechanical-startup delay (MD) -- combined through a configurable weighted
model (`resolved_weights`). Clock drift, network delay, and actuator-driver delay evolve
stochastically over the simulated run (drift growth, jitter) within configured bounds.

## How PSM is calculated (PSME)

The Perceptual Synchronization Margin Engine computes:
- `PSM(t) = PT(t) - PE(t)` (the modeled margin between threshold and estimated error)
- `NPSM(t) = PSM(t) / PT(t)` (normalized margin)
- `TU(t) = PE(t) / PT(t) * 100` (threshold utilization, percent)

## How states are assigned (SCE)

The State Classification Engine maps `NPSM(t)` to an operational state (e.g. Relaxed,
Nominal, Elevated/Alert) using configured state boundaries with a hysteresis margin and a
persistence requirement, so a node must cross a boundary by more than the hysteresis margin
and hold that condition for a minimum number of steps before its state changes -- this avoids
rapid state chattering from small perceptual-margin fluctuations.

## How ARAC controls resources

The Adaptive Resource Allocation Controller maps each node's operational state to concrete
resource settings: synchronization interval, beacon interval, radio wake-up interval,
transmit power level, and trigger-offset logic. More conservative states (lower margin)
receive tighter/more frequent synchronization settings; more relaxed states receive longer
intervals and lower transmit power, reducing radio activity and energy use without letting
the modeled perceptual margin go negative.

## How energy is estimated

A simple accounting model estimates communication energy from radio-active time, using
configured per-active-second energy coefficients (by transmit-power level), a wake-up energy
cost, and a per-sync-event messaging cost. This is an estimated/simulated energy figure, not a
measurement of real radio hardware or real battery life.

## Uniform Baseline vs PSM-Adaptive

- **Uniform Baseline:** every node uses one fixed synchronization/resource policy, regardless
  of body zone or measured PSM.
- **PSM-Adaptive ("proposed", full Patent 5 system):** resource allocation is driven by each
  node's own body-zone-specific PSM via the SCE/ARAC chain above.

A third method, **Generic-Adaptive**, is also implemented for the Sprint 12 ablation study: it
uses the same adaptive SCE/ARAC control loop but drives every node from a single
population-mean NPSM instead of each node's own body-zone-specific value, isolating whether
body-zone differentiation itself (rather than adaptivity in general) contributes technical
value.

## How experiments were paired

For every (scenario, node-count, seed) combination, a Uniform run and a PSM-Adaptive run are
constructed from the identical seed, node/body-zone/actuator distribution, clock-drift and
network-disturbance sequence, context/scenario timeline, duration, and energy coefficients --
only the synchronization/resource-control strategy differs (see
`results/validation/baseline_fairness.csv`). The frozen final experiment matrix is 3 scenarios
x 5 node counts x 10 seeds x 2 strategies = 300 runs.

## How to interpret violation rate

"Violation rate" is the modeled percentage of observed time steps where `PSM(t) < 0`, i.e. the
estimated perceived error exceeded the modeled perceptual threshold for that node at that
step. It is a simulation-internal quantity computed from `PT(t)` and `PE(t)` -- it is not a
measurement of human perception. Reports typically include both the relative percentage
change and the absolute percentage-point change between Baseline and Proposed, since absolute
pp changes are clearer than relative percentages alone when baseline rates are small.

## What is simulated vs experimentally measured

Everything in `results/` is produced by the PSDT software simulation under the frozen
configuration in `results/configuration/final_configuration.json`. No number in this repository
should be read as a measurement of real human perception, real radio hardware, or real battery
life -- these are simulation validation results only.

## Repository layout

- `core/` -- the DTCE/PEEE/PSME/SCE/ARAC/PRAP simulation engine, node model, coordinator, and
  experiment/metrics helpers.
- `config/` -- frozen parameters: baseline policies, energy model, resource profiles,
  simulation profiles, state boundaries.
- `pages/` + `app.py` -- the Streamlit application (Home, Patent Architecture, Simulation,
  Analytics, Comparison, **Final Validation**, About).
- `scripts/` -- Sprint 12 audit/table/graph/export scripts (`sprint12_*.py`).
- `results/` -- all frozen configuration, raw data, aggregate summaries, validation reports,
  and figures referenced throughout this README and the Final Validation dashboard.
- `exports/` -- the assembled `PSDT_Patent5_Final_Evidence` package and zip (Deliverable 20).
- `tests/` -- the automated regression test suite.

## Running the app

```
pip install -r requirements.txt
streamlit run app.py
```

See the **Final Validation** page for the current reproducibility, invariant, baseline-fairness,
sensitivity, and ablation status, the core/scenario/body-zone/scalability result tables, the
final graph set, and a one-click Export Final Evidence Package button.
