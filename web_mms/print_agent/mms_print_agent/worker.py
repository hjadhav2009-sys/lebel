import hashlib

from .spooler import RawSpooler, SpoolError


class IntegrityError(RuntimeError): pass


class PrintWorker:
    def __init__(self, api, spooler: RawSpooler, *, transport_allowed: bool):
        self.api, self.spooler, self.transport_allowed = api, spooler, transport_allowed

    def process(self, claim: dict) -> str:
        job_id, token = claim["job_id"], claim["claim_token"]
        raw = self.api.download(job_id, token)
        if len(raw) != claim["byte_size"] or hashlib.sha256(raw).hexdigest() != claim["sha256"]:
            self.api.report(job_id, {"claim_token": token, "status": "transport_failed", "error_code": "ARTIFACT_INTEGRITY_FAILED", "error_message": "Downloaded bytes did not match the immutable artifact."})
            raise IntegrityError("Artifact SHA-256 or size mismatch")
        if not self.transport_allowed:
            self.api.report(job_id, {"claim_token": token, "status": "transport_failed", "error_code": "AGENT_TRANSPORT_DISABLED", "error_message": "Agent real transport is disabled."})
            return "disabled"
        self.api.report(job_id, {"claim_token": token, "status": "downloaded"})
        self.api.report(job_id, {"claim_token": token, "status": "spooling"})
        try: spool_id = self.spooler.spool(claim["printer_name"], raw, f"MMS {job_id}")
        except SpoolError as exc:
            state = "uncertain" if exc.uncertain else "transport_failed"
            self.api.report(job_id, {"claim_token": token, "status": state, "error_code": "RAW_SPOOL_FAILED", "error_message": str(exc)})
            return state
        self.api.report(job_id, {"claim_token": token, "status": "spooled", "spool_job_id": spool_id})
        return "spooled"
