from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import PrintAgent, Printer, PrintJob

router = APIRouter(prefix="/print-queue", tags=["print-queue"])

@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    return list(db.scalars(select(PrintJob).order_by(PrintJob.created_at.desc()).limit(100)).all())

@router.get("/printers")
def list_printers(db: Session = Depends(get_db)):
    rows = db.execute(select(Printer, PrintAgent).join(PrintAgent, PrintAgent.id == Printer.agent_id)).all()
    return [{"id": str(printer.id), "name": printer.name, "driver": printer.driver_name, "dpi": printer.dpi, "status": printer.status, "agent": agent.name, "machine": agent.machine_name, "last_seen_at": printer.last_seen_at} for printer, agent in rows]
