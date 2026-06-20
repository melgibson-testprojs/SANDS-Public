# SANDS — Swarm-based Anomaly Network Detection System

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124.2-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.52.1-FF4B4B.svg)](https://streamlit.io/)
[![Scapy](https://img.shields.io/badge/Scapy-2.6.1-red.svg)](https://scapy.net/)
[![XGBoost](https://img.shields.io/badge/XGBoost-3.1.2-green.svg)](https://xgboost.readthedocs.io/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.20.0-orange.svg)](https://www.tensorflow.org/)

**SANDS** is a distributed, edge-based Intrusion Detection and Mitigation System. Lightweight agents capture network traffic locally, run hybrid machine learning inference to detect anomalies, and coordinate with each other over a peer-to-peer MQTT swarm to vote on and automatically quarantine malicious devices — without relying on a central decision-making server.

---

## Overview

Traditional IDS setups route all traffic through a single analysis point, which becomes a bottleneck and a single point of failure. SANDS instead deploys agents at the network edge (gateways, endpoints). Each agent independently captures packets, builds flow records, and extracts statistical features. When an agent's local ML model flags suspicious behavior, it raises an alert across the swarm. Peer agents factor that alert into their own risk scoring, and if enough agents agree, the swarm reaches consensus and the offending device is blocked — locally, on every node, without any single agent acting alone.

## Key Features

- **Real-time flow analysis** — Scapy-based packet capture with 80+ CICIDS2018-style extracted features
- **Hybrid ML detection** — XGBoost for known-attack classification, paired with an Autoencoder for zero-day anomaly detection
- **Decentralized consensus** — MQTT-based peer voting and leader election, with no single point of failure
- **SOC dashboard** — live device states, network topology, and a captive-portal registration flow
- **Global analytics UI** — Streamlit dashboard with live-refreshing charts and trend breakdowns
- **Explainable AI assistant** — a Groq-powered (Llama-3.3-70b) chat that answers questions about live security logs
- **Role-based access control** — admin and viewer roles, with automatic masking of MACs, IPs, and device identifiers for non-admin users
- **Offline testing tools** — PCAP replay and synthetic traffic generation for development without live capture

## Tech Stack

| Layer | Components |
| :--- | :--- |
| **API & Backend** | FastAPI 0.124.2, Uvicorn 0.38.0, Pydantic 2.12.5 |
| **Machine Learning** | TensorFlow 2.20.0, XGBoost 3.1.2, Scikit-Learn 1.7.2, Pandas 2.3.3, NumPy 2.3.3, Joblib 1.5.2 |
| **Network & Swarm** | Scapy 2.6.1, Paho-MQTT 2.1.0 (Eclipse Mosquitto broker) |
| **Visualization** | Streamlit 1.52.1, Plotly 6.5.0 |
| **Explainable AI** | Groq 0.18.0 (Llama-3.3-70b-versatile) |

## Project Structure

```
sands/
├── agent/                      # Edge agent codebase
│   ├── comm/                   # consensus.py, leader.py, mqtt_client.py, swarm_protocol.py
│   ├── core/                   # Logging, settings, device registry
│   ├── discovery/               # arp_monitor.py, dhcp_sniffer.py
│   ├── modes/                  # network_agent.py, host_agent.py
│   ├── traffic/                 # scapy_flow_collector.py
│   └── utils/                   # cic_feature_extractor.py
├── dashboard/                  # SOC management interface
│   └── app/
│       ├── api/                 # agent.py, auth.py, dashboard.py, devices.py, portal.py, topology.py
│       ├── services/             # auth_service.py, device_store.py, log_aggregator.py, xai_service.py
│       └── templates/            # dashboard.html, soc_device.html, login.html, xai_chat.html, topology.html
├── fusion/                     # fusion_engine.py — combines XGBoost + Autoencoder
├── logs/                        # swarmsec_agent.log, swarmsec_ids.log, swarmsec_server.log
├── models/                      # scapy_autoencoder.h5, scapy_xgb_model.pkl, scapy_scaler.pkl
├── risk/                        # config.py, engine.py, rules.py
├── server/                      # main.py — central ML inference backend
├── streamlit_global/            # Streamlit dashboard app
├── swarmsec-mqtt/                # Docker Compose setup for Mosquitto
└── trainer/                      # Offline model training scripts/notebooks
```

## Getting Started

### Prerequisites

- Python 3.10+
- Npcap (Windows) or libpcap (Linux) for live packet capture via Scapy
- Docker and Docker Compose, for the MQTT broker

### 1. Configure Environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_DIR=models
```

### 2. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 3. Start the MQTT Broker

```bash
cd swarmsec-mqtt
docker-compose up -d
cd ..
```

### 4. Launch the Application

**Windows (all-in-one):**

```cmd
start.bat
```

This starts the ML server (port 8000), the dashboard API (port 8001), the Streamlit UI (port 8501), and the agent auto-scaler. Run as Administrator for packet sniffing permissions.

**Manual (any OS):**

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload          # ML backend
uvicorn dashboard.app.main:app --host 0.0.0.0 --port 8001 --reload   # SOC dashboard API
streamlit run streamlit_global/app.py                                  # Global analytics UI
python -m agent.run_agent --agent-id agent-001                         # Edge agent
```

## How the Swarm Reaches Consensus

1. **Peer discovery & leader election** — On startup, each agent broadcasts a `HELLO` message. The agent with the lowest lexicographical ID becomes the swarm leader.
2. **Telemetry alerting** — If an agent's ML inference returns `ATTACK` or `SUSPICIOUS`, it publishes a warning to its device-specific topic, including the model's reconstruction error.
3. **Risk accumulation & decay** — Every peer maintains a local risk score per device:
   - ML attack classification: `+2.0`
   - ML suspicious classification: `+0.7`
   - Swarm warning multiplier: `×1.2`
   - Passive decay: `-0.01` per second
4. **Local railguard** — If a device's risk score reaches `8.0` on any single agent, that agent blocks it immediately, bypassing the vote — this caps worst-case response time for severe threats.
5. **Voting** — Once a device's risk score crosses `2.5`, the detecting agent requests a swarm vote. Peers cast `BLOCK` or `ABSTAIN` based on their own risk evaluation.
6. **Consensus** — When `60%` or more of known agents vote `BLOCK`, the leader broadcasts a consensus decision and every agent quarantines the device locally.

If the MQTT broker is unreachable, agents fall back to HTTP-only mode and skip swarm voting entirely.

## Explainable AI & Access Control

**Security Analyst Chat** — The dashboard includes an XAI chat backed by Groq's Llama-3.3-70b. It parses the user's question for identifiers (MACs, IPs, device IDs, event types like `CONSENSUS_APPLIED`), pulls up to 40 matching log entries in a compact format, and feeds them into the model for a grounded, real-time explanation.

**Role-Based Access Control** — Two built-in roles govern dashboard visibility:

- **Admin** — full access to raw MACs, IPs, and device identifiers.
- **Viewer** — sees masked data only: IPs and MACs are partially redacted, log text is automatically stripped of identifying patterns, and real device IDs are replaced with opaque hashed IDs (`dev_<hash>`) in URLs and views.


## Testing & Replay

- **PCAP playback** — run an agent against a pre-recorded capture file:
  ```bash
  python -m agent.run_agent --agent-id test-agent --pcap /path/to/traffic.pcap
  ```
- **Synthetic traffic** — when prompted `Use Scapy live capture? (y/n):`, answer `n` to run a background generator that simulates TCP flows against common ports (22, 23, 3389, 4444) for testing without elevated privileges.
- **Log review** — inspect parsed system events at `http://localhost:8001/dashboard/debug`.

## Design Decisions

- **Hybrid inference model** — combining a supervised classifier with an unsupervised autoencoder lets the system catch both known attack signatures and previously unseen anomalies. The fusion engine treats XGBoost detections as direct triggers, while autoencoder reconstruction error only forces a block at extreme deviation (`mse > 5 × threshold`), avoiding over-triggering on borderline anomalies.
- **In-memory state stores** — the dashboard keeps device and token state in memory rather than a database. This keeps setup dependency-free, at the cost of losing state on restart.
- **Decoupled discovery** — ARP/DHCP sniffing runs on separate threads from the core packet capture loop, so slower lookups never block flow collection.

## Known Issues & Limitations

- **Weak agent registration tokens** — `server/main.py` issues tokens as `token-{agent_id}`, a predictable format. Earlier design notes called for UUID-based tokens (as used elsewhere in the auth and portal services), but the ML server has not yet been updated.
- **No persistence** — all state (registered agents, device store, portal tokens) lives in memory and resets on restart.
- **MQTT dependency** — without a running Mosquitto broker, agents silently degrade to HTTP-only mode and the swarm voting layer is disabled.
