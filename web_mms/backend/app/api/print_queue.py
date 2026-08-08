from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Marketplace, PrintAgent, Printer, PrintJob, PrintJobEvent, PrintJobLine
from app.schemas import BarcodeVerificationWrite, PrintJobCreate, ReprintRequest
from app.services.print_compilation_service import PrintCompilationError, PrintCompilationService
from app.services.print_job_service import PrintJobService, PrintJobValidationError
from app.services.renderer_approval_service import RendererApprovalService
from app.services.print_state_service import InvalidPrintJobState, transition

router = APIRouter(prefix="/print-jobs", tags=["print-jobs"])
printers_router = APIRouter(prefix="/printers", tags=["printers"])


def _summary(job: PrintJob, db: Session):
    rows, labels = db.execute(select(func.count(PrintJobLine.id), func.coalesce(func.sum(PrintJobLine.label_count), 0)).where(PrintJobLine.print_job_id == job.id)).one()
    return {"id": str(job.id), "consignment_id": str(job.consignment_id) if job.consignment_id else None, "account_id": str(job.account_id),
        "marketplace": job.marketplace.value, "status": job.status, "printer_name": job.printer_name,
        "printer_profile_id": str(job.printer_profile_id) if job.printer_profile_id else None, "created_by_id": str(job.created_by_id) if job.created_by_id else None,
        "rows": rows, "labels": labels, "created_at": job.created_at, "updated_at": job.updated_at, "completed_at": job.completed_at, "simulation": job.is_simulation,
        "is_test": job.is_test, "renderer_key": job.renderer_key, "renderer_version": job.renderer_version, "layout_version": job.layout_version,
        "transport_status": job.transport_status, "spool_job_id": job.spool_job_id, "transport_error_code": job.transport_error_code, "transport_error_message": job.transport_error_message}


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


@router.post("/{job_id}/compile")
def compile_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    try: artifact = PrintCompilationService(db).compile(job); db.commit(); db.refresh(artifact)
    except PrintCompilationError as exc: db.commit(); raise HTTPException(422, detail={"code": exc.code, "message": exc.message, "diagnostics": exc.diagnostics}) from exc
    return {"artifact_id": str(artifact.id), "sha256": artifact.sha256, "byte_size": artifact.byte_size, "status": job.status}


@router.get("/{job_id}/preview")
def preview(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    try: data, diagnostics = PrintCompilationService(db).preview(job)
    except PrintCompilationError as exc: raise HTTPException(422, detail={"code": exc.code, "message": exc.message, "diagnostics": exc.diagnostics}) from exc
    return Response(data, media_type="image/png", headers={"X-Renderer-Diagnostics": str(diagnostics)[:1000]})


@router.get("/{job_id}/diagnostics")
def diagnostics(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    return PrintCompilationService(db).diagnostics(job)


@router.post("/{job_id}/verify-barcode", status_code=201)
def verify_barcode(job_id: UUID, payload: BarcodeVerificationWrite, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    row = RendererApprovalService(db).verify_barcode(job, payload.expected_value, payload.scanned_value, line_id=payload.print_job_line_id); db.commit(); db.refresh(row)
    return {"id": str(row.id), "passed": row.passed, "expected": row.expected_value, "scanned": row.scanned_value}


@router.post("/{job_id}/confirm-physical-output")
def confirm_physical_output(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(PrintJob, job_id)
    if not job: raise HTTPException(404, detail={"code": "PRINT_JOB_NOT_FOUND"})
    try: PrintJobService(db).confirm_physical_output(job); db.commit()
    except PrintJobValidationError as exc: raise HTTPException(422, detail={"code": exc.code, "message": exc.message}) from exc
    return {"id": str(job.id), "status": job.status, "signal": "operator_confirmed_physical_output"}


@router.post("/{job_id}/cancel")
def cancel(job_id: UUID, db: Session = Depends(get_db)):
    job=db.get(PrintJob,job_id)
    if not job: raise HTTPException(404,detail={"code":"PRINT_JOB_NOT_FOUND"})
    try: transition(db,job,"cancelled");db.commit()
    except InvalidPrintJobState as exc: raise HTTPException(409,detail={"code":"CANCELLATION_NOT_SAFE","message":"Cancellation is not guaranteed after agent claim or spooling."}) from exc
    return {"id":str(job.id),"status":job.status}


@printers_router.get("")
def list_printers(db: Session = Depends(get_db)):
    rows = db.execute(select(Printer, PrintAgent).join(PrintAgent, PrintAgent.id == Printer.agent_id)).all()
    return [{"id": str(printer.id), "name": printer.name, "driver": printer.driver_name, "port": printer.port_name, "dpi": printer.dpi, "status": printer.status,
        "enabled": printer.is_enabled, "default": printer.is_default, "network": printer.is_network, "agent_id": str(agent.id), "agent": agent.name,
        "agent_status": agent.status, "machine": agent.machine_name, "last_seen_at": printer.last_seen_at} for printer, agent in rows]
