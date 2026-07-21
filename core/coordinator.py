"""
Sprint 4 - Central Synchronization Coordinator.
Sprint 5 - adds the DTCE pass (Dynamic Perceptual Threshold PTz(t)).
Sprint 6 - adds the PEEE pass (Estimated Perceived Error PEz(t)).
Sprint 7 - adds the PSME pass (Perceptual Synchronization Margin PSMz(t))
           and seeds a rolling PT/PE/PSM history buffer per node for
           Sprint 8+ (hysteresis/dwell-time, trend animation, graphs).

Responsible for:
- registering wearable nodes into a registry indexed by Node ID and zone
- requesting/receiving node synchronization status (PSSP)
- validating incoming status packets
- storing the latest status of every node
- maintaining packet/event counters
- preparing (placeholder, non-adaptive) resource-allocation commands (PRAP)
- logging synchronization communication
- running DTCE (PTz(t)), PEEE (PEz(t)) and PSME (PSMz(t)) for every registered node

The SCE / ARAC engines are represented here only as named placeholders
in the processing pipeline. They are implemented in later sprints (8-9)
and must not be faked in this sprint.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .packets import PSSP, PRAP
from .dtce import DynamicThresholdCharacterizationEngine, DTCEAudit
from .peee import PerceivedErrorEstimationEngine, PEEEAudit
from .psme import PerceptualSynchronizationMarginEngine, PSMResult
from .error_profiles import DEFAULT_PE_MODEL, DEFAULT_WEIGHTS, DEFAULT_NETWORK_CONDITION

PIPELINE_STAGES = [
    ("DTCE", "Sprint 5"),
    ("PEEE", "Sprint 6"),
    ("PSME", "Sprint 7"),
    ("SCE", "Sprint 8"),
    ("ARAC", "Sprint 9"),
]


@dataclass
class CommunicationLogEntry:
    timestamp: float
    node_id: str
    event: str
    packet_id: Optional[str] = None


class CentralSynchronizationCoordinator:
    """A single digital twin's coordinator instance."""

    def __init__(self, seed=None):
        self.registry: Dict[str, object] = {}
        self.zone_index: Dict[str, List[str]] = {}
        self.status_repository: Dict[str, PSSP] = {}
        self.packet_history: Dict[str, PSSP] = {}
        self.latest_praps: Dict[str, PRAP] = {}
        self.log: List[CommunicationLogEntry] = []

        self.dtce = DynamicThresholdCharacterizationEngine()
        self.dtce_audit: Dict[str, DTCEAudit] = {}
        self.perceptual_context = {
            "calibration_profile": "Standard",
            "custom_calibration_factor": None,
            "motion_state": "Stationary",
            "environment_state": "Normal",
        }

        self.peee = PerceivedErrorEstimationEngine(seed=seed)
        self.peee_audit: Dict[str, PEEEAudit] = {}
        self.error_model_context = {
            "model": DEFAULT_PE_MODEL,
            "weights": dict(DEFAULT_WEIGHTS),
            "network_condition": DEFAULT_NETWORK_CONDITION,
        }
        self.psme = PerceptualSynchronizationMarginEngine()
        self.psme_audit: Dict[str, PSMResult] = {}
        self._last_timestamp = 0.0

        self.packets_generated = 0
        self.packets_received = 0
        self.valid_packets = 0
        self.rejected_packets = 0
        self.prap_generated = 0

        self._seen_packet_ids = set()
        self._packet_counter = 0
        self.cycle_count = 0

    def register_nodes(self, nodes):
        self.registry = {}
        self.zone_index = {}
        for node in nodes:
            self.registry[node.node_id] = node
            self.zone_index.setdefault(node.body_zone, []).append(node.node_id)

    @property
    def registered_node_count(self):
        return len(self.registry)

    def _next_packet_id(self, prefix):
        self._packet_counter += 1
        return f"{prefix}-{self._packet_counter:06d}"

    def validate_pssp(self, pssp: PSSP):
        if pssp.node_id not in self.registry:
            return False, "Unknown node ID"

        node = self.registry[pssp.node_id]
        if pssp.body_zone != node.body_zone:
            return False, "Body zone mismatch"

        delay_fields = (
            ("clock drift", pssp.clock_drift_ms),
            ("network delay", pssp.network_delay_ms),
            ("actuator driver delay", pssp.actuator_driver_delay_ms),
            ("mechanical startup delay", pssp.mechanical_startup_delay_ms),
        )
        for name, value in delay_fields:
            if value is None or value < 0:
                return False, f"Negative or missing {name}"

        if pssp.battery_percent is None or not (0 <= pssp.battery_percent <= 100):
            return False, "Battery out of range"

        if pssp.simulation_timestamp is None or pssp.simulation_timestamp < 0:
            return False, "Invalid timestamp"

        required = [pssp.packet_id, pssp.node_id, pssp.body_zone, pssp.current_state]
        if any(value is None or value == "" for value in required):
            return False, "Missing required field"

        if pssp.packet_id in self._seen_packet_ids:
            return False, "Duplicate packet ID"

        return True, None

    def run_communication_cycle(self, simulation_timestamp=0.0):
        self.cycle_count += 1
        entries = []

        elapsed = max(0.0, simulation_timestamp - self._last_timestamp)
        self._last_timestamp = simulation_timestamp
        self.advance_timing_state(elapsed)

        for node_id, node in self.registry.items():
            packet_id = self._next_packet_id("PSSP")
            pssp = node.to_pssp(packet_id=packet_id, simulation_timestamp=simulation_timestamp)

            self.packets_generated += 1
            self.packets_received += 1
            self.packet_history[pssp.packet_id] = pssp

            is_valid, reason = self.validate_pssp(pssp)
            if is_valid:
                self._seen_packet_ids.add(pssp.packet_id)
                self.valid_packets += 1
                self.status_repository[node_id] = pssp
                event = "PSSP received"
            else:
                self.rejected_packets += 1
                event = f"PSSP rejected: {reason}"

            entry = CommunicationLogEntry(
                timestamp=simulation_timestamp,
                node_id=node_id,
                event=event,
                packet_id=pssp.packet_id,
            )
            self.log.append(entry)
            entries.append(entry)

        self._generate_baseline_praps(simulation_timestamp)
        self.run_dtce_pass()
        self.run_peee_pass()
        self.run_psme_pass()

        return entries

    def _generate_baseline_praps(self, simulation_timestamp):
        for node_id in self.registry:
            packet_id = self._next_packet_id("PRAP")
            prap = PRAP(
                packet_id=packet_id,
                target_node_id=node_id,
                body_zone=self.registry[node_id].body_zone,
                simulation_timestamp=simulation_timestamp,
            )
            self.latest_praps[node_id] = prap
            self.prap_generated += 1

    def set_perceptual_context(self, calibration_profile=None, custom_calibration_factor=None,
                                motion_state=None, environment_state=None):
        """Update the shared Perceptual Context used by DTCE for every node."""
        if calibration_profile is not None:
            self.perceptual_context["calibration_profile"] = calibration_profile
        if custom_calibration_factor is not None:
            self.perceptual_context["custom_calibration_factor"] = custom_calibration_factor
        if motion_state is not None:
            self.perceptual_context["motion_state"] = motion_state
        if environment_state is not None:
            self.perceptual_context["environment_state"] = environment_state

    def run_dtce_pass(self):
        """Run the Dynamic Threshold Characterization Engine for every
        registered node using the current Perceptual Context. Stores a full
        audit trail per node and writes PTz(t) back onto the node itself.
        Returns the dtce_audit dict (node_id -> DTCEAudit).
        """
        ctx = self.perceptual_context
        for node_id, node in self.registry.items():
            audit = self.dtce.compute_threshold(
                body_zone=node.body_zone,
                frequency_hz=node.vibration_frequency,
                actuator_type=node.actuator_type,
                calibration_profile=ctx["calibration_profile"],
                custom_calibration_factor=ctx["custom_calibration_factor"],
                motion_state=ctx["motion_state"],
                environment_state=ctx["environment_state"],
            )
            self.dtce_audit[node_id] = audit
            node.perceptual_threshold = audit.dynamic_pt_ms
        self.run_psme_pass()
        return self.dtce_audit

    def set_error_model_context(self, model=None, weights=None, network_condition=None):
        """Update the shared Error Model context used by PEEE for every node."""
        if model is not None:
            self.error_model_context["model"] = model
        if weights is not None:
            self.error_model_context["weights"] = weights
        if network_condition is not None:
            self.error_model_context["network_condition"] = network_condition

    def run_peee_pass(self):
        """Run the Perceived Error Estimation Engine for every registered
        node using the current Error Model context. Stores a full audit
        trail per node and writes PEz(t) back onto the node itself.
        Returns the peee_audit dict (node_id -> PEEEAudit).
        """
        ctx = self.error_model_context
        for node_id, node in self.registry.items():
            cd = self.peee.resolve_clock_drift_ms(node.clock_drift)
            nd = self.peee.resolve_network_residual_ms(node.network_delay, ctx["network_condition"])
            ad = self.peee.resolve_actuator_driver_delay_ms(node.actuator_driver_delay, node.actuator_type)
            md = self.peee.resolve_mechanical_startup_delay_ms(node.mechanical_startup_delay, node.actuator_type)

            audit = self.peee.compute_error(
                clock_drift_ms=cd,
                network_residual_ms=nd,
                actuator_driver_delay_ms=ad,
                mechanical_startup_delay_ms=md,
                model=ctx["model"],
                weights=ctx["weights"],
                node_id=node_id,
                body_zone=node.body_zone,
            )
            self.peee_audit[node_id] = audit
            node.perceived_error = audit.perceived_error_ms
        self.run_psme_pass()
        return self.peee_audit

    def run_psme_pass(self):
        """Run the Perceptual Synchronization Margin Engine for every
        registered node that already has both a Dynamic Perceptual
        Threshold PTz(t) (from DTCE) and an Estimated Perceived Error
        PEz(t) (from PEEE). Stores a full audit trail per node and writes
        PSM/NPSM/Threshold Utilization/Margin Sign back onto the node
        itself. Nodes missing PT or PE are left uncomputed (None) rather
        than faked.

        Uses the PSME's boundary-safe entry point (safe_compute_margin)
        so a single malformed node (PT<=0, NaN/Infinity, non-numeric,
        negative PE, etc.) can never raise out of a simulation cycle and
        take the whole Coordinator down with it. An invalid result is
        stored with status="INVALID_INPUT" and the event is logged to
        the communication log; that node's PT/PE are left untouched and
        its previously computed PSM/NPSM/TU/Margin Sign are not reset to
        fabricated values. Returns the psme_audit dict (node_id -> PSMResult).

        Also appends a (step, timestamp, PT, PE, PSM) sample to each valid
        node's rolling history buffer (HapticNode.record_history_point),
        bounded to MAX_HISTORY_LENGTH entries, for use by later sprints.
        """
        for node_id, node in self.registry.items():
            if node.perceptual_threshold is None or node.perceived_error is None:
                continue
            result = self.psme.safe_compute_margin(
                pt_ms=node.perceptual_threshold,
                pe_ms=node.perceived_error,
                node_id=node_id,
            )
            self.psme_audit[node_id] = result

            if result.status == "INVALID_INPUT":
                self.log.append(
                    CommunicationLogEntry(
                        timestamp=self._last_timestamp,
                        node_id=node_id,
                        event=f"PSME rejected invalid input: {result.error_reason}",
                        packet_id=None,
                    )
                )
                continue

            node.psm = result.psm_ms
            node.normalized_psm = result.normalized_psm
            node.threshold_utilization_pct = result.threshold_utilization_pct
            node.margin_sign = result.margin_sign
            node.record_history_point(
                step=self.cycle_count,
                timestamp=self._last_timestamp,
                pt=node.perceptual_threshold,
                pe=node.perceived_error,
                psm=node.psm,
            )
        return self.psme_audit

    def advance_timing_state(self, elapsed_seconds):
        """Advance every node's raw simulated timing measurements by
        elapsed_seconds (infrastructure for Sprint 10's live time
        evolution). Uses the coordinator's current network condition."""
        network_condition = self.error_model_context["network_condition"]
        for node in self.registry.values():
            self.peee.update_timing_state(node, elapsed_seconds, network_condition=network_condition)

    def get_packet_counts(self):
        return {
            "generated": self.packets_generated,
            "received": self.packets_received,
            "valid": self.valid_packets,
            "rejected": self.rejected_packets,
        }
