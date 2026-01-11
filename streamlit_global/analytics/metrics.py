# streamlit_global/analytics/metrics.py

import pandas as pd


def compute_kpis(df: pd.DataFrame) -> dict:
    """
    Compute global SOC KPIs from IDS log DataFrame.
    """

    if df.empty:
        return {
            "total": 0,
            "attack": 0,
            "suspicious": 0,
            "anomaly_rate": 0.0,
            "avg_recon": 0.0,
            "max_recon": 0.0,
            "agents": 0,
            "lids": 0,
        }

    total = len(df)

    attack = int((df["decision"] == "ATTACK").sum())
    suspicious = int((df["decision"] == "SUSPICIOUS").sum())

    anomaly_rate = (
        (suspicious / total) * 100.0 if total > 0 else 0.0
    )

    avg_recon = float(
        df["recon_err"].dropna().mean()
        if "recon_err" in df else 0.0
    )

    max_recon = float(
        df["recon_err"].dropna().max()
        if "recon_err" in df else 0.0
    )

    agents = df["agent"].nunique() if "agent" in df else 0
    lids = df["lid"].nunique() if "lid" in df else 0

    return {
        "total": total,
        "attack": attack,
        "suspicious": suspicious,
        "anomaly_rate": round(anomaly_rate, 2),
        "avg_recon": round(avg_recon, 2),
        "max_recon": round(max_recon, 2),
        "agents": agents,
        "lids": lids,
    }

def compute_kpis_for_window(df: pd.DataFrame, start_ts, end_ts) -> dict:
    """
    Compute KPIs for a specific time window.
    """
    mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
    return compute_kpis(df.loc[mask])
