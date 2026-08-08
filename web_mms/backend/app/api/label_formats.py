from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import LabelFormatProfile, Marketplace
from app.schemas import LabelFormatWrite

router = APIRouter(prefix="/label-formats", tags=["label-formats"])


def output(row: LabelFormatProfile):
    return {"id": str(row.id), "account_id": str(row.account_id) if row.account_id else None, "key": row.key, "display_name": row.display_name,
        "marketplace": row.marketplace.value if row.marketplace else None, "generic_name": row.generic_name, "required_fields": row.required_fields,
        "field_order": row.field_order, "config": row.config, "is_active": row.is_active}


@router.get("")
def list_formats(account_id: UUID | None = None, marketplace: str | None = None, db: Session = Depends(get_db)):
    query = select(LabelFormatProfile)
    if account_id: query = query.where(or_(LabelFormatProfile.account_id == account_id, LabelFormatProfile.account_id.is_(None)))
    if marketplace: query = query.where(or_(LabelFormatProfile.marketplace == Marketplace(marketplace.casefold()), LabelFormatProfile.marketplace.is_(None)))
    return [output(row) for row in db.scalars(query.order_by(LabelFormatProfile.display_name)).all()]


def assign(row: LabelFormatProfile, payload: LabelFormatWrite):
    values = payload.model_dump(); values["marketplace"] = Marketplace(values["marketplace"].casefold()) if values["marketplace"] else None
    values["name"] = values["display_name"]
    for key, value in values.items(): setattr(row, key, value)


@router.post("", status_code=201)
def create_format(payload: LabelFormatWrite, db: Session = Depends(get_db)):
    row = LabelFormatProfile(name=payload.display_name, key=payload.key, display_name=payload.display_name, marketplace=None, config={})
    assign(row, payload); db.add(row); db.commit(); db.refresh(row); return output(row)


@router.patch("/{format_id}")
def patch_format(format_id: UUID, payload: LabelFormatWrite, db: Session = Depends(get_db)):
    row = db.get(LabelFormatProfile, format_id)
    if not row: raise HTTPException(404, detail={"code": "LABEL_FORMAT_NOT_FOUND", "message": "Label format not found."})
    assign(row, payload); db.commit(); return output(row)
