from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditEvent, ImportError
from app.schemas import ErrorOut, ErrorPage

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("", response_model=ErrorPage)
def list_errors(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), severity: str | None = None, marketplace: str | None = None, code: str | None = None, resolved: bool | None = None, db: Session = Depends(get_db)):
    filters = []
    if severity: filters.append(ImportError.severity == severity)
    if marketplace: filters.append(ImportError.marketplace == marketplace)
    if code: filters.append(ImportError.code == code)
    if resolved is not None: filters.append(ImportError.resolved == resolved)
    total = db.scalar(select(func.count()).select_from(ImportError).where(*filters)) or 0
    items = db.scalars(select(ImportError).where(*filters).order_by(ImportError.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ErrorPage(items=[ErrorOut.model_validate(item) for item in items], total=total, page=page, page_size=page_size)


@router.post("/{error_id}/resolve")
def resolve_error(error_id: UUID, db: Session = Depends(get_db)):
    item = db.get(ImportError, error_id)
    if not item: raise HTTPException(404, "Error not found")
    item.resolved = True
    db.add(AuditEvent(entity_type="import_error", entity_id=str(item.id), action="resolved", changes={"resolved": {"old": False, "new": True}}, context={}))
    db.commit()
    return {"status": "resolved"}
