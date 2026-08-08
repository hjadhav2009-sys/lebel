from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Marketplace, MarketplaceAccount
from app.schemas import AccountCreate, MarketplaceAccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[MarketplaceAccountOut])
def list_accounts(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = select(MarketplaceAccount).order_by(MarketplaceAccount.marketplace, MarketplaceAccount.name)
    if not include_inactive:
        query = query.where(MarketplaceAccount.is_active.is_(True))
    return list(db.scalars(query).all())


@router.post("", response_model=MarketplaceAccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    try:
        marketplace = Marketplace(payload.marketplace.casefold())
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "invalid_marketplace", "message": "Unsupported marketplace", "details": {}}) from exc
    account = MarketplaceAccount(marketplace=marketplace, name=payload.name, external_id=payload.external_id, default_address_profile_id=payload.default_address_profile_id, is_active=payload.is_active)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
