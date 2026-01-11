# streamlit_global/charts/plots.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ----------------------------------
# Decision Timeline
# ----------------------------------

def decision_timeline(df: pd.DataFrame):
    """
    Stacked timeline of BENIGN / SUSPICIOUS / ATTACK.
    """

    if df.empty:
        return go.Figure()

    timeline = (
        df
        .groupby([
            pd.Grouper(key="timestamp", freq="1min"),
            "decision"
        ])
        .size()
        .reset_index(name="count")
    )

    fig = px.area(
        timeline,
        x="timestamp",
        y="count",
        color="decision",
        title="Decision Timeline",
        color_discrete_map={
            "BENIGN": "#3ddc97",
            "SUSPICIOUS": "#f6c343",
            "ATTACK": "#ff6b6b"
        }
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Flows",
        legend_title="Decision",
        template="plotly_dark",
        height=350
    )

    return fig


# ----------------------------------
# Autoencoder Anomaly Trend
# ----------------------------------

def anomaly_trend(df: pd.DataFrame, threshold: float | None = None):
    """
    Reconstruction error over time.
    """

    if df.empty or "recon_err" not in df:
        return go.Figure()

    fig = px.scatter(
        df,
        x="timestamp",
        y="recon_err",
        color="decision",
        title="Autoencoder Reconstruction Error",
        color_discrete_map={
            "BENIGN": "#3ddc97",
            "SUSPICIOUS": "#f6c343",
            "ATTACK": "#ff6b6b"
        }
    )

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="red",
            annotation_text="AE Threshold"
        )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Reconstruction Error",
        template="plotly_dark",
        height=350
    )

    return fig


# ----------------------------------
# Protocol Distribution
# ----------------------------------

def protocol_distribution(df: pd.DataFrame):
    """
    Pie chart of protocol usage.
    """

    if df.empty or "protocol" not in df:
        return go.Figure()

    counts = df["protocol"].value_counts().reset_index()
    counts.columns = ["protocol", "count"]

    fig = px.pie(
        counts,
        names="protocol",
        values="count",
        title="Protocol Distribution",
        hole=0.4
    )

    fig.update_layout(
        template="plotly_dark",
        height=300
    )

    return fig


# ----------------------------------
# Decision Breakdown
# ----------------------------------

def decision_breakdown(df: pd.DataFrame):
    """
    Bar chart of decision counts.
    """

    if df.empty:
        return go.Figure()

    counts = df["decision"].value_counts().reset_index()
    counts.columns = ["decision", "count"]

    fig = px.bar(
        counts,
        x="decision",
        y="count",
        color="decision",
        title="Decision Breakdown",
        color_discrete_map={
            "BENIGN": "#3ddc97",
            "SUSPICIOUS": "#f6c343",
            "ATTACK": "#ff6b6b"
        }
    )

    fig.update_layout(
        template="plotly_dark",
        height=300,
        showlegend=False
    )

    return fig
