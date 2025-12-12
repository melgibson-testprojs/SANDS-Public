from .network_agent import NetworkAgent
from ..inference.ae_local import LocalAE

class HostAgent(NetworkAgent):
    def __init__(self, config, comm):
        super().__init__(config, comm)
        self.ae = LocalAE(config.local_ae_path)

    def capabilities(self):
        return ["network", "host"]

    def run(self):
        while True:
            flow = self._collect_flow()
            features = extract_features(flow)
            ae_res = self.ae.infer(features)
            payload = {"agent_id": self.agent_id, "ts": time.time(), "features": features, "local_inference": ae_res}
            self.comm.send_telemetry(payload)
            # optionally take local action if ae_res flag is critical
            time.sleep(self.config.polling_interval)
