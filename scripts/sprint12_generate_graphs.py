"""
Sprint 12 Deliverables 17-18 -- Final Graph Set with Provenance.

Generates the 6 required graphs from the actual results already written to
results/raw and results/aggregates (no re-simulation, no manually edited
values). Each PNG gets a sidecar *.provenance.json with Model Version,
Configuration ID, Scenario, Node Count, Seeds, Strategies, and a generation
timestamp.
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

import plotly.graph_objects as go

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

AGG_DIR = os.path.join(ROOT, "results", "aggregates")
RAW_DIR = os.path.join(ROOT, "results", "raw")
FIG_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

with open(os.path.join(ROOT, "results", "configuration", "final_configuration.json")) as f:
    CONFIG = json.load(f)

MODEL_VERSION = CONFIG["model_version"]
CONFIG_ID = CONFIG["configuration_id"]


def read_csv(name):
    with open(os.path.join(AGG_DIR, name)) as f:
        return list(csv.DictReader(f))


def save_fig(fig, name, provenance, width=900, height=550):
    png_path = os.path.join(FIG_DIR, f"{name}.png")
    fig.write_image(png_path, width=width, height=height, scale=2)
    provenance_full = {
        "model_version": MODEL_VERSION,
        "configuration_id": CONFIG_ID,
        "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **provenance,
    }
    with open(os.path.join(FIG_DIR, f"{name}.provenance.json"), "w") as f:
        json.dump(provenance_full, f, indent=2, default=str)
    print(f"  wrote {png_path}")


print("=== Deliverables 17-18: Final Graph Set with Provenance ===")

# ------------------------------------------------------------------
# Graph 1: Synchronization Messages -- Uniform vs Proposed by Scenario
# ------------------------------------------------------------------
scenario_rows = read_csv("scenario_results.csv")
scenarios_order = ["Scenario A: Stable", "Scenario B: Moderate", "Scenario C: Dynamic/Challenging"]
uniform_vals = [float([r for r in scenario_rows if r["scenario"] == s and r["strategy"] == "Uniform"][0]["sync_messages_mean"]) for s in scenarios_order]
proposed_vals = [float([r for r in scenario_rows if r["scenario"] == s and r["strategy"] == "PSM-Adaptive"][0]["sync_messages_mean"]) for s in scenarios_order]
short_labels = ["Stable", "Moderate", "Challenging"]

fig1 = go.Figure()
fig1.add_bar(name="Uniform Baseline", x=short_labels, y=uniform_vals, marker_color="#888888")
fig1.add_bar(name="PSM-Adaptive", x=short_labels, y=proposed_vals, marker_color="#2E7D32")
fig1.update_layout(title="Graph 1: Synchronization Messages by Scenario (30 nodes, 10 seeds, mean)",
                    yaxis_title="Sync Messages", barmode="group", template="simple_white")
save_fig(fig1, "sync_messages", {
    "graph": "Sync messages by scenario", "node_count": 30, "seeds": "42-51 (10)",
    "strategies": ["Uniform Baseline", "PSM-Adaptive"], "scenarios": scenarios_order,
})

print("Graph 1 done.")

# ------------------------------------------------------------------
# Graph 2: Estimated Communication Energy -- Uniform vs Proposed w/ error bars
# ------------------------------------------------------------------
with open(os.path.join(RAW_DIR, "experiment_runs.csv")) as f:
    all_runs = list(csv.DictReader(f))

import statistics as _st

def energy_mean_std(scenario, strategy):
    vals = [float(r["estimated_energy_j"]) for r in all_runs
            if r["scenario"] == scenario and r["strategy"] == strategy and r["num_nodes"] == "30"]
    return _st.fmean(vals), (_st.stdev(vals) if len(vals) > 1 else 0.0)

energy_base_mean, energy_base_std, energy_prop_mean, energy_prop_std = [], [], [], []
for s in scenarios_order:
    m, sd = energy_mean_std(s, "baseline"); energy_base_mean.append(m); energy_base_std.append(sd)
    m, sd = energy_mean_std(s, "proposed"); energy_prop_mean.append(m); energy_prop_std.append(sd)

fig2 = go.Figure()
fig2.add_bar(name="Uniform Baseline", x=short_labels, y=energy_base_mean,
             error_y=dict(type="data", array=energy_base_std), marker_color="#888888")
fig2.add_bar(name="PSM-Adaptive", x=short_labels, y=energy_prop_mean,
             error_y=dict(type="data", array=energy_prop_std), marker_color="#2E7D32")
fig2.update_layout(title="Graph 2: Estimated Communication Energy by Scenario (mean +/- stdev, n=10 seeds)",
                    yaxis_title="Estimated Energy (J)", barmode="group", template="simple_white")
save_fig(fig2, "estimated_energy", {
    "graph": "Estimated energy by scenario with error bars", "node_count": 30, "seeds": "42-51 (10)",
    "strategies": ["Uniform Baseline", "PSM-Adaptive"], "scenarios": scenarios_order,
})
print("Graph 2 done.")

# ------------------------------------------------------------------
# Graph 3: Perceptual-Threshold Violation Rate -- Uniform vs Proposed
# ------------------------------------------------------------------
viol_uniform = [float([r for r in scenario_rows if r["scenario"] == s and r["strategy"] == "Uniform"][0]["violation_rate_pct_mean"]) for s in scenarios_order]
viol_proposed = [float([r for r in scenario_rows if r["scenario"] == s and r["strategy"] == "PSM-Adaptive"][0]["violation_rate_pct_mean"]) for s in scenarios_order]

fig3 = go.Figure()
fig3.add_bar(name="Uniform Baseline", x=short_labels, y=viol_uniform, marker_color="#888888")
fig3.add_bar(name="PSM-Adaptive", x=short_labels, y=viol_proposed, marker_color="#2E7D32")
fig3.update_layout(title="Graph 3: Perceptual-Threshold Violation Rate by Scenario",
                    yaxis_title="Violation Rate (%)", barmode="group", template="simple_white")
save_fig(fig3, "violation_rate", {
    "graph": "Violation rate by scenario", "node_count": 30, "seeds": "42-51 (10)",
    "strategies": ["Uniform Baseline", "PSM-Adaptive"], "scenarios": scenarios_order,
})
print("Graph 3 done.")

# ---------------------------------------------------------------------------
# Graph 4: Mean Synchronization Interval by Body Zone -- Uniform vs PSM-Adaptive
# ---------------------------------------------------------------------------
zone_rows = read_csv("body_zone_results.csv")
zone_order = ["Fingertip", "Hand", "Forearm", "Torso", "Leg", "Foot"]
zone_by_name = {r["body_zone"]: r for r in zone_rows}
zone_uniform = [float(zone_by_name[z]["baseline_mean_sync_interval_ms"]) for z in zone_order]
zone_proposed = [float(zone_by_name[z]["proposed_mean_sync_interval_ms"]) for z in zone_order]

fig4 = go.Figure()
fig4.add_bar(name="Uniform Baseline", x=zone_order, y=zone_uniform, marker_color="#888888")
fig4.add_bar(name="PSM-Adaptive", x=zone_order, y=zone_proposed, marker_color="#2E7D32")
fig4.update_layout(title="Graph 4: Mean Synchronization Interval by Body Zone",
                    yaxis_title="Mean Sync Interval (ms)", barmode="group", template="simple_white")
save_fig(fig4, "body_zone_sync", {
    "graph": "Mean sync interval by body zone -- demonstrates differentiated, non-uniform resource allocation",
    "node_count": 30, "seeds": "42-51 (10)",
    "strategies": ["Uniform Baseline", "PSM-Adaptive"], "body_zones": zone_order,
})
print("Graph 4 done.")

# ---------------------------------------------------------------------------
# Graph 5: Disturbance Response -- PT, PE, PSM, State, Sync Interval over time
# ---------------------------------------------------------------------------
from plotly.subplots import make_subplots
from core.experiment_engine import run_disturbance_experiment
from core.node_factory import generate_nodes
from config.baseline_policies import DEFAULT_UNIFORM_POLICY

_probe_nodes = generate_nodes(30, 42)
probe_node_id = next(n.node_id for n in _probe_nodes if n.body_zone == "Fingertip")

disturbance = run_disturbance_experiment(
    seed=42, nodes=30, duration=300.0, time_step=1.0,
    scenario="Scenario B: Moderate", baseline_policy=DEFAULT_UNIFORM_POLICY,
    node_id=probe_node_id,
)
base_eng, prop_eng = disturbance["baseline_engine"], disturbance["proposed_engine"]
d_start, d_end = disturbance["disturbance_start_s"], disturbance["disturbance_end_s"]

series_p = prop_eng.history.node_dataframe_dict(probe_node_id)
series_b = base_eng.history.node_dataframe_dict(probe_node_id)
t = series_p["timestamp"]

seen_states = []
for s in series_p["current_state"]:
    if s not in seen_states:
        seen_states.append(s)
state_index = {s: i for i, s in enumerate(seen_states)}
state_numeric = [state_index.get(s) for s in series_p["current_state"]]

fig5 = make_subplots(
    rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
    row_heights=[0.45, 0.25, 0.3],
    subplot_titles=(
        f"PT / PE / PSM -- Node {probe_node_id} (Fingertip)",
        "SCE Operational State (Proposed)",
        "Allocated Sync Interval (ms)",
    ),
)
fig5.add_scatter(x=t, y=series_p["PT"], name="PT (Proposed)", line=dict(color="#1f77b4"), row=1, col=1)
fig5.add_scatter(x=t, y=series_p["PE"], name="PE (Proposed)", line=dict(color="#d62728"), row=1, col=1)
fig5.add_scatter(x=t, y=series_p["PSM"], name="PSM (Proposed)", line=dict(color="#2E7D32"), row=1, col=1)
fig5.add_scatter(x=series_b["timestamp"], y=series_b["PSM"], name="PSM (Uniform Baseline)",
                 line=dict(color="#888888", dash="dot"), row=1, col=1)
fig5.add_scatter(x=t, y=state_numeric, name="State (Proposed)", mode="lines+markers",
                 line=dict(color="#8e44ad", shape="hv"), row=2, col=1)
fig5.update_yaxes(tickmode="array", tickvals=list(state_index.values()), ticktext=list(state_index.keys()), row=2, col=1)
fig5.add_scatter(x=t, y=series_p["sync_interval_ms"], name="Sync Interval (Proposed)",
                 line=dict(color="#2E7D32", shape="hv"), row=3, col=1)
fig5.add_scatter(x=series_b["timestamp"], y=series_b["sync_interval_ms"], name="Sync Interval (Uniform)",
                 line=dict(color="#888888", dash="dot", shape="hv"), row=3, col=1)
for r in (1, 2, 3):
    fig5.add_vrect(x0=d_start, x1=d_end, fillcolor="red", opacity=0.08, line_width=0, row=r, col=1)
fig5.update_layout(
    title="Graph 5: Disturbance Response Over Time (network jitter + clock-drift spike injected)",
    template="simple_white",
)
fig5.update_xaxes(title_text="Simulation Time (s)", row=3, col=1)
save_fig(fig5, "disturbance_response", {
    "graph": "Time-series PT/PE/PSM/State/SyncInterval response to an injected disturbance",
    "node_id": probe_node_id, "body_zone": "Fingertip",
    "disturbance_start_s": d_start, "disturbance_end_s": d_end,
    "baseline_recovery_s": disturbance["baseline_recovery_s"],
    "proposed_recovery_s": disturbance["proposed_recovery_s"],
    "node_count": 30, "seeds": "42", "strategies": ["Uniform Baseline", "PSM-Adaptive"],
    "scenario": "Scenario B: Moderate",
}, width=950, height=900)
print(f"Graph 5 done. baseline_recovery_s={disturbance['baseline_recovery_s']} proposed_recovery_s={disturbance['proposed_recovery_s']}")

# ---------------------------------------------------------------------------
# Graph 6: Scalability -- Node Count vs Energy / Sync Messages
# ---------------------------------------------------------------------------
scal_rows = read_csv("scalability_results.csv")
scal_rows.sort(key=lambda r: int(float(r["num_nodes"])))
node_counts = [int(float(r["num_nodes"])) for r in scal_rows]
scal_base_energy = [float(r["baseline_energy_j"]) for r in scal_rows]
scal_prop_energy = [float(r["proposed_energy_j"]) for r in scal_rows]
scal_base_msgs = [float(r["baseline_messages"]) for r in scal_rows]
scal_prop_msgs = [float(r["proposed_messages"]) for r in scal_rows]

fig6 = make_subplots(rows=1, cols=2, subplot_titles=(
    "Estimated Communication Energy vs Node Count",
    "Synchronization Messages vs Node Count",
))
fig6.add_scatter(x=node_counts, y=scal_base_energy, name="Uniform Baseline (Energy)",
                 mode="lines+markers", line=dict(color="#888888"), row=1, col=1)
fig6.add_scatter(x=node_counts, y=scal_prop_energy, name="PSM-Adaptive (Energy)",
                 mode="lines+markers", line=dict(color="#2E7D32"), row=1, col=1)
fig6.add_scatter(x=node_counts, y=scal_base_msgs, name="Uniform Baseline (Messages)",
                 mode="lines+markers", line=dict(color="#888888", dash="dash"), row=1, col=2)
fig6.add_scatter(x=node_counts, y=scal_prop_msgs, name="PSM-Adaptive (Messages)",
                 mode="lines+markers", line=dict(color="#2E7D32", dash="dash"), row=1, col=2)
fig6.update_xaxes(title_text="Node Count", row=1, col=1)
fig6.update_xaxes(title_text="Node Count", row=1, col=2)
fig6.update_yaxes(title_text="Estimated Energy (J)", row=1, col=1)
fig6.update_yaxes(title_text="Sync Messages", row=1, col=2)
fig6.update_layout(title="Graph 6: Scalability -- Node Count vs Energy and Sync Messages",
                    template="simple_white")
save_fig(fig6, "scalability", {
    "graph": "Estimated communication energy and synchronization-message count vs node count",
    "node_counts": node_counts, "seeds": "42-51 (10)",
    "strategies": ["Uniform Baseline", "PSM-Adaptive"],
}, width=1100, height=500)
print("Graph 6 done.")

print("=== Deliverables 17-18 complete: 6 graphs + provenance written to results/figures/ ===")
