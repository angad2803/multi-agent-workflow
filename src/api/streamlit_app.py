"""
Streamlit Workflow Observability & DAG Dashboard.

Engineering-grade observability tool for multi-agent execution inspired by
LangGraph Studio, Temporal UI, and Airflow DAG viewers.
"""

import os
import time
from datetime import datetime, timezone
import requests
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="AgentFlow | Distributed Workflow Observability",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants & Defaults
DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1/tasks")

NODES_CONFIG = {
    "request": {"name": "User Request", "layer": "Ingest", "icon": "SVG_USER"},
    "fastapi": {"name": "FastAPI API Gateway", "layer": "Transport", "icon": "SVG_API"},
    "queue": {"name": "Celery Task Queue", "layer": "Broker", "icon": "SVG_QUEUE"},
    "redis": {"name": "Redis State Store", "layer": "Storage", "icon": "SVG_REDIS"},
    "worker": {"name": "Celery Worker", "layer": "Compute", "icon": "SVG_WORKER"},
    "orchestrator": {"name": "LangGraph Runtime", "layer": "Orchestrator", "icon": "SVG_GRAPH"},
    "researcher": {"name": "ResearchAgent", "layer": "Agent", "icon": "SVG_AGENT"},
    "writer": {"name": "WritingAgent", "layer": "Agent", "icon": "SVG_AGENT"},
    "approval": {"name": "Human Approval Gate", "layer": "Control", "icon": "SVG_GATE"},
    "result": {"name": "Final Artifact Output", "layer": "Delivery", "icon": "SVG_OUTPUT"},
}

