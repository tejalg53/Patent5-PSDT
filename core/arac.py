"""
Sprint 9 - Adaptive Resource Allocation Controller (ARAC).

Dynamically adapts each node's synchronization-related technical
resources - synchronization interval, beacon interval, radio wake-up
interval, transmit power, and actuator trigger-timing offset - based on
the synchronization state assigned by the SCE (core/sce.py).

ARAC closes the control loop described in the patent:

    Wearable Nodes -> DTCE -> PEEE -> PSME -> SCE -> ARAC ->
    Updated Synchronization Parameters -> Wearable Nodes

This controller performs no classification of its own: it never
recomputes PT, PE, PSM, NPSM, or state. It only converts an already-
classified state (plus body zone and mechanical/actuator delay, which are
node properties rather than SCE outputs) into concrete resource settings.

States with less perceptual margin (ELEVATED, IMMEDIATE) receive shorter
synchronization/beacon/wake-up intervals and higher transmit power, so
synchronization quality is protected when it matters most. States with a
comfortable margin (RELAXED, NOMINAL) receive longer intervals and lower
power, reducing communication overhead and energy consumption when the
node does not need tight synchronization.
"""

from dataclasses import dataclass
from typing import Optional
import math

from config.resource_profiles import (
    SYNC_INTERVAL_MS_BY_STATE,
    BEACON_INTERVAL_MS_BY_STATE,
    RADIO_WAKEUP_INTERVAL_MS_BY_STATE,
    TRANSMIT_POWER_LEVEL_BY_STATE,
    TRANSMIT_POWER_PCT_BY_STATE,
    DEFAULT_SYNC_INTERVAL_MS,
    DEFAULT_BEACON_INTERVAL_MS,
    DEFAULT_RADIO_WAKEUP_INTERVAL_MS,
    DEFAULT_TRANSMIT_POWER_LEVEL,
    DEFAULT_TRANSMIT_POWER_PCT,
    DEFAULT_TRIGGER_OFFSET_MS,
    ZONE_SYNC_SCALE,
    DEFAULT_ZONE_SYNC_SCALE,
)
from core.sce import STATE_ORDER


@dataclass(frozen=True)
class ARACResult:
    """Full, human-readable audit trail for one ARAC allocation.

    `status` is "OK" for a normal allocation, or "INVALID_INPUT" when
    safe_allocate() had to reject malformed input without raising. On
    INVALID_INPUT the returned resource fields simply carry over the
    caller-supplied previous_resources (or the documented NOMINAL
    defaults if none were supplied), per Sprint 9 Deliverable 23.
    """

    target_state: Optional[str]
    sync_interval_ms: Optional[float]
    beacon_interval_ms: Optional[float]
    radio_wakeup_interval_ms: Optional[float]
    transmit_power_level: Optional[str]
    transmit_power_pct: Optional[float]
    trigger_timing_offset_ms: Optional[float]
    status: str = "OK"
    error_reason: Optional[str] = None


def _default_resources():
    """The documented conservative (NOMINAL) fallback profile used when
    there is no previous allocation to retain (Sprint 9 Deliverable 23)."""
    return {
        "sync_interval_ms": DEFAULT_SYNC_INTERVAL_MS,
        "beacon_interval_ms": DEFAULT_BEACON_INTERVAL_MS,
        "radio_wakeup_interval_ms": DEFAULT_RADIO_WAKEUP_INTERVAL_MS,
        "transmit_power_level": DEFAULT_TRANSMIT_POWER_LEVEL,
        "transmit_power_pct": DEFAULT_TRANSMIT_POWER_PCT,
        "trigger_timing_offset_ms": DEFAULT_TRIGGER_OFFSET_MS,
    }


