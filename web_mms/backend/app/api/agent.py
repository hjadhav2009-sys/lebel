from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import PrintAgent, PrintArtifact, Printer, PrintJob
from app.schemas import AgentHeartbeat, AgentJobReport, AgentPairRequest, PrinterSync
from app.services.agent_auth_service import AgentAuthenticationError, AgentAuthService
from app.services.agent_job_service import AgentJobError, AgentJobService
from app.services.artifact_store import FileSystemPrintArtifactStore

router = APIRouter(prefix="/agent/v1", tags=["print-agent"])


def current_agent(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> PrintAgent:
    token = authorization.removeprefix("Bearer ").strip() if authorization and authorization.startswith("Bearer ") else ""
    try:
        return AgentAuthService(db).authenticate(token)
    except AgentAuthenticationError as exc:
        raise HTTPException(401, detail={"code": str(exc), "message": "Agent authentication failed."}) from exc


@router.post("/pair", status_code=201)
def pair(payload: AgentPairRequest, db: Session = Depends(get_db)):
    try:
        agent, token = AgentAuthService(db).pair(payload.code, machine_name=payload.machine_name, name=payload.name, version=payload.version)
        db.commit(); db.refresh(agent)
    except AgentAuthenticationError as exc:
        db.rollback(); raise HTTPException(422, detail={"code": str(exc), "message": "Pairing failed."}) from exc
    return {"agent_id": str(agent.id), "token": token, "token_hint": agent.token_hint}


@router.post("/heartbeat")
def heartbeat(payload: AgentHeartbeat, agent: PrintAgent = Depends(current_agent), db: Session = Depends(get_db)):
    agent.status, agent.last_seen_at = "online", datetime.now(timezone.utc)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(agent, key, value)
    db.commit()
    return {"agent_id": str(agent.id), "status": agent.status, "transport_enabled": get_settings().print_transport_enabled}


@router.put("/printers")
@router.post("/printers/sync")
def sync_printers(payload: PrinterSync, agent: PrintAgent = Depends(current_agent), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc); seen = set()
    for item in payload.printers:
        seen.add(item.name)
        row = db.scalar(select(Printer).where(Printer.agent_id == agent.id, Printer.name == item.name)) or Printer(agent_id=agent.id, name=item.name, is_enabled=False)
        for key, value in item.model_dump().items(): setattr(row, key, value)
        row.last_seen_at = now; db.add(row)
    for row in db.scalars(select(Printer).where(Printer.agent_id == agent.id, Printer.name.not_in(seen))).all(): row.status = "offline"
    db.commit()
    return {"count": len(seen)}


@router.post("/jobs/claim")
def claim(agent: PrintAgent = Depends(current_agent), db: Session = Depends(get_db)):
    if not get_settings().print_transport_enabled:
        raise HTTPException(503, detail={"code": "PRINT_TRANSPORT_DISABLED", "message": "Real printer transport is disabled."})
    try: result = AgentJobService(db).claim(agent)
    except AgentJobError as exc: raise HTTPException(409, detail={"code": exc.code, "message": exc.message}) from exc
    if not result: return Response(status_code=204)
    job, artifact, token = result; db.commit()
    return {"job_id": str(job.id), "artifact_id": str(artifact.id), "sha256": artifact.sha256, "byte_size": artifact.byte_size,
        "printer_name": job.printer_name, "claim_token": token, "idempotency_key": job.idempotency_key, "lease_expires_at": job.lease_expires_at}


@router.get("/jobs/{job_id}/artifact")
def artifact(job_id: UUID, claim_token: str = Header(alias="X-Claim-Token"), agent: PrintAgent = Depends(current_agent), db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    try: AgentJobService.authorize_claim(job, agent, claim_token)
    except AgentJobError as exc: raise HTTPException(403, detail={"code": exc.code, "message": exc.message}) from exc
    row = db.scalar(select(PrintArtifact).where(PrintArtifact.print_job_id == job.id, PrintArtifact.artifact_type == "raw_tspl", PrintArtifact.status == "ready"))
    if not row: raise HTTPException(404, detail={"code": "ARTIFACT_NOT_FOUND"})
    store = FileSystemPrintArtifactStore(get_settings().print_artifact_root)
    with store.open(row.storage_key) as source: data = source.read()
    return Response(data, media_type="application/octet-stream", headers={"X-Artifact-SHA256": row.sha256, "Cache-Control":"no-store", "Content-Disposition": f'attachment; filename="{job.id}.tspl"'})


@router.post("/jobs/{job_id}/report")
@router.post("/jobs/{job_id}/status")
def report(job_id: UUID, payload: AgentJobReport, agent: PrintAgent = Depends(current_agent), db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    try: AgentJobService(db).report(job, agent, payload.claim_token, payload.status, spool_job_id=payload.spool_job_id, error_code=payload.error_code, error_message=payload.error_message); db.commit()
    except AgentJobError as exc: db.rollback(); raise HTTPException(409, detail={"code": exc.code, "message": exc.message}) from exc
    return {"job_id": str(job.id), "status": job.status}
