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
    'Dst Port', 'Protocol', 'Flow Duration', 'Tot Fwd Pkts', 'Tot Bwd Pkts',
    'TotLen Fwd Pkts', 'TotLen Bwd Pkts', 'Fwd Pkt Len Max', 'Fwd Pkt Len Min',
    'Fwd Pkt Len Mean', 'Fwd Pkt Len Std', 'Bwd Pkt Len Max', 'Bwd Pkt Len Min',
    'Bwd Pkt Len Mean', 'Bwd Pkt Len Std', 'Flow Byts/s', 'Flow Pkts/s',
    'Flow IAT Mean', 'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min',
    'Fwd IAT Tot', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min',
    'Bwd IAT Tot', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min',
    'Fwd PSH Flags', 'Bwd PSH Flags', 'Fwd URG Flags', 'Bwd URG Flags',
    'Fwd Header Len', 'Bwd Header Len', 'Fwd Pkts/s', 'Bwd Pkts/s',
    'Pkt Len Min', 'Pkt Len Max', 'Pkt Len Mean', 'Pkt Len Std', 'Pkt Len Var',
    'FIN Flag Cnt', 'SYN Flag Cnt', 'RST Flag Cnt', 'PSH Flag Cnt',
    'ACK Flag Cnt', 'URG Flag Cnt', 'CWE Flag Count', 'ECE Flag Cnt',
    'Pkt Size Avg', 'Fwd Seg Size Avg', 'Bwd Seg Size Avg',
    'Fwd Byts/b Avg', 'Fwd Pkts/b Avg', 'Fwd Blk Rate Avg',
    'Bwd Byts/b Avg', 'Bwd Pkts/b Avg', 'Bwd Blk Rate Avg',
    'Subflow Fwd Pkts', 'Subflow Fwd Byts', 'Subflow Bwd Pkts',
    'Subflow Bwd Byts', 'Init Fwd Win Byts', 'Init Bwd Win Byts',
    'Fwd Act Data Pkts', 'Fwd Seg Size Min',
    'Active Mean', 'Active Std', 'Active Max', 'Active Min',
    'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min'
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
    duration = max(0.0, float(end) - float(start))

    fwd_pkts = int(flow.get("pkt_counts", {}).get("src_to_dst", 0))
    bwd_pkts = int(flow.get("pkt_counts", {}).get("dst_to_src", 0))

    fwd_bytes = int(flow.get("directional_bytes", {}).get("src_to_dst", 0))
    bwd_bytes = int(flow.get("directional_bytes", {}).get("dst_to_src", 0))
    total_bytes = fwd_bytes + bwd_bytes
    total_pkts = fwd_pkts + bwd_pkts

    times = [p.get("ts", 0.0) for p in pkts]
    iats = [t2 - t1 for t1, t2 in zip(times[:-1], times[1:])] if len(times) > 1 else []

    lengths = [int(p.get("length", 0)) for p in pkts]

    # Flags
    flags = Counter()
    for p in pkts:
        for ch in str(p.get("flags", "")):
            flags[ch] += 1

    # Rates
    flow_byts_s = total_bytes / duration if duration > 0 else 0.0
    flow_pkts_s = total_pkts / duration if duration > 0 else 0.0

    # Active / Idle
    def active_idle(ts):
        if len(ts) < 2:
            return (0, 0, 0, 0, 0, 0, 0, 0)
        gaps = [t2 - t1 for t1, t2 in zip(ts[:-1], ts[1:])]
        act = [g for g in gaps if g <= 1.0]
        idle = [g for g in gaps if g > 1.0]
        return (
            _safe_mean(act), _safe_std(act), max(act, default=0), min(act, default=0),
            _safe_mean(idle), _safe_std(idle), max(idle, default=0), min(idle, default=0)
        )

    active_mean, active_std, active_max, active_min, \
    idle_mean, idle_std, idle_max, idle_min = active_idle(times)

    # ============================================================
    # FEATURE MAP (STRICT)
    # ============================================================

    feats = {
        'Dst Port': float(flow.get("dst_port", 0)),
        'Protocol': 6.0 if flow.get("protocol") == "TCP" else 17.0,
        'Flow Duration': duration,
        'Tot Fwd Pkts': fwd_pkts,
        'Tot Bwd Pkts': bwd_pkts,
        'TotLen Fwd Pkts': fwd_bytes,
        'TotLen Bwd Pkts': bwd_bytes,
        'Flow Byts/s': flow_byts_s,
        'Flow Pkts/s': flow_pkts_s,
        'Pkt Len Min': min(lengths, default=0),
        'Pkt Len Max': max(lengths, default=0),
        'Pkt Len Mean': _safe_mean(lengths),
        'Pkt Len Std': _safe_std(lengths),
        'Pkt Len Var': _safe_std(lengths) ** 2,
        'FIN Flag Cnt': flags.get('F', 0),
        'SYN Flag Cnt': flags.get('S', 0),
        'RST Flag Cnt': flags.get('R', 0),
        'PSH Flag Cnt': flags.get('P', 0),
        'ACK Flag Cnt': flags.get('A', 0),
        'URG Flag Cnt': flags.get('U', 0),
        'ECE Flag Cnt': flags.get('E', 0),
        'CWE Flag Count': 0.0,   # not available
        'Pkt Size Avg': _safe_mean(lengths),
        'Init Fwd Win Byts': 0.0,
        'Init Bwd Win Byts': 0.0,
        'Fwd Act Data Pkts': fwd_pkts,
        'Fwd Seg Size Min': min(lengths, default=0),
        'Active Mean': active_mean,
        'Active Std': active_std,
        'Active Max': active_max,
        'Active Min': active_min,
        'Idle Mean': idle_mean,
        'Idle Std': idle_std,
        'Idle Max': idle_max,
        'Idle Min': idle_min,
    }

    # ============================================================
    # FINAL ORDERED VECTOR (ZERO-FILL GUARANTEED)
    # ============================================================

    return [float(feats.get(name, 0.0)) for name in FEATURE_NAMES]
