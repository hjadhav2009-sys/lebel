import httpx


class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=30, headers={"Authorization": f"Bearer {token}"} if token else {})

    def pair(self, payload: dict) -> dict: return self.client.post("/agent/v1/pair", json=payload).raise_for_status().json()
    def heartbeat(self, payload: dict) -> dict: return self.client.post("/agent/v1/heartbeat", json=payload).raise_for_status().json()
    def sync_printers(self, printers: list[dict]) -> dict: return self.client.post("/agent/v1/printers/sync", json={"printers": printers}).raise_for_status().json()
    def claim(self) -> dict | None:
        response = self.client.post("/agent/v1/jobs/claim")
        if response.status_code == 204: return None
        response.raise_for_status(); return response.json()
    def download(self, job_id: str, claim_token: str) -> bytes:
        response = self.client.get(f"/agent/v1/jobs/{job_id}/artifact", headers={"X-Claim-Token":claim_token}); response.raise_for_status(); return response.content
    def report(self, job_id: str, payload: dict) -> dict: return self.client.post(f"/agent/v1/jobs/{job_id}/status", json=payload).raise_for_status().json()
