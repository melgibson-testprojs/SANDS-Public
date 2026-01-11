# streamlit_global/utils/time_filters.py

from datetime import datetime, timedelta
import pandas as pd


def apply_time_filter(
    df: pd.DataFrame,
    range_label: str,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None
) -> pd.DataFrame:
    """
    Filter DataFrame by time range.
    """

    if df.empty or "timestamp" not in df:
        return df

    now = datetime.now()

    if range_label == "Last 1 Hour":
        start = now - timedelta(hours=1)

    elif range_label == "Last 24 Hours":
        start = now - timedelta(days=1)

    elif range_label == "Last 7 Days":
        start = now - timedelta(days=7)

    elif range_label == "Last 30 Days":
        start = now - timedelta(days=30)

    elif range_label == "Last 1 Year":
        start = now - timedelta(days=365)

    elif range_label == "Custom":
        if not custom_start or not custom_end:
            return df
        return df[
            (df["timestamp"] >= custom_start) &
            (df["timestamp"] <= custom_end)
        ]

    else:  # "All"
        return df

    return df[df["timestamp"] >= start]
