# streamlit_global/data/ids_log_reader.py

import re
from pathlib import Path
from datetime import datetime
import pandas as pd


# -----------------------------
# Regex patterns
# -----------------------------

TIMESTAMP_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)"
)

KV_RE = re.compile(
    r"(\w+)=([^|]+)"
)


# -----------------------------
# Core parser
# -----------------------------

def parse_log_line(line: str) -> dict | None:
    """
    Parse a single IDS log line.
    Returns dict or None if parsing fails.
    """

    line = line.strip()
    if not line:
        return None

    # ---- Timestamp ----
    ts_match = TIMESTAMP_RE.match(line)
    if not ts_match:
        return None

    try:
        timestamp = datetime.strptime(
            ts_match.group("ts"),
            "%Y-%m-%d %H:%M:%S,%f"
        )
    except ValueError:
        return None

    # ---- Key-Value pairs ----
    fields = dict(KV_RE.findall(line))

    # ---- SRC / DST split ----
    src_ip, src_port = _split_ip_port(fields.get("SRC"))
    dst_ip, dst_port = _split_ip_port(fields.get("DST"))

    # ---- Reconstruction error ----
    recon_err = _safe_float(fields.get("RECON_ERR"))

    return {
        "timestamp": timestamp,
        "agent": fields.get("AGENT"),
        "lid": fields.get("LID"),
        "mac": fields.get("MAC"),
        "src_ip": src_ip,
        "src_port": src_port,
        "dst_ip": dst_ip,
        "dst_port": dst_port,
        "protocol": fields.get("PROTO"),
        "decision": fields.get("DECISION"),
        "supervised": fields.get("SUPERVISED"),
        "ae_flag": fields.get("AE_FLAG"),
        "recon_err": recon_err,
    }


def _split_ip_port(value: str | None):
    if not value or ":" not in value:
        return None, None
    ip, port = value.rsplit(":", 1)
    try:
        return ip.strip(), int(port)
    except ValueError:
        return ip.strip(), None


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# -----------------------------
# Public loader
# -----------------------------

def load_logs(log_path: str | Path) -> pd.DataFrame:
    """
    Load swarmsec_ids.log and return DataFrame.
    """

    log_path = Path(log_path)

    if not log_path.exists():
        return pd.DataFrame()

    records = []

    with log_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed = parse_log_line(line)
            if parsed:
                records.append(parsed)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # ---- Ensure correct dtypes ----
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)

    return df
