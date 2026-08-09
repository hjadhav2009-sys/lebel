from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentPrincipal,current_principal
from app.core.config import get_settings
from app.core.security import create_access_token,hash_password,verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest,PasswordChangeRequest

router=APIRouter(prefix="/auth",tags=["auth"])


def _out(principal:CurrentPrincipal):return {"id":principal.id,"email":principal.email,"display_name":principal.display_name,"roles":sorted(principal.roles),"development":principal.development}


@router.post("/login")
def login(payload:LoginRequest,response:Response,db:Session=Depends(get_db)):
    settings=get_settings()
    if settings.auth_mode!="local":raise HTTPException(409,detail={"code":"LOCAL_AUTH_DISABLED","message":"Local login is not active."})
    user=db.scalar(select(User).where(User.email==payload.email.strip().casefold()))
    if not user or not user.is_active or not user.password_hash or not verify_password(payload.password,user.password_hash):
        raise HTTPException(401,detail={"code":"INVALID_CREDENTIALS","message":"Email or password is incorrect."})
    token=create_access_token(str(user.id),settings.auth_session_minutes)
    response.set_cookie("mms_session",token,httponly=True,secure=settings.auth_cookie_secure,samesite="strict",max_age=settings.auth_session_minutes*60,path="/")
    return {"id":str(user.id),"email":user.email,"display_name":user.display_name,"roles":[role.name for role in user.roles],"development":False}


@router.post("/logout")
def logout(response:Response):response.delete_cookie("mms_session",path="/");return {"logged_out":True}


@router.get("/me")
def me(principal:CurrentPrincipal=Depends(current_principal)):return _out(principal)


@router.post("/change-password")
def change_password(payload:PasswordChangeRequest,principal:CurrentPrincipal=Depends(current_principal),db:Session=Depends(get_db)):
    if principal.development or not principal.id:raise HTTPException(409,detail={"code":"PASSWORD_CHANGE_UNAVAILABLE"})
    user=db.get(User,principal.id)
    if not user or not user.password_hash or not verify_password(payload.current_password,user.password_hash):raise HTTPException(422,detail={"code":"CURRENT_PASSWORD_INVALID"})
    user.password_hash=hash_password(payload.new_password);db.commit();return {"changed":True}
