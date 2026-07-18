"""
Sprint 3 - Node Factory.

Generates a reproducible set of virtual HapticNode instances distributed
across the six anatomical zones. Reproducibility is achieved with a
seeded random.Random instance: the same (num_nodes, seed) pair always
yields identical node parameters. This module contains simulation
infrastructure only - no PSM-based control logic lives here.
"""

import random

from .constants import (
    ZONE_ORDER,
    ZONE_WEIGHTS,
    ZONE_ACTUATOR,
    ACTUATOR_FREQUENCY_RANGE,
    BATTERY_RANGE,
    CLOCK_DRIFT_RANGE,
    NETWORK_DELAY_RANGE,
    ACTUATOR_DRIVER_DELAY_RANGE,
    MECHANICAL_DELAY_RANGE,
    SYNC_INTERVAL_RANGE,
)
from .node import HapticNode


def compute_zone_distribution(num_nodes):
    """
    Deterministically split num_nodes across ZONE_ORDER proportionally to
    ZONE_WEIGHTS, using the largest-remainder method so the total always
    equals num_nodes exactly (ties broken by ZONE_ORDER position).
    """
    total_weight = sum(ZONE_WEIGHTS.values())
    raw = {zone: num_nodes * ZONE_WEIGHTS[zone] / total_weight for zone in ZONE_ORDER}
    floors = {zone: int(raw[zone]) for zone in ZONE_ORDER}
    remainder = num_nodes - sum(floors.values())

    ranked = sorted(
        ZONE_ORDER,
        key=lambda z: (-(raw[z] - floors[z]), ZONE_ORDER.index(z)),
    )
    for zone in ranked[:remainder]:
        floors[zone] += 1

    return floors


def generate_nodes(num_nodes, seed):
    """
    Generate `num_nodes` HapticNode instances using the given seed.
    Same (num_nodes, seed) => identical output every time.
    """
    if num_nodes not in (10, 20, 30, 40, 50):
        raise ValueError("num_nodes must be one of 10, 20, 30, 40, 50")

    rng = random.Random(seed)
    distribution = compute_zone_distribution(num_nodes)

    nodes = []
    node_index = 1
    for zone in ZONE_ORDER:
        actuator = ZONE_ACTUATOR[zone]
        freq_range = ACTUATOR_FREQUENCY_RANGE[actuator]
        for _ in range(distribution[zone]):
            node = HapticNode(
                node_id=f"HN-{node_index:03d}",
                body_zone=zone,
                actuator_type=actuator,
                vibration_frequency=round(rng.uniform(*freq_range), 1),
                battery_level=round(rng.uniform(*BATTERY_RANGE), 1),
                clock_drift=round(rng.uniform(*CLOCK_DRIFT_RANGE), 2),
                network_delay=round(rng.uniform(*NETWORK_DELAY_RANGE), 2),
                actuator_driver_delay=round(rng.uniform(*ACTUATOR_DRIVER_DELAY_RANGE), 2),
                mechanical_startup_delay=round(rng.uniform(*MECHANICAL_DELAY_RANGE), 2),
                sync_interval=round(rng.uniform(*SYNC_INTERVAL_RANGE), 2),
            )
            nodes.append(node)
            node_index += 1

    return nodes
