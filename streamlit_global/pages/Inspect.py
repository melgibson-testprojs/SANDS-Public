# streamlit_global/pages/Inspect.py

import streamlit as st
from datetime import datetime

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
# Page config
# -------------------------------------------------

st.set_page_config(
    page_title="SwarmSec – Device Inspect",
    layout="wide",
)

# -------------------------------------------------
# Read query param (MAC-centric)
# -------------------------------------------------

params = st.query_params
mac = params.get("mac")

if not mac:
    st.error("❌ No device selected (missing MAC)")
    st.stop()

mac = mac.lower().strip()

st.title("🔍 Device Inspect")
st.caption(f"MAC Address: {mac}")

# -------------------------------------------------
# Load logs (cached)
# -------------------------------------------------

@st.cache_data(ttl=5)
def load_data():
    return load_logs("logs/swarmsec_ids.log")

df = load_data()

# ---- FIX 1: Correct column check (MAC, not LID)
if df.empty or "mac" not in df.columns:
    st.warning("No IDS data available.")
    st.stop()


# -------------------------------------------------
# Filter logs for this device (DEFENSIVE)
# -------------------------------------------------

device_df = df[
    df["mac"]
    .astype(str)
    .str.lower()
    .str.replace("mac=", "", regex=False)
    .str.strip()
    == mac
]

if device_df.empty:
    st.warning("No activity recorded for this device yet.")
    st.stop()

# -------------------------------------------------
# Sidebar – Time filter
# -------------------------------------------------

with st.sidebar:
    st.header("⏱️ Time Filter")

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
        key="inspect_time_range",
    )

    custom_start = None
    custom_end = None

    if time_range == "Custom":
        custom_start = st.date_input(
            "Start Date",
            value=datetime.now().date(),
            key="inspect_start_date",
        )
        custom_end = st.date_input(
            "End Date",
            value=datetime.now().date(),
            key="inspect_end_date",
        )

        custom_start = datetime.combine(custom_start, datetime.min.time())
        custom_end = datetime.combine(custom_end, datetime.max.time())

# Apply time filter
filtered_df = apply_time_filter(
    device_df,
    time_range,
    custom_start,
    custom_end,
)

if filtered_df.empty:
    st.warning("No data in selected time range.")
    st.stop()

# -------------------------------------------------
# Device identity summary
# -------------------------------------------------

latest = filtered_df.sort_values("timestamp").iloc[-1]

with st.container():
    col1, col2 = st.columns(2)
    col1.metric("MAC", latest.get("mac", "UNKNOWN"))
    col2.metric("IP", latest.get("src_ip", "UNKNOWN"))

    st.markdown("<br>", unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    col3.metric(
        "First Seen",
        filtered_df["timestamp"].min().strftime("%Y-%m-%d %H:%M:%S")
    )
    col4.metric(
        "Last Seen",
        filtered_df["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")
    )



# -------------------------------------------------
# KPIs
# -------------------------------------------------

kpis = compute_kpis(filtered_df)

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Total Flows", kpis["total"])
k2.metric("ATTACK", kpis["attack"])
k3.metric("SUSPICIOUS", kpis["suspicious"])
benign = (
    kpis["total"]
    - kpis.get("attack", 0)
    - kpis.get("suspicious", 0)
)

k4.metric("BENIGN", benign)
k5.metric("Avg Recon Err", kpis["avg_recon"])
k6.metric("Max Recon Err", kpis["max_recon"])

st.divider()

# -------------------------------------------------
# Charts (UNIQUE KEYS, FUTURE-PROOF)
# -------------------------------------------------

st.subheader("📈 Decision Timeline")
st.plotly_chart(
    decision_timeline(filtered_df),
    width="stretch",
    key="inspect_decision_timeline",
)

st.subheader("🔥 Autoencoder Anomaly Trend")
st.plotly_chart(
    anomaly_trend(filtered_df),
    width="stretch",
    key="inspect_anomaly_trend",
)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🌐 Protocol Distribution")
    st.plotly_chart(
        protocol_distribution(filtered_df),
        width="stretch",
        key="inspect_protocol_dist",
    )

with col_b:
    st.subheader("⚠️ Decision Breakdown")
    st.plotly_chart(
        decision_breakdown(filtered_df),
        width="stretch",
        key="inspect_decision_breakdown",
    )

st.divider()

# -------------------------------------------------
# Flow table (deep inspection)
# -------------------------------------------------

st.subheader("🧾 Flow Details")

display_cols = [
    "timestamp",
    "src_ip",
    "dst_ip",
    "protocol",
    "decision",
    "ae_flag",
    "recon_err",
]

available_cols = [c for c in display_cols if c in filtered_df.columns]

st.dataframe(
    filtered_df
    .sort_values("timestamp", ascending=False)[available_cols]
    .head(500),
    width="stretch",
    key="inspect_flow_table",
)

st.caption(
    f"Flows shown: {len(filtered_df)} | "
    f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"
)
