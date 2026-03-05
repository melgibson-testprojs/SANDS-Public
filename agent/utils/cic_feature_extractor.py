"""
CICFlowMeter-style feature extractor
STRICTLY ALIGNED with trained CICIDS2018 feature schema.

- Feature names & order EXACTLY match training
- Missing features -> 0.0
- Safe for StandardScaler + Autoencoder + XGBoost
"""

from collections import Counter
import math

# ============================================================
# CANONICAL FEATURE NAMES (DO NOT CHANGE ORDER)
# ============================================================

FEATURE_NAMES = [
    "Flow Duration",
    "Tot Fwd Pkts",
    "Tot Bwd Pkts",
    "Fwd Pkts/s",
    "Bwd Pkts/s",
    "Fwd Pkt Len Mean",
    "Fwd Pkt Len Std",
    "Bwd Pkt Len Mean",
    "Bwd Pkt Len Std",
    "Pkt Len Std",
    "Pkt Len Var",
    "Flow IAT Mean",
    "Flow IAT Std",
    "Flow IAT Max",
    "Flow IAT Min",
    "Fwd IAT Mean",
    "Bwd IAT Mean",
    "SYN Flag Cnt",
    "ACK Flag Cnt",
    "RST Flag Cnt",
    "PSH Flag Cnt"
]

# ============================================================
# HELPERS
# ============================================================

def _safe_mean(vals):
    return float(sum(vals)) / len(vals) if vals else 0.0


def _safe_std(vals):
    if not vals:
        return 0.0
    m = _safe_mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / len(vals))


# ============================================================
# MAIN FEATURE EXTRACTION
# ============================================================

def extract_cic_features(flow: dict):
    pkts = flow.get("packets", []) or []

    start = flow.get("start_ts", 0.0)
    end = flow.get("end_ts", 0.0)
    duration = max(0.000001, float(end) - float(start)) # Avoid div by zero

    fwd_pkts = int(flow.get("pkt_counts", {}).get("src_to_dst", 0))
    bwd_pkts = int(flow.get("pkt_counts", {}).get("dst_to_src", 0))

    # Directional sub-packets
    fwd_pkt_list = [p for p in pkts if p.get("src_ip") == flow.get("src_ip")]
    bwd_pkt_list = [p for p in pkts if p.get("src_ip") == flow.get("dst_ip")]

    def get_iats(pkt_list):
        if len(pkt_list) < 2:
            return []
        ts = sorted([p.get("ts", 0.0) for p in pkt_list])
        return [ts[i+1] - ts[i] for i in range(len(ts)-1)]

    flow_iats = [pkts[i+1]["ts"] - pkts[i]["ts"] for i in range(len(pkts)-1)] if len(pkts) > 1 else []
    fwd_iats = get_iats(fwd_pkt_list)
    bwd_iats = get_iats(bwd_pkt_list)

    fwd_lens = [p.get("length", 0) for p in fwd_pkt_list]
    bwd_lens = [p.get("length", 0) for p in bwd_pkt_list]
    all_lens = [p.get("length", 0) for p in pkts]

    # Flags
    flags = Counter()
    for p in pkts:
        for ch in str(p.get("flags", "")):
            flags[ch] += 1

    # Rates
    fwd_pkts_s = fwd_pkts / duration
    bwd_pkts_s = bwd_pkts / duration

    # ============================================================
    # FEATURE MAP (STRICT 21 FEATURES)
    # ============================================================

    feats = {
        "Flow Duration": duration,
        "Tot Fwd Pkts": fwd_pkts,
        "Tot Bwd Pkts": bwd_pkts,
        "Fwd Pkts/s": fwd_pkts_s,
        "Bwd Pkts/s": bwd_pkts_s,

        "Fwd Pkt Len Mean": _safe_mean(fwd_lens),
        "Fwd Pkt Len Std": _safe_std(fwd_lens),
        "Bwd Pkt Len Mean": _safe_mean(bwd_lens),
        "Bwd Pkt Len Std": _safe_std(bwd_lens),
        "Pkt Len Std": _safe_std(all_lens),
        "Pkt Len Var": _safe_std(all_lens) ** 2,

        "Flow IAT Mean": _safe_mean(flow_iats),
        "Flow IAT Std": _safe_std(flow_iats),
        "Flow IAT Max": max(flow_iats) if flow_iats else 0.0,
        "Flow IAT Min": min(flow_iats) if flow_iats else 0.0,
        "Fwd IAT Mean": _safe_mean(fwd_iats),
        "Bwd IAT Mean": _safe_mean(bwd_iats),

        "SYN Flag Cnt": flags.get("S", 0),
        "ACK Flag Cnt": flags.get("A", 0),
        "RST Flag Cnt": flags.get("R", 0),
        "PSH Flag Cnt": flags.get("P", 0),
    }

    # ============================================================
    # FINAL ORDERED VECTOR
    # ============================================================

    return [float(feats.get(name, 0.0)) for name in FEATURE_NAMES]
