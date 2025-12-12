"""
CICFlowMeter-style 77-feature extractor (CSE-CIC-IDS2018 compatible).

Usage:
    from agent.utils.cic_feature_extractor import FEATURE_NAMES, extract_cic_features

    features = extract_cic_features(flow_dict)  # returns list of 77 numbers

This is defensive: missing fields -> zeros/defaults.
"""

from collections import Counter
import math

# --- Canonical feature names (77) ---
FEATURE_NAMES = [
    "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts", "TotLen Bwd Pkts",
    "Fwd Pkt Len Max", "Fwd Pkt Len Min", "Fwd Pkt Len Mean", "Fwd Pkt Len Std",
    "Bwd Pkt Len Max", "Bwd Pkt Len Min", "Bwd Pkt Len Mean", "Bwd Pkt Len Std",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Tot", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
    "Bwd IAT Tot", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    "Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags",
    "Fwd Header Len", "Bwd Header Len", "Fwd Pkts/s", "Bwd Pkts/s",
    "Pkt Len Min", "Pkt Len Max", "Pkt Len Mean", "Pkt Len Std", "Pkt Len Var",
    "FIN Flag Cnt", "SYN Flag Cnt", "RST Flag Cnt", "PSH Flag Cnt", "ACK Flag Cnt",
    "URG Flag Cnt", "ECE Flag Cnt", "Down/Up Ratio", "Pkt Size Avg",
    "Fwd Seg Size Avg", "Bwd Seg Size Avg", "Fwd Byts/b Avg", "Fwd Pkts/b Avg",
    "Fwd Blk Rate Avg", "Bwd Byts/b Avg", "Bwd Pkts/b Avg", "Bwd Blk Rate Avg",
    "Subflow Fwd Pkts", "Subflow Fwd Byts", "Subflow Bwd Pkts", "Subflow Bwd Byts",
    "Init Wnd Bytes Fwd", "Init Wnd Bytes Bwd", "Fwd Act Data Pkts", "Min Seg Size Fwd",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
    "Label", "Flow Byts/s", "Flow Pkts/s", "Flow IAT Tot"
]

# Safety pad/truncate to 77
if len(FEATURE_NAMES) != 77:
    if len(FEATURE_NAMES) > 77:
        FEATURE_NAMES = FEATURE_NAMES[:77]
    else:
        FEATURE_NAMES += [f"extra_{i}" for i in range(len(FEATURE_NAMES), 77)]


def _safe_mean(vals):
    try:
        return float(sum(vals)) / len(vals) if vals else 0.0
    except Exception:
        return 0.0


def _safe_std(vals):
    if not vals:
        return 0.0
    m = _safe_mean(vals)
    var = sum((x - m) ** 2 for x in vals) / len(vals)
    return math.sqrt(var)


