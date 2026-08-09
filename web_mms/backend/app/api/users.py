from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentPrincipal,current_principal,require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Role,User
from app.schemas import CurrentUserOut,UserWrite

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserOut)
def current_user(principal:CurrentPrincipal=Depends(current_principal)):
    return CurrentUserOut(id=principal.id,email=principal.email,display_name=principal.display_name,roles=sorted(principal.roles),development=principal.development)


@router.get("")
def list_users(_:CurrentPrincipal=Depends(require_roles("Admin")),db:Session=Depends(get_db)):
    return [{"id":str(user.id),"email":user.email,"display_name":user.display_name,"is_active":user.is_active,"roles":[role.name for role in user.roles]} for user in db.scalars(select(User).order_by(User.email)).all()]


@router.post("",status_code=201)
def create_user(payload:UserWrite,_:CurrentPrincipal=Depends(require_roles("Admin")),db:Session=Depends(get_db)):
    if len(payload.password)<12:raise HTTPException(422,detail={"code":"PASSWORD_TOO_SHORT"})
    if db.scalar(select(User).where(User.email==payload.email.casefold())):raise HTTPException(409,detail={"code":"USER_EXISTS"})
    roles=list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
    if len(roles)!=len(set(payload.roles)):raise HTTPException(422,detail={"code":"ROLE_INVALID"})
    user=User(email=payload.email.casefold(),display_name=payload.display_name,password_hash=hash_password(payload.password),is_active=True,roles=roles);db.add(user);db.commit();db.refresh(user)
    return {"id":str(user.id),"email":user.email,"roles":[role.name for role in user.roles]}


@router.put("/{user_id}")
def update_user(user_id:UUID,payload:UserWrite,_:CurrentPrincipal=Depends(require_roles("Admin")),db:Session=Depends(get_db)):
    user=db.get(User,user_id)
    if not user:raise HTTPException(404,detail={"code":"USER_NOT_FOUND"})
    roles=list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
    if len(roles)!=len(set(payload.roles)):raise HTTPException(422,detail={"code":"ROLE_INVALID"})
    user.display_name=payload.display_name;user.is_active=payload.is_active;user.roles=roles
    if payload.password:
        if len(payload.password)<12:raise HTTPException(422,detail={"code":"PASSWORD_TOO_SHORT"})
        user.password_hash=hash_password(payload.password)
    db.commit();return {"id":str(user.id),"is_active":user.is_active,"roles":[role.name for role in user.roles]}
