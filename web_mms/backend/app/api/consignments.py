from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Consignment

router = APIRouter(prefix="/consignments", tags=["consignments"])

@router.get("")
def list_consignments(db: Session = Depends(get_db)):
    return list(db.scalars(select(Consignment).order_by(Consignment.created_at.desc()).limit(100)).all())
