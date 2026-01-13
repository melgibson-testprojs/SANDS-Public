# streamlit_global/app.py

import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from data.ids_log_reader import load_logs
from analytics.metrics import compute_kpis
from charts.plots import (
    decision_timeline,
    anomaly_trend,
    protocol_distribution,
    decision_breakdown,
)
from utils.time_filters import apply_time_filter


# -------------------------------------------------
# Streamlit config
# -------------------------------------------------

st.set_page_config(
    page_title="SwarmSec – Global Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ SwarmSec – Global Network Analytics")
st.caption("Network-wide IDS & ML posture (log-based)")

# -------------------------------------------------
# Load data (cached)
# -------------------------------------------------

@st.cache_data(ttl=10)
def load_data():
    return load_logs("logs/swarmsec_ids.log")


df = load_data()

if df.empty:
    st.warning("No IDS logs found in /logs directory.")
    st.stop()

# 🔄 Live auto-refresh (every 5 seconds)
st_autorefresh(interval=5000, key="log_refresh")


# -------------------------------------------------
# Sidebar – Filters
# -------------------------------------------------

with st.sidebar:
    st.header("🔍 Filters")

    time_range = st.selectbox(
        "Time Range",
        [
            "Last 1 Hour",
            "Last 24 Hours",
            "Last 7 Days",
            "Last 30 Days",
            "Last 1 Year",
            "All",
            "Custom",
        ],
    )

    custom_start = None
    custom_end = None

    if time_range == "Custom":
        custom_start = st.date_input(
            "Start Date",
            value=datetime.now().date()
        )
        custom_end = st.date_input(
            "End Date",
            value=datetime.now().date()
        )

        custom_start = datetime.combine(
            custom_start, datetime.min.time()
        )
        custom_end = datetime.combine(
            custom_end, datetime.max.time()
        )

    # Agent filter
    agents = ["All"] + sorted(df["agent"].dropna().unique().tolist())
    agent_filter = st.selectbox("Agent", agents)

    # Protocol filter
    protocols = ["All"] + sorted(df["protocol"].dropna().unique().tolist())
    protocol_filter = st.selectbox("Protocol", protocols)

    # Decision filter
    decisions = ["All"] + sorted(df["decision"].dropna().unique().tolist())
    decision_filter = st.selectbox("Decision", decisions)

# -------------------------------------------------
# Apply filters
# -------------------------------------------------

filtered_df = apply_time_filter(
    df,
    time_range,
    custom_start,
    custom_end,
)

if agent_filter != "All":
    filtered_df = filtered_df[
        filtered_df["agent"] == agent_filter
    ]

if protocol_filter != "All":
    filtered_df = filtered_df[
        filtered_df["protocol"] == protocol_filter
    ]

if decision_filter != "All":
    filtered_df = filtered_df[
        filtered_df["decision"] == decision_filter
    ]

# -------------------------------------------------
# KPIs
# -------------------------------------------------

kpis = compute_kpis(filtered_df)

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total Flows", kpis["total"])
col2.metric("ATTACK", kpis["attack"])
col3.metric("SUSPICIOUS", kpis["suspicious"])
col4.metric("Avg Recon Err", kpis["avg_recon"])
col5.metric("Max Recon Err", kpis["max_recon"])
col6.metric("Agents", kpis["agents"])

st.divider()

# -------------------------------------------------
# Charts
# -------------------------------------------------

st.subheader("📈 Decision Timeline")
st.plotly_chart(
    decision_timeline(filtered_df),
    width="stretch",
)

st.subheader("🔥 Autoencoder Anomaly Trend")
st.plotly_chart(
    anomaly_trend(filtered_df),
    width="stretch",
)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🌐 Protocol Distribution")
    st.plotly_chart(
        protocol_distribution(filtered_df),
        width="stretch",
    )

with col_b:
    st.subheader("⚠️ Decision Breakdown")
    st.plotly_chart(
        decision_breakdown(filtered_df),
        width="stretch",
    )

st.divider()

# -------------------------------------------------
# Recent Events Table
# -------------------------------------------------

st.subheader("🧾 Recent Events")

display_cols = [
    "timestamp",
    "agent",
    "src_ip",
    "dst_ip",
    "protocol",
    "decision",
    "ae_flag",
    "recon_err",
]

available_cols = [
    c for c in display_cols if c in filtered_df.columns
]

st.dataframe(
    filtered_df
    .sort_values("timestamp", ascending=False)
    [available_cols]
    .head(100),
    use_container_width=True,
)

# -------------------------------------------------
# Footer
# -------------------------------------------------

st.caption(
    f"Log entries loaded: {len(filtered_df)} | "
    f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"
)
