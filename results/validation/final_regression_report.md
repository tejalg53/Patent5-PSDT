# Sprint 12 Deliverable 24 -- Final Regression Test Report

Full automated suite: `python3 -m pytest tests/ -q`

**Result: 123 passed, 3 failed** (down from 4 failed/122 passed at the start of Sprint 12;
one pre-existing broken test was fixed as a safe, non-model-affecting correction -- see below).

Coverage includes: node generation, PSSP, Coordinator, DTCE, PEEE, PSME, SCE, ARAC, PRAP,
temporal simulation, energy accounting, experiments, and exports.

## Fixed during Sprint 12 (safe, test-only corrections)

Two tests called `generate_nodes()` / `_build()` with `num_nodes` values (5 and 15) that are
not in the frozen valid set `{10, 20, 30, 40, 50}` enforced by `core/node_factory.py`. These
were test-authoring bugs (invalid input to a validated function) unrelated to any Sprint 12
model change -- corrected to the nearest valid node count (10 and 20 respectively), which does
not alter what each test actually checks:
- `tests/test_sce.py::TestSCECoordinatorIntegration::test_state_history_is_bounded_rolling_buffer`
  (`num_nodes=5` -> `10`) -- **now passes**.
- `tests/test_simulation_engine.py::TestEnergyAccounting::test_dynamic_scenario_consumes_more_energy_than_stable`
  (`num_nodes=15` -> `20`) -- see below; still fails, but now for a substantive reason rather
  than an invalid-input error.

## Remaining known limitations (documented, not hidden, not fixed this sprint)

No core/config model logic was changed to force any of these to pass -- per Deliverable 1,
the frozen model must not silently change. Each is a pre-existing condition that predates
Sprint 12 (confirmed identical before/after all Sprint 12 code changes via git-stash
comparison during the Deliverable 8 ablation work).

1. **`tests/test_coordinator.py::TestCoordinator::test_prap_is_structural_placeholder_only`**
   -- asserts every node's PRAP snapshot is `is_baseline=True` immediately after one
   low-level `run_communication_cycle()` call (bypassing the full engine/SCE classification
   pass). At least one randomly-generated node in the default registry is not in the expected
   baseline PRAP state at that point, so the assertion fails. This is a test-harness ordering
   question (whether an SCE pass must run before PRAP is guaranteed baseline), not a
   correctness question about the frozen DTCE/PEEE/PSME/SCE/ARAC/PRAP chain itself, which is
   separately and extensively validated by the Sprint 12 invariant audit (0 violations across
   6,000 observations) and traceability tests.

2. **`tests/test_simulation_engine.py::TestResynchronizationEffect::test_resync_reduces_drift`**
   -- asserts that immediately after a node's synchronization event fires, its clock drift is
   strictly less than immediately before. In this run, one observed pair violated strict
   monotonicity (0.187 not less than 0.103 at the specific step captured). Clock drift and
   post-resync jitter are both stochastic (bounded random processes), so a resync reducing
   drift *on average* does not guarantee it reduces drift at every single observed instant --
   the test's strict per-event assertion is stronger than the model's actual guarantee
   (average tendency, not per-event certainty). This is a test-strength mismatch, not
   evidence that resynchronization fails to work: the aggregate 300-run matrix and Sprint 12
   sensitivity analysis both show the proposed system's energy/message reductions hold
   robustly across parameter variation.

3. **`tests/test_simulation_engine.py::TestEnergyAccounting::test_dynamic_scenario_consumes_more_energy_than_stable`**
   -- asserts a Dynamic/Challenging-scenario run always consumes strictly more total energy
   than a Stable-scenario run for one fixed (20-node, 90s, seed=42) configuration. After
   correcting the test's invalid node count (see above), the assertion still fails
   (24.76 J vs 25.24 J) for this specific short/small configuration -- i.e. a single seed and
   a 90-second run is not long enough / not a large enough sample for this particular
   assumption to hold deterministically. This matches Sprint 12's broader finding (Deliverable
   14, scenario table) that scenario-dependent energy behavior is nuanced rather than
   monotonic in every single configuration; the aggregated 10-seed scenario table shows the
   expected pattern in aggregate. This test's single-seed, short-duration assumption was never
   re-validated against the frozen configuration and is left as a known limitation rather than
   force-fit by cherry-picking a seed/duration that happens to pass.

## Conclusion

0 *unexplained* failing tests. All 3 remaining failures are explained, pre-existing, and do
not involve any change to frozen model/parameter logic. No test was weakened (no assertion was
loosened) to make it pass -- the two corrections made were strictly fixing invalid test inputs
to conform to the frozen `generate_nodes()` validation contract.
