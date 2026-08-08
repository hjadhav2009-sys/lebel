import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PrintAgent, PrintArtifact, Printer, PrinterProfile, PrintJob
from app.services.print_state_service import transition


class AgentJobError(ValueError):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message


class AgentJobService:
    def __init__(self, db: Session):
        self.db = db

    def claim(self, agent: PrintAgent) -> tuple[PrintJob, PrintArtifact, str] | None:
        now = datetime.now(timezone.utc)
        query = (select(PrintJob).join(PrinterProfile, PrinterProfile.id == PrintJob.printer_profile_id).join(Printer, Printer.id == PrinterProfile.printer_id)
            .where(Printer.agent_id == agent.id, Printer.is_enabled.is_(True), Printer.status == "online", or_(PrintJob.status == "waiting_for_agent", (PrintJob.status == "claimed") & (PrintJob.lease_expires_at < now)))
            .order_by(PrintJob.created_at).with_for_update(skip_locked=True).limit(1))
        job = self.db.scalar(query)
        if not job:
            return None
        if job.status == "claimed":
            job.status = "waiting_for_agent"
        raw_token = secrets.token_urlsafe(32)
        job.claimed_by_agent_id = agent.id
        job.claimed_at = now
        job.lease_expires_at = now + timedelta(seconds=get_settings().agent_lease_seconds)
        job.claim_token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        job.attempt_count += 1
        job.last_attempt_at = now
        transition(self.db, job, "claimed", payload={"agent_id": str(agent.id), "attempt": job.attempt_count})
        artifact = self.db.scalar(select(PrintArtifact).where(PrintArtifact.print_job_id == job.id, PrintArtifact.artifact_type == "raw_tspl", PrintArtifact.status == "ready"))
        if not artifact:
            raise AgentJobError("ARTIFACT_NOT_READY", "The immutable raw artifact is unavailable.")
        agent.current_job_id = job.id
        return job, artifact, raw_token

    @staticmethod
    def authorize_claim(job: PrintJob, agent: PrintAgent, token: str) -> None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        if job.claimed_by_agent_id != agent.id or not job.claim_token_hash or not secrets.compare_digest(job.claim_token_hash, digest):
            raise AgentJobError("CLAIM_TOKEN_INVALID", "This agent does not own the job lease.")
        if job.status=="claimed" and job.lease_expires_at and job.lease_expires_at < datetime.now(timezone.utc):
            raise AgentJobError("CLAIM_LEASE_EXPIRED", "The pre-spool claim lease expired.")

    def report(self, job: PrintJob, agent: PrintAgent, claim_token: str, status: str, *, spool_job_id: str | None = None, error_code: str | None = None, error_message: str | None = None) -> PrintJob:
        self.authorize_claim(job, agent, claim_token)
        if status == "downloaded":
            transition(self.db, job, "downloaded", payload={"agent_id": str(agent.id)})
        elif status == "spooling":
            transition(self.db, job, "spooling", payload={"agent_id": str(agent.id)})
        elif status == "spooled":
            if job.status == "downloaded":
                transition(self.db, job, "spooling", payload={"agent_id": str(agent.id)})
            transition(self.db, job, "spooled", payload={"spool_job_id": spool_job_id})
            job.spool_job_id = spool_job_id
            agent.current_job_id = None
        elif status in {"transport_failed", "uncertain"}:
            transition(self.db, job, status, payload={"code": error_code, "message": error_message})
            job.transport_error_code, job.transport_error_message = error_code, error_message
            agent.last_error, agent.current_job_id = error_message or error_code, None
        else:
            raise AgentJobError("INVALID_TRANSPORT_STATUS", "Unsupported agent status report.")
        job.transport_status = status
        return job
