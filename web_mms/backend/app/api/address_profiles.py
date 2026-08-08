from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AddressProfile, MarketplaceAccount
from app.schemas import AddressProfileWrite

router = APIRouter(prefix="/address-profiles", tags=["address-profiles"])


def output(row: AddressProfile):
    return {"id": str(row.id), "account_id": str(row.account_id), "name": row.name, "marketed_by": row.marketed_by,
        "address_line_1": row.address_line_1, "address_line_2": row.address_line_2, "city_state": row.city_state,
        "email": row.email, "phone": row.phone, "origin": row.origin, "is_active": row.is_active, "is_default": row.is_default}


@router.get("")
def list_profiles(account_id: UUID | None = None, include_inactive: bool = False, db: Session = Depends(get_db)):
    query = select(AddressProfile)
    if account_id: query = query.where(AddressProfile.account_id == account_id)
    if not include_inactive: query = query.where(AddressProfile.is_active.is_(True))
    return [output(row) for row in db.scalars(query.order_by(AddressProfile.name)).all()]


def save_default(db: Session, row: AddressProfile):
    if row.is_default:
        db.execute(update(AddressProfile).where(AddressProfile.account_id == row.account_id, AddressProfile.id != row.id).values(is_default=False))
        account = db.get(MarketplaceAccount, row.account_id)
        if account: account.default_address_profile_id = row.id


@router.post("", status_code=201)
def create_profile(payload: AddressProfileWrite, db: Session = Depends(get_db)):
    if not db.get(MarketplaceAccount, payload.account_id): raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found."})
    row = AddressProfile(**payload.model_dump(), config={}); db.add(row); db.flush(); save_default(db, row); db.commit(); db.refresh(row); return output(row)


@router.patch("/{profile_id}")
def patch_profile(profile_id: UUID, payload: AddressProfileWrite, db: Session = Depends(get_db)):
    row = db.get(AddressProfile, profile_id)
    if not row: raise HTTPException(404, detail={"code": "ADDRESS_PROFILE_NOT_FOUND", "message": "Address profile not found."})
    if row.account_id != payload.account_id: raise HTTPException(422, detail={"code": "ADDRESS_ACCOUNT_IMMUTABLE", "message": "Address profiles cannot move between accounts."})
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    save_default(db, row); db.commit(); return output(row)