class AdaptiveResourceAllocationController:
    """Allocates synchronization-related technical resources per node,
    driven by the node's current SCE-classified synchronization state.
    """

    def _resource_for_state(self, state, zone_scale):
        """Deterministic base resource profile for `state`, with the
        synchronization interval scaled by the node's body-zone factor
        (Sprint 9 Deliverables 3-4-5-7 and 14/17). Raises ValueError for
        an unrecognized state - callers needing fail-safe behavior should
        use safe_allocate() instead of calling this directly."""
        if state not in STATE_ORDER:
            raise ValueError(f"Unrecognized synchronization state: {state!r}")

        return {
            "sync_interval_ms": round(SYNC_INTERVAL_MS_BY_STATE[state] * zone_scale, 2),
            "beacon_interval_ms": BEACON_INTERVAL_MS_BY_STATE[state],
            "radio_wakeup_interval_ms": RADIO_WAKEUP_INTERVAL_MS_BY_STATE[state],
            "transmit_power_level": TRANSMIT_POWER_LEVEL_BY_STATE[state],
            "transmit_power_pct": TRANSMIT_POWER_PCT_BY_STATE[state],
        }

    def _trigger_offset_for(self, mechanical_delay_ms, actuator_driver_delay_ms):
        """Trigger-timing offset compensation (Sprint 9 Deliverable 6).

        The actuator is triggered earlier by the total known mechanical +
        driver delay, so perceived vibration onset remains synchronized
        despite hardware latency. Expressed as a negative number of
        milliseconds (i.e. "fire this many ms earlier").
        """
        total_delay = (mechanical_delay_ms or 0.0) + (actuator_driver_delay_ms or 0.0)
        return -round(total_delay, 2)

    def allocate(self, state, body_zone=None, mechanical_delay_ms=0.0,
                 actuator_driver_delay_ms=0.0):
        """Strict allocation. Raises ValueError on invalid input.

        Parameters
        ----------
        state : str
            The node's current SCE-classified synchronization state.
        body_zone : Optional[str]
            The node's anatomical zone, used to differentiate resource
            allocation across body regions (Deliverables 14/17).
        mechanical_delay_ms, actuator_driver_delay_ms : float
            The node's known hardware delays, used only for trigger-
            timing-offset compensation (Deliverable 6). ARAC does not use
            these to drive sync/beacon/wake-up/power decisions.

        Returns
        -------
        ARACResult
        """
        if state is None:
            raise ValueError("Synchronization state is required.")
        if state not in STATE_ORDER:
            raise ValueError(f"Unrecognized synchronization state: {state!r}")

        zone_scale = ZONE_SYNC_SCALE.get(body_zone, DEFAULT_ZONE_SYNC_SCALE)
        resources = self._resource_for_state(state, zone_scale)
        trigger_offset = self._trigger_offset_for(mechanical_delay_ms, actuator_driver_delay_ms)

        return ARACResult(
            target_state=state,
            sync_interval_ms=resources["sync_interval_ms"],
            beacon_interval_ms=resources["beacon_interval_ms"],
            radio_wakeup_interval_ms=resources["radio_wakeup_interval_ms"],
            transmit_power_level=resources["transmit_power_level"],
            transmit_power_pct=resources["transmit_power_pct"],
            trigger_timing_offset_ms=trigger_offset,
            status="OK",
        )

    def safe_allocate(self, state, battery=None, pt=None, pe=None, psm=None,
                       body_zone=None, mechanical_delay_ms=0.0,
                       actuator_driver_delay_ms=0.0, previous_resources=None):
        """Boundary-safe wrapper around allocate(). Never raises.

        On invalid input - missing/None state, an unrecognized state
        name, missing battery, missing PT, NaN/Infinite numeric inputs -
        this returns an ARACResult with status="INVALID_INPUT" whose
        resource fields simply retain `previous_resources` (a dict with
        the same keys as allocate()'s output) if supplied, or fall back to
        the documented conservative NOMINAL defaults otherwise (Sprint 9
        Deliverable 23). It never fabricates a state-driven allocation
        from malformed input.
        """
        def _fallback(reason):
            base = dict(previous_resources) if previous_resources else _default_resources()
            return ARACResult(
                target_state=state if isinstance(state, str) else None,
                sync_interval_ms=base.get("sync_interval_ms"),
                beacon_interval_ms=base.get("beacon_interval_ms"),
                radio_wakeup_interval_ms=base.get("radio_wakeup_interval_ms"),
                transmit_power_level=base.get("transmit_power_level"),
                transmit_power_pct=base.get("transmit_power_pct"),
                trigger_timing_offset_ms=base.get("trigger_timing_offset_ms"),
                status="INVALID_INPUT",
                error_reason=reason,
            )

        if state is None:
            return _fallback("Missing synchronization state.")
        if state not in STATE_ORDER:
            return _fallback(f"Invalid synchronization state: {state!r}")
        if battery is None:
            return _fallback("Missing battery level.")
        try:
            battery_f = float(battery)
            if math.isnan(battery_f) or math.isinf(battery_f):
                return _fallback("Battery level is NaN/Infinite.")
        except (TypeError, ValueError):
            return _fallback(f"Non-numeric battery level: {battery!r}")
        if pt is None:
            return _fallback("Missing Perceptual Threshold (PT).")
        try:
            pt_f = float(pt)
            if math.isnan(pt_f) or math.isinf(pt_f):
                return _fallback("PT is NaN/Infinite.")
        except (TypeError, ValueError):
            return _fallback(f"Non-numeric PT: {pt!r}")

        for label, value in (("PE", pe), ("PSM", psm)):
            if value is not None:
                try:
                    value_f = float(value)
                    if math.isnan(value_f) or math.isinf(value_f):
                        return _fallback(f"{label} is NaN/Infinite.")
                except (TypeError, ValueError):
                    return _fallback(f"Non-numeric {label}: {value!r}")

        try:
            return self.allocate(
                state=state,
                body_zone=body_zone,
                mechanical_delay_ms=mechanical_delay_ms,
                actuator_driver_delay_ms=actuator_driver_delay_ms,
            )
        except ValueError as exc:
            return _fallback(str(exc))
