from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends,HTTPException,Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User


@dataclass(frozen=True)
class CurrentPrincipal:
    id: UUID|None
    email: str
    display_name: str
    roles: frozenset[str]
    development: bool=False


def current_principal(request:Request,db:Session=Depends(get_db))->CurrentPrincipal:
    settings=get_settings()
    if settings.auth_mode=="development":return CurrentPrincipal(None,"developer@localhost","Development User",frozenset({"Admin"}),True)
    if settings.auth_mode!="local":raise HTTPException(503,detail={"code":"AUTH_MODE_INVALID","message":"Unsupported authentication mode."})
    subject=decode_access_token(request.cookies.get("mms_session",""))
    try:user=db.get(User,UUID(subject)) if subject else None
    except ValueError:user=None
    if not user or not user.is_active:raise HTTPException(401,detail={"code":"AUTHENTICATION_REQUIRED","message":"Sign in with an active account."})
    return CurrentPrincipal(user.id,user.email,user.display_name,frozenset(role.name for role in user.roles))


def require_roles(*allowed:str):
    def dependency(principal:CurrentPrincipal=Depends(current_principal))->CurrentPrincipal:
        if not principal.roles.intersection(allowed):raise HTTPException(403,detail={"code":"ACCESS_DENIED","message":"Your role cannot perform this action."})
        return principal
    return dependency
