from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Marketplace, PrintAgent, Printer, PrintJob, PrintJobEvent, PrintJobLine
from app.schemas import PrintJobCreate, ReprintRequest
from app.services.print_job_service import PrintJobService, PrintJobValidationError

router = APIRouter(prefix="/print-jobs", tags=["print-jobs"])
printers_router = APIRouter(prefix="/printers", tags=["printers"])


def _summary(job: PrintJob, db: Session):
    rows, labels = db.execute(select(func.count(PrintJobLine.id), func.coalesce(func.sum(PrintJobLine.label_count), 0)).where(PrintJobLine.print_job_id == job.id)).one()
    return {"id": str(job.id), "consignment_id": str(job.consignment_id) if job.consignment_id else None, "account_id": str(job.account_id),
        "marketplace": job.marketplace.value, "status": job.status, "printer_name": job.printer_name,
        "printer_profile_id": str(job.printer_profile_id) if job.printer_profile_id else None, "created_by_id": str(job.created_by_id) if job.created_by_id else None,
        "rows": rows, "labels": labels, "created_at": job.created_at, "updated_at": job.updated_at, "completed_at": job.completed_at, "simulation": job.is_simulation}


@router.post("", status_code=201)
def create_job(payload: PrintJobCreate, db: Session = Depends(get_db)):
    try: job = PrintJobService(db).prepare(payload.consignment_id, printer_profile_id=payload.printer_profile_id, line_ids=payload.line_ids, test_labels=payload.test_labels); db.commit(); db.refresh(job)
    except PrintJobValidationError as exc: raise HTTPException(422, detail={"code": exc.code, "message": exc.message}) from exc
    return _summary(job, db)


@router.get("")
def list_jobs(status: str | None = None, marketplace: str | None = None, account_id: UUID | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    query = select(PrintJob)
    if status: query = query.where(PrintJob.status == status)
    if marketplace: query = query.where(PrintJob.marketplace == Marketplace(marketplace.casefold()))
    if account_id: query = query.where(PrintJob.account_id == account_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(db.scalars(query.order_by(PrintJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all())
    return {"items": [_summary(row, db) for row in rows], "total": total, "page": page, "page_size": page_size, "page_count": ceil(total / page_size) if total else 0,
        "simulation_enabled": get_settings().enable_print_simulation}


@router.get("/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND", "message": "Print job not found."})
    lines = list(db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id == job.id).order_by(PrintJobLine.id)).all())
    events = list(db.scalars(select(PrintJobEvent).where(PrintJobEvent.print_job_id == job.id).order_by(PrintJobEvent.created_at)).all())
    return {**_summary(job, db), "simulation_enabled": get_settings().enable_print_simulation, "lines": [{"id": str(line.id), "consignment_line_id": str(line.consignment_line_id) if line.consignment_line_id else None, "copies": line.label_count, "status": line.status, "result": line.result, "snapshot": line.data_snapshot} for line in lines],
        "events": [{"id": str(event.id), "type": event.event_type, "created_at": event.created_at, "payload": event.payload} for event in events]}


@router.post("/{job_id}/simulate-success")
def simulate_success(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND", "message": "Print job not found."})
    try: PrintJobService(db).simulate_success(job, enabled=get_settings().enable_print_simulation, is_admin=True); db.commit()
    except PrintJobValidationError as exc: raise HTTPException(403, detail={"code": exc.code, "message": exc.message}) from exc
    return {"id": str(job.id), "status": job.status, "simulation": True}


@router.post("/{job_id}/reprint", status_code=201)
def reprint(job_id: UUID, payload: ReprintRequest, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND", "message": "Print job not found."})
    try: replacement = PrintJobService(db).reprint_exact(job, source_line_ids=payload.source_line_ids); db.commit(); db.refresh(replacement)
    except PrintJobValidationError as exc: raise HTTPException(422, detail={"code": exc.code, "message": exc.message}) from exc
    return _summary(replacement, db)


@printers_router.get("")
def list_printers(db: Session = Depends(get_db)):
    rows = db.execute(select(Printer, PrintAgent).join(PrintAgent, PrintAgent.id == Printer.agent_id)).all()
    return [{"id": str(printer.id), "name": printer.name, "driver": printer.driver_name, "dpi": printer.dpi, "status": printer.status, "agent": agent.name, "machine": agent.machine_name, "last_seen_at": printer.last_seen_at} for printer, agent in rows]