def extract_cic_features(flow: dict):
    """
    Given an aggregated flow dict (packets optional), return a 77-dim list in FEATURE_NAMES order.
    Missing data => 0 defaults.
    """
    pkts = flow.get("packets", []) or []
    start = flow.get("start_ts")
    end = flow.get("end_ts")
    if not start or not end:
        if pkts:
            start = start or min(p.get("ts", 0.0) for p in pkts)
            end = end or max(p.get("ts", 0.0) for p in pkts)
        else:
            start = start or 0.0
            end = end or 0.0

    duration = max(0.0, float(end) - float(start))
    total_pkts = int(flow.get("pkt_counts", {}).get("total", len(pkts)))
    fwd_pkts = int(flow.get("pkt_counts", {}).get("src_to_dst", 0))
    bwd_pkts = int(flow.get("pkt_counts", {}).get("dst_to_src", 0))
    total_bytes = int(flow.get("total_bytes", 0) or sum(int(p.get("length", 0)) for p in pkts))
    fwd_bytes = int(flow.get("directional_bytes", {}).get("src_to_dst", 0))
    bwd_bytes = int(flow.get("directional_bytes", {}).get("dst_to_src", 0))

    # packet lengths by direction
    fwd_lengths = [int(p.get("length", 0)) for p in pkts if p.get("src_ip") == flow.get("src_ip") and p.get("src_port") == flow.get("src_port")]
    bwd_lengths = [int(p.get("length", 0)) for p in pkts if p.get("src_ip") == flow.get("dst_ip") and p.get("src_port") == flow.get("dst_port")]
    all_lengths = [int(p.get("length", 0)) for p in pkts]

    # flow IATs (inter-arrival times) overall and per direction
    times = [p.get("ts", 0.0) for p in pkts]
    times_sorted = sorted(times)
    iats = [t2 - t1 for t1, t2 in zip(times_sorted[:-1], times_sorted[1:])] if len(times_sorted) > 1 else []

    # directional IATs
    fwd_times = [p.get("ts", 0.0) for p in pkts if p.get("src_ip") == flow.get("src_ip") and p.get("src_port") == flow.get("src_port")]
    bwd_times = [p.get("ts", 0.0) for p in pkts if p.get("src_ip") == flow.get("dst_ip") and p.get("src_port") == flow.get("dst_port")]
    fwd_iats = [t2 - t1 for t1, t2 in zip(sorted(fwd_times)[:-1], sorted(fwd_times)[1:])] if len(fwd_times) > 1 else []
    bwd_iats = [t2 - t1 for t1, t2 in zip(sorted(bwd_times)[:-1], sorted(bwd_times)[1:])] if len(bwd_times) > 1 else []

    # header lengths if present
    fwd_hdrs = [int(p.get("header_len", 0)) for p in pkts if p.get("src_ip") == flow.get("src_ip") and p.get("src_port") == flow.get("src_port")]
    bwd_hdrs = [int(p.get("header_len", 0)) for p in pkts if p.get("src_ip") == flow.get("dst_ip") and p.get("src_port") == flow.get("dst_port")]

    # flag counts (TCP)
    tcp_flags_counter = Counter()
    for p in pkts:
        flags = p.get("flags")
        if flags:
            if isinstance(flags, str):
                for ch in flags:
                    tcp_flags_counter[ch] += 1
            else:
                try:
                    for ch in str(flags):
                        tcp_flags_counter[ch] += 1
                except Exception:
                    pass

    fin = tcp_flags_counter.get("F", 0)
    syn = tcp_flags_counter.get("S", 0)
    rst = tcp_flags_counter.get("R", 0)
    psh = tcp_flags_counter.get("P", 0)
    ack = tcp_flags_counter.get("A", 0)
    urg = tcp_flags_counter.get("U", 0)
    ece = tcp_flags_counter.get("E", 0) or tcp_flags_counter.get("C", 0)

    # flow rates
    pkt_rate_fwd = float(fwd_pkts) / duration if duration > 0 else float(fwd_pkts)
    pkt_rate_bwd = float(bwd_pkts) / duration if duration > 0 else float(bwd_pkts)

    # packet size statistics
    pkt_min = min(all_lengths) if all_lengths else 0
    pkt_max = max(all_lengths) if all_lengths else 0
    pkt_mean = _safe_mean(all_lengths)
    pkt_std = _safe_std(all_lengths)
    pkt_var = pkt_std ** 2

    fwd_seg_avg = _safe_mean(fwd_lengths)
    bwd_seg_avg = _safe_mean(bwd_lengths)

    down_up_ratio = (bwd_bytes / fwd_bytes) if fwd_bytes else float(bwd_bytes)
    pkt_size_avg = pkt_mean

    # subflow approximations
    def _compute_subflows(pkts_list, idle_threshold=1.0):
        if not pkts_list:
            return (0.0, 0.0)
        sub_pkt_counts = []
        sub_byte_counts = []
        cur_pkt = 0
        cur_bytes = 0
        last_ts = None
        for p in sorted(pkts_list, key=lambda x: x.get("ts", 0.0)):
            ts = p.get("ts", 0.0)
            if last_ts is None or (ts - last_ts) <= idle_threshold:
                cur_pkt += 1
                cur_bytes += int(p.get("length", 0))
            else:
                sub_pkt_counts.append(cur_pkt)
                sub_byte_counts.append(cur_bytes)
                cur_pkt = 1
                cur_bytes = int(p.get("length", 0))
            last_ts = ts
        sub_pkt_counts.append(cur_pkt)
        sub_byte_counts.append(cur_bytes)
        return (_safe_mean(sub_pkt_counts), _safe_mean(sub_byte_counts))

    fwd_pkts_list = [p for p in pkts if p.get("src_ip") == flow.get("src_ip") and p.get("src_port") == flow.get("src_port")]
    bwd_pkts_list = [p for p in pkts if p.get("src_ip") == flow.get("dst_ip") and p.get("src_port") == flow.get("dst_port")]
    subf_fw_pkt_avg, subf_fw_byt_avg = _compute_subflows(fwd_pkts_list)
    subf_bw_pkt_avg, subf_bw_byt_avg = _compute_subflows(bwd_pkts_list)

    def _init_win_bytes(pkts_list, window_packets=3):
        if not pkts_list:
            return 0
        first_pkts = sorted(pkts_list, key=lambda x: x.get("ts", 0.0))[:window_packets]
        return sum(int(p.get("length", 0)) for p in first_pkts)

    init_wnd_fwd = _init_win_bytes(fwd_pkts_list)
    init_wnd_bwd = _init_win_bytes(bwd_pkts_list)

    def _active_idle_stats(pkts_list, active_threshold=1.0):
        if not pkts_list:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        ts_sorted = sorted([p.get("ts", 0.0) for p in pkts_list])
        gaps = [t2 - t1 for t1, t2 in zip(ts_sorted[:-1], ts_sorted[1:])]
        active_periods = []
        idle_periods = []
        seg_start = ts_sorted[0]
        last = ts_sorted[0]
        for g, t in zip(gaps, ts_sorted[1:]):
            if g > active_threshold:
                active_periods.append(last - seg_start)
                idle_periods.append(g)
                seg_start = t
            last = t
        active_periods.append(last - seg_start)
        if not active_periods:
            active_periods = [0.0]
        if not idle_periods:
            idle_periods = [0.0]
        return (_safe_mean(active_periods), _safe_std(active_periods), max(active_periods), min(active_periods),
                _safe_mean(idle_periods), _safe_std(idle_periods), max(idle_periods), min(idle_periods))

    active_mean, active_std, active_max, active_min, idle_mean, idle_std, idle_max, idle_min = _active_idle_stats(times_sorted := times_sorted if (times_sorted := sorted(times)) else [])

    act_data_pkt_fwd = sum(1 for p in fwd_pkts_list if int(p.get("length", 0)) > 0)
    min_seg_size_fwd = min((int(p.get("length", 0)) for p in fwd_pkts_list), default=0)

    flow_byts_s = total_bytes / duration if duration > 0 else float(total_bytes)
    flow_pkts_s = total_pkts / duration if duration > 0 else float(total_pkts)
    flow_iat_tot = sum(iats) if iats else 0.0

    feat = [
        float(duration), int(fwd_pkts), int(bwd_pkts), int(fwd_bytes), int(bwd_bytes),
        int(max(fwd_lengths) if fwd_lengths else 0), int(min(fwd_lengths) if fwd_lengths else 0),
        float(_safe_mean(fwd_lengths)), float(_safe_std(fwd_lengths)),
        int(max(bwd_lengths) if bwd_lengths else 0), int(min(bwd_lengths) if bwd_lengths else 0),
        float(_safe_mean(bwd_lengths)), float(_safe_std(bwd_lengths)),
        float(_safe_mean(iats)), float(_safe_std(iats)), float(max(iats) if iats else 0.0), float(min(iats) if iats else 0.0),
        float(sum(fwd_iats)), float(_safe_mean(fwd_iats)), float(_safe_std(fwd_iats)),
        float(max(fwd_iats) if fwd_iats else 0.0), float(min(fwd_iats) if fwd_iats else 0.0),
        float(sum(bwd_iats)), float(_safe_mean(bwd_iats)), float(_safe_std(bwd_iats)),
        float(max(bwd_iats) if bwd_iats else 0.0), float(min(bwd_iats) if bwd_iats else 0.0),
        int(sum(1 for p in fwd_pkts_list if 'P' in str(p.get("flags","")))),
        int(sum(1 for p in bwd_pkts_list if 'P' in str(p.get("flags","")))),
        int(sum(1 for p in fwd_pkts_list if 'U' in str(p.get("flags","")))),
        int(sum(1 for p in bwd_pkts_list if 'U' in str(p.get("flags","")))),
        int(sum(fwd_hdrs) if fwd_hdrs else 0), int(sum(bwd_hdrs) if bwd_hdrs else 0),
        float(pkt_rate_fwd), float(pkt_rate_bwd), int(pkt_min), int(pkt_max), float(pkt_mean), float(pkt_std), float(pkt_var),
        int(fin), int(syn), int(rst), int(psh), int(ack), int(urg), int(ece),
        float(down_up_ratio), float(pkt_size_avg), float(fwd_seg_avg), float(bwd_seg_avg),
        float(subf_fw_byt_avg), float(subf_fw_pkt_avg), float(subf_fw_pkt_avg if subf_fw_pkt_avg else 0.0),
        float(subf_bw_byt_avg), float(subf_bw_pkt_avg), float(subf_bw_pkt_avg if subf_bw_pkt_avg else 0.0),
        float(subf_fw_pkt_avg), float(subf_fw_byt_avg), float(subf_bw_pkt_avg), float(subf_bw_byt_avg),
        int(init_wnd_fwd), int(init_wnd_bwd), int(act_data_pkt_fwd), int(min_seg_size_fwd),
        float(active_mean), float(active_std), float(active_max), float(active_min),
        float(idle_mean), float(idle_std), float(idle_max), float(idle_min),
        0.0, float(flow_byts_s), float(flow_pkts_s), float(flow_iat_tot)
    ]

    # pad/truncate to 77
    if len(feat) != 77:
        if len(feat) < 77:
            feat += [0.0] * (77 - len(feat))
        else:
            feat = feat[:77]
    return feat
