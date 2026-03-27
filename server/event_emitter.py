import requests
import logging

DASHBOARD_URL = "http://localhost:8001"   # dashboard backend
TIMEOUT = 0.5

log = logging.getLogger("fusion_event_emitter")

def emit_prediction_event(
    agent_id: str,
    fusion_result: dict,
    flow_meta: dict | None
):
    payload = {
        "device_key": f"agent:{agent_id}",
        "decision": fusion_result.get("final_decision"),
        # use recon error as anomaly/confidence signal
        "score": fusion_result.get("reconstruction_error"),
        "source": "fusion",
        "extra": {
            "supervised": fusion_result.get("supervised_pred"),
            "ae_flag": fusion_result.get("autoencoder_flag"),
            "src": f"{flow_meta.get('src_ip')}:{flow_meta.get('src_port')}" if flow_meta else "NA",
            "dst": f"{flow_meta.get('dst_ip')}:{flow_meta.get('dst_port')}" if flow_meta else "NA",
            "proto": flow_meta.get("protocol") if flow_meta else "NA"
        }
    }

    try:
        requests.post(
            f"{DASHBOARD_URL}/agent/predict",
            json=payload,
            timeout=TIMEOUT
        )
    except Exception as e:
        log.debug(f"Prediction emit failed: {e}")