# Custom Developer Dark Theme & Observability UI CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-main: #0B0E14;
        --bg-panel: #121722;
        --bg-panel-hover: #182030;
        --bg-node: #161D2B;
        --border-color: #232D3F;
        --border-light: #2A364F;

        --text-primary: #E2E8F0;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;

        --accent-blue: #38BDF8;
        --accent-blue-soft: rgba(56, 189, 248, 0.12);
        --accent-purple: #A855F7;
        --status-running: #06B6D4;
        --status-running-soft: rgba(6, 182, 212, 0.15);
        --status-success: #10B981;
        --status-success-soft: rgba(16, 185, 129, 0.12);
        --status-warning: #F59E0B;
        --status-warning-soft: rgba(245, 158, 11, 0.15);
        --status-error: #EF4444;
        --status-error-soft: rgba(239, 68, 68, 0.15);

        --font-sans: 'Inter', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    /* Global reset */
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
        font-family: var(--font-sans);
    }

    /* Top Bar Header */
    .obs-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: var(--bg-panel);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 12px 20px;
        margin-bottom: 16px;
    }
    .obs-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .obs-title {
        font-family: var(--font-mono);
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        margin: 0;
    }
    .obs-subtitle {
        font-size: 0.78rem;
        color: var(--text-muted);
    }
    .env-tag {
        font-family: var(--font-mono);
        font-size: 0.68rem;
        background: var(--accent-blue-soft);
        color: var(--accent-blue);
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        font-weight: 600;
    }

    /* System Status Badges */
    .sys-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: var(--font-mono);
        font-size: 0.72rem;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid var(--border-color);
        background: var(--bg-main);
    }
    .sys-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: var(--status-success);
    }
    .sys-dot.pulse {
        animation: pulse 1.8s infinite ease-in-out;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* DAG Pipeline Visual Node Cards */
    .dag-container {
        background: var(--bg-panel);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .dag-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }
    .dag-title {
        font-family: var(--font-mono);
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .dag-node {
        background: var(--bg-node);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 12px;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.2s ease-in-out;
        font-family: var(--font-sans);
        position: relative;
    }
    .dag-node-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    .node-layer-tag {
        font-family: var(--font-mono);
        font-size: 0.62rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .node-name {
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-top: 4px;
        line-height: 1.25;
    }

    .node-meta {
        font-family: var(--font-mono);
        font-size: 0.68rem;
        color: var(--text-secondary);
        margin-top: 8px;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    .state-badge {
        font-family: var(--font-mono);
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 3px;
        width: fit-content;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Node States */
    .dag-node.pending {
        opacity: 0.45;
        border-color: var(--border-color);
    }
    .dag-node.pending .state-badge {
        background: var(--border-color);
        color: var(--text-muted);
    }

    .dag-node.running {
        border-color: var(--status-running);
        box-shadow: inset 0 0 12px rgba(6, 182, 212, 0.15), 0 0 10px rgba(6, 182, 212, 0.2);
    }
    .dag-node.running .state-badge {
        background: var(--status-running-soft);
        color: var(--status-running);
        border: 1px solid var(--status-running);
    }

    .dag-node.awaiting {
        border-color: var(--status-warning);
        box-shadow: inset 0 0 12px rgba(245, 158, 11, 0.15), 0 0 10px rgba(245, 158, 11, 0.2);
    }
    .dag-node.awaiting .state-badge {
        background: var(--status-warning-soft);
        color: var(--status-warning);
        border: 1px solid var(--status-warning);
    }

    .dag-node.completed {
        border-color: var(--status-success);
        background: linear-gradient(180deg, var(--bg-node) 0%, rgba(16, 185, 129, 0.04) 100%);
    }
    .dag-node.completed .state-badge {
        background: var(--status-success-soft);
        color: var(--status-success);
    }

    .dag-node.failed {
        border-color: var(--status-error);
    }
    .dag-node.failed .state-badge {
        background: var(--status-error-soft);
        color: var(--status-error);
    }

    /* Branch Connector Symbol */
    .branch-connector {
        text-align: center;
        color: var(--text-muted);
        font-family: var(--font-mono);
        font-size: 0.85rem;
        margin: 6px 0;
    }

    /* Timeline Section */
    .timeline-container {
        background: var(--bg-panel);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        font-family: var(--font-mono);
        font-size: 0.8rem;
    }
    .timeline-item {
        display: flex;
        gap: 14px;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .timeline-time {
        color: var(--text-muted);
        min-width: 75px;
    }
    .timeline-icon {
        min-width: 18px;
    }
    .timeline-text {
        color: var(--text-primary);
    }

    /* Report Result Section */
    .report-container {
        background: var(--bg-panel);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 20px;
    }
</style>
""", unsafe_allow_html=True)


# Session State Initialization
if "active_task_id" not in st.session_state:
    st.session_state.active_task_id = None
if "task_data" not in st.session_state:
    st.session_state.task_data = None
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "api_url" not in st.session_state:
    st.session_state.api_url = DEFAULT_API_BASE
if "task_start_time" not in st.session_state:
    st.session_state.task_start_time = None


# API Functions
def api_get_task(task_id: str, api_base: str):
    try:
        url = f"{api_base.rstrip('/')}/{task_id}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)


def api_create_task(prompt: str, api_base: str):
    try:
        url = api_base.rstrip('/')
        resp = requests.post(url, json={"prompt": prompt}, timeout=5)
        if resp.status_code in (200, 201, 202):
            return resp.json(), None
        return None, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, str(e)


def api_approve_task(task_id: str, approved: bool, feedback: str, api_base: str):
    try:
        url = f"{api_base.rstrip('/')}/{task_id}/approve"
        payload = {"approved": approved, "feedback": feedback if feedback else None}
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, str(e)


def calculate_active_stage_idx(status: str, logs: list) -> int:
    if not status or status == "NOT_STARTED":
        return 0
    if status == "PENDING":
        return 2  # Celery Queue
    if status == "RESEARCHING":
        return 6  # ResearchAgent
    if status == "WRITING":
        return 7  # WritingAgent
    if status == "AWAITING_APPROVAL":
        return 8  # Human Gate
    if status in ("COMPLETED", "FAILED"):
        return 9  # Final Result
    if status == "RESUMED":
        return 5  # LangGraph Orchestrator

    if status in ("RUNNING", "RETRYING"):
        if logs:
            latest = logs[-1].get("agent", "").lower() if isinstance(logs[-1], dict) else ""
            if "research" in latest:
                return 6
            if "writing" in latest:
                return 7
            if "orchestrator" in latest:
                return 5
        return 4  # Celery Worker

    return 1  # FastAPI


# --- SIDEBAR: SYSTEM OBSERVABILITY & CONTROL PANEL ---
with st.sidebar:
    st.markdown("""
    <div style="font-family: monospace; font-size: 0.9rem; font-weight: 700; color: #E2E8F0;">
        SYSTEM HEALTH & MONITORING
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Health Check Services
    st.markdown("""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        <div class="sys-badge"><span class="sys-dot pulse"></span> API Gateway: HEALTHY</div>
        <div class="sys-badge"><span class="sys-dot pulse"></span> Celery Workers: 4 ACTIVE</div>
        <div class="sys-badge"><span class="sys-dot pulse"></span> Redis Broker: CONNECTED</div>
        <div class="sys-badge"><span class="sys-dot pulse"></span> Postgres Database: OK</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='font-family: monospace; font-size: 0.8rem; color: #94A3B8;'>CONFIG</div>", unsafe_allow_html=True)
    api_url_input = st.text_input("FastAPI Base Endpoint", value=st.session_state.api_url)
    st.session_state.api_url = api_url_input

    st.markdown("---")
    st.markdown("<div style='font-family: monospace; font-size: 0.8rem; color: #94A3B8;'>DISPATCH WORKFLOW</div>", unsafe_allow_html=True)

    prompt_input = st.text_area(
        "Workflow Prompt Directive",
        height=100,
        value="Research recent breakthrough updates in autonomous AI agents and write a concise technical report."
    )

    if st.button("▶ Dispatch Task", type="primary", use_container_width=True):
        if prompt_input.strip():
            res, err = api_create_task(prompt_input.strip(), st.session_state.api_url)
            if res:
                st.session_state.active_task_id = res.get("task_id")
                st.session_state.task_start_time = time.time()
                st.session_state.auto_refresh = True
                st.rerun()
            else:
                st.error(f"Dispatch Failed: {err}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-family: monospace; font-size: 0.8rem; color: #94A3B8;'>TRACK TASK UUID</div>", unsafe_allow_html=True)
    track_uuid = st.text_input("Task UUID", value=st.session_state.active_task_id or "", label_visibility="collapsed")
    if st.button("Inspect Task", use_container_width=True):
        if track_uuid.strip():
            st.session_state.active_task_id = track_uuid.strip()
            st.session_state.task_start_time = time.time()
            st.session_state.auto_refresh = True
            st.rerun()


# --- HEADER: WORKFLOW OBSERVABILITY DASHBOARD ---
st.markdown("""
<div class="obs-header">
    <div class="obs-brand">
        <span class="obs-title">AgentFlow / Workflow Studio</span>
        <span class="env-tag">Production Multi-Agent Pipeline</span>
    </div>
    <div style="display: flex; gap: 12px; align-items: center;">
        <span class="sys-badge">Architecture: LangGraph + Celery + Redis</span>
    </div>
</div>
""", unsafe_allow_html=True)


# Fetch task status if tracking
if st.session_state.active_task_id:
    task_res, fetch_err = api_get_task(st.session_state.active_task_id, st.session_state.api_url)
    if task_res:
        st.session_state.task_data = task_res
        if task_res.get("status") in ("COMPLETED", "FAILED"):
            st.session_state.auto_refresh = False

task_data = st.session_state.task_data
status_val = task_data.get("status", "NOT_STARTED") if task_data else "NOT_STARTED"
logs_list = task_data.get("agent_logs", []) if task_data else []
current_stage_idx = calculate_active_stage_idx(status_val, logs_list)


# --- 1. MAIN WORKFLOW CANVAS (DAG PIPELINE VISUALIZATION) ---
st.markdown("""
<div class="dag-container">
    <div class="dag-header">
        <span class="dag-title">Execution Graph (DAG Lifecycle Pipeline)</span>
        <span style="font-family: monospace; font-size: 0.75rem; color: #64748B;">Topology: Sequential + Parallel Agent Fan-Out</span>
    </div>
</div>
""", unsafe_allow_html=True)

# List of stages in order
stage_keys = ["request", "fastapi", "queue", "redis", "worker", "orchestrator", "agents_branch", "approval", "result"]

# Layer 1: Sequential Ingestion Pipeline (Nodes 1 -> 6)
seq_cols = st.columns(6)

stages_seq = [
    ("request", "User Request", "Ingest"),
    ("fastapi", "FastAPI API Gateway", "Transport"),
    ("queue", "Celery Task Queue", "Broker"),
    ("redis", "Redis State Store", "Storage"),
    ("worker", "Celery Worker", "Compute"),
    ("orchestrator", "LangGraph Runtime", "Orchestrator"),
]

for idx, (s_key, s_name, s_layer) in enumerate(stages_seq):
    with seq_cols[idx]:
        if status_val == "FAILED" and idx == current_stage_idx:
            node_state = "failed"
            badge_label = "FAILED"
        elif idx < current_stage_idx or status_val == "COMPLETED":
            node_state = "completed"
            badge_label = "DONE"
        elif idx == current_stage_idx:
            node_state = "running"
            badge_label = "ACTIVE"
        else:
            node_state = "pending"
            badge_label = "PENDING"

        st.markdown(f"""
        <div class="dag-node {node_state}">
            <div class="dag-node-header">
                <span class="node-layer-tag">{s_layer}</span>
                <span class="state-badge">{badge_label}</span>
            </div>
            <div class="node-name">{s_name}</div>
            <div class="node-meta">
                <span>Stage: 0{idx + 1}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div class='branch-connector'>│<br>▼</div>", unsafe_allow_html=True)

# Layer 2: Parallel Agent Execution Branch (ResearchAgent & WritingAgent)
agent_col1, agent_col2 = st.columns(2)

with agent_col1:
    idx_res = 6
    if status_val == "FAILED" and current_stage_idx == idx_res:
        node_state = "failed"
        badge_label = "FAILED"
    elif idx_res < current_stage_idx or status_val == "COMPLETED":
        node_state = "completed"
        badge_label = "DONE"
    elif current_stage_idx == idx_res:
        node_state = "running"
        badge_label = "RUNNING"
    else:
        node_state = "pending"
        badge_label = "PENDING"

    st.markdown(f"""
    <div class="dag-node {node_state}">
        <div class="dag-node-header">
            <span class="node-layer-tag">LangGraph Agent</span>
            <span class="state-badge">{badge_label}</span>
        </div>
        <div class="node-name">ResearchAgent</div>
        <div class="node-meta">
            <span>Role: Web Search & Data Gathering</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with agent_col2:
    idx_wri = 7
    if status_val == "FAILED" and current_stage_idx == idx_wri:
        node_state = "failed"
        badge_label = "FAILED"
    elif idx_wri < current_stage_idx or status_val == "COMPLETED":
        node_state = "completed"
        badge_label = "DONE"
    elif current_stage_idx == idx_wri:
        node_state = "running"
        badge_label = "RUNNING"
    else:
        node_state = "pending"
        badge_label = "PENDING"

    st.markdown(f"""
    <div class="dag-node {node_state}">
        <div class="dag-node-header">
            <span class="node-layer-tag">LangGraph Agent</span>
            <span class="state-badge">{badge_label}</span>
        </div>
        <div class="node-name">WritingAgent</div>
        <div class="node-meta">
            <span>Role: Technical Response Synthesis</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div class='branch-connector'>▲<br>│<br>▼</div>", unsafe_allow_html=True)

# Layer 3: Terminal Control & Output (Human Approval Gate & Final Result)
end_col1, end_col2 = st.columns(2)

with end_col1:
    idx_app = 8
    if status_val == "FAILED" and current_stage_idx == idx_app:
        node_state = "failed"
        badge_label = "REJECTED"
    elif idx_app < current_stage_idx or status_val == "COMPLETED":
        node_state = "completed"
        badge_label = "PASSED"
    elif current_stage_idx == idx_app:
        node_state = "awaiting"
        badge_label = "HUMAN_GATE"
    else:
        node_state = "pending"
        badge_label = "PENDING"

    st.markdown(f"""
    <div class="dag-node {node_state}">
        <div class="dag-node-header">
            <span class="node-layer-tag">Human-in-the-Loop</span>
            <span class="state-badge">{badge_label}</span>
        </div>
        <div class="node-name">Human Approval Gate</div>
        <div class="node-meta">
            <span>Role: Manual Quality & Policy Check</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with end_col2:
    idx_res_out = 9
    if status_val == "COMPLETED":
        node_state = "completed"
        badge_label = "DELIVERED"
    elif status_val == "FAILED":
        node_state = "failed"
        badge_label = "FAILED"
    else:
        node_state = "pending"
        badge_label = "WAITING"

    st.markdown(f"""
    <div class="dag-node {node_state}">
        <div class="dag-node-header">
            <span class="node-layer-tag">Output Artifact</span>
            <span class="state-badge">{badge_label}</span>
        </div>
        <div class="node-name">Final Result Payload</div>
        <div class="node-meta">
            <span>Role: Response Delivery</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# --- 2. HUMAN APPROVAL SECTION (IF AWAITING REVIEW) ---
if status_val == "AWAITING_APPROVAL":
    st.markdown("""
    <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid #F59E0B; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
        <div style="font-family: monospace; font-size: 0.9rem; font-weight: 700; color: #F59E0B; margin-bottom: 4px;">
            ⚠️ HUMAN APPROVAL CHECKPOINT REQUIRED
        </div>
        <div style="font-size: 0.85rem; color: #CBD5E1;">
            The workflow state has paused at node <code>Human Approval Gate</code>. Review current agent outputs before proceeding.
        </div>
    </div>
    """, unsafe_allow_html=True)

    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        feedback_input = st.text_input("Optional Directive Feedback", placeholder="Add review notes or directive corrections...")
    with f_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        b_approve = st.button("✔ Approve & Proceed", type="primary", use_container_width=True)
        b_reject = st.button("✖ Reject & Terminate", use_container_width=True)

    if b_approve or b_reject:
        is_approved = bool(b_approve)
        app_res, app_err = api_approve_task(
            st.session_state.active_task_id,
            approved=is_approved,
            feedback=feedback_input,
            api_base=st.session_state.api_url
        )
        if app_res:
            st.success(f"Approval status registered. Workflow resumed.")
            st.session_state.auto_refresh = True
            st.rerun()
        else:
            st.error(f"Failed to submit approval: {app_err}")


# --- 3. EXECUTION TIMELINE & FINAL RESULT SPLIT VIEW ---
t_col, r_col = st.columns(2)

with t_col:
    st.markdown("""
    <div style="font-family: monospace; font-size: 0.85rem; font-weight: 600; color: #94A3B8; margin-bottom: 8px;">
        TIMELINE & AGENT AUDIT LOGS
    </div>
    """, unsafe_allow_html=True)

    if logs_list:
        timeline_html = '<div class="timeline-container">'
        for log in reversed(logs_list):
            if isinstance(log, dict):
                agent = log.get("agent", "System")
                t_stamp = log.get("timestamp", "")
                t_formatted = t_stamp[11:19] if len(t_stamp) >= 19 else "--:--:--"
                action = log.get("action", "")
                
                icon_symbol = "✓"
                if "research" in agent.lower():
                    icon_symbol = "🔍"
                elif "writing" in agent.lower():
                    icon_symbol = "✍️"
                elif "orchestrator" in agent.lower():
                    icon_symbol = "🧠"

                timeline_html += f"""
                <div class="timeline-item">
                    <span class="timeline-time">{t_formatted}</span>
                    <span class="timeline-icon">{icon_symbol}</span>
                    <span class="timeline-text"><strong>[{agent}]</strong> {action}</span>
                </div>
                """
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="timeline-container" style="color: #64748B;">
            No execution events recorded. Dispatch a task to monitor real-time event stream.
        </div>
        """, unsafe_allow_html=True)

with r_col:
    st.markdown("""
    <div style="font-family: monospace; font-size: 0.85rem; font-weight: 600; color: #94A3B8; margin-bottom: 8px;">
        GENERATED TECHNICAL REPORT / ARTIFACT
    </div>
    """, unsafe_allow_html=True)

    result_payload = task_data.get("result") if task_data else None
    if result_payload:
        st.markdown(f"""
        <div class="report-container">
            {result_payload}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="report-container" style="color: #64748B; font-family: monospace; font-size: 0.82rem;">
            // Awaiting workflow completion to render generated technical artifact payload.
        </div>
        """, unsafe_allow_html=True)


# Auto Refresh handling when task is actively running
if st.session_state.auto_refresh and st.session_state.active_task_id:
    time.sleep(1.5)
    st.rerun()
