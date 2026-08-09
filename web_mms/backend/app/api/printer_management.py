from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentPrincipal,require_roles
from app.db.session import get_db
from app.models import AuditEvent, Marketplace, PrintAgent, PrintJob, Printer, PrinterProfile, RendererProfileApproval
from app.renderers import get_renderer
from app.renderers.base import RendererError
from app.renderers.font_registry import resolve_font
from app.schemas import PrinterProfileWrite, RendererApprovalWrite
from app.services.agent_auth_service import AgentAuthService
from app.services.renderer_approval_service import RendererApprovalError, RendererApprovalService

router = APIRouter(tags=["printer-management"])


@router.post("/print-agents/pairing-codes", status_code=201)
def pairing_code(principal:CurrentPrincipal=Depends(require_roles("Admin")),db: Session = Depends(get_db)):
    code, row = AgentAuthService(db).create_pairing_code(actor_id=principal.id); db.commit()
    return {"code": code, "expires_at": row.expires_at}


@router.get("/print-agents")
def agents(_:CurrentPrincipal=Depends(require_roles("Admin","QC")),db: Session = Depends(get_db)):
    return [{"id": str(row.id), "name": row.name, "machine_name": row.machine_name, "status": row.status, "last_seen_at": row.last_seen_at,
        "version": row.version, "windows_version": row.windows_version, "token_hint": row.token_hint, "last_error": row.last_error} for row in db.scalars(select(PrintAgent).order_by(PrintAgent.name)).all()]


@router.post("/print-agents/{agent_id}/revoke")
def revoke_agent(agent_id: UUID, principal:CurrentPrincipal=Depends(require_roles("Admin")),db: Session = Depends(get_db)):
    row = db.get(PrintAgent, agent_id)
    if not row: raise HTTPException(404, detail={"code": "PRINT_AGENT_NOT_FOUND"})
    AgentAuthService.revoke(row);db.add(AuditEvent(actor_id=principal.id,entity_type="print_agent",entity_id=str(row.id),action="revoked",changes={}));db.commit()
    return {"id": str(row.id), "status": row.status}


def _profile(row: PrinterProfile,db:Session):
    renderer=get_renderer(row.renderer);font_identity=None
    if renderer.key=="flipkart_hybrid_tspl_v2":
        try:font_identity=resolve_font(str((row.config or {}).get("font_key") or "mms_default_sans"))
        except RendererError as exc:font_identity={"font_key":(row.config or {}).get("font_key"),"error":exc.code}
    approvals=list(db.scalars(select(RendererProfileApproval).where(RendererProfileApproval.printer_profile_id==row.id,RendererProfileApproval.revoked_at.is_(None))).all())
    return {"id": str(row.id), "printer_id": str(row.printer_id), "marketplace": row.marketplace.value, "account_id": str(row.account_id) if row.account_id else None,
        "media_width_mm": row.media_width_mm, "media_height_mm": row.media_height_mm, "gap_mm": row.gap_mm, "speed": row.speed, "darkness": row.darkness,
        "renderer": row.renderer,"renderer_version":renderer.version,"layout_version": row.layout_version, "config": row.config,"font_identity":font_identity,
        "approvals":[{"id":str(item.id),"format_key":item.format_key,"renderer_version":item.renderer_version,"layout_version":item.layout_version,"font_fingerprint":item.font_fingerprint} for item in approvals]}


@router.get("/printers/{printer_id}/profiles")
def profiles(printer_id: UUID, _:CurrentPrincipal=Depends(require_roles("Admin","QC")),db: Session = Depends(get_db)):
    return [_profile(row,db) for row in db.scalars(select(PrinterProfile).where(PrinterProfile.printer_id == printer_id).order_by(PrinterProfile.marketplace)).all()]


@router.post("/printers/{printer_id}/profiles", status_code=201)
def create_profile(printer_id: UUID, payload: PrinterProfileWrite, principal:CurrentPrincipal=Depends(require_roles("Admin")),db: Session = Depends(get_db)):
    printer = db.get(Printer, printer_id)
    if not printer: raise HTTPException(404, detail={"code": "PRINTER_NOT_FOUND"})
    try: get_renderer(payload.renderer)
    except ValueError as exc: raise HTTPException(422, detail={"code": "RENDERER_NOT_FOUND", "message": str(exc)}) from exc
    values=payload.model_dump();values["marketplace"]=Marketplace(payload.marketplace.casefold())
    row = PrinterProfile(printer_id=printer.id, **values); db.add(row); printer.is_enabled = True;db.flush();db.add(AuditEvent(actor_id=principal.id,entity_type="printer_profile",entity_id=str(row.id),action="created",changes={"renderer":row.renderer,"layout_version":row.layout_version})); db.commit(); db.refresh(row)
    return _profile(row,db)


@router.put("/printer-profiles/{profile_id}")
def update_profile(profile_id: UUID, payload: PrinterProfileWrite, principal:CurrentPrincipal=Depends(require_roles("Admin")),db: Session = Depends(get_db)):
    row = db.get(PrinterProfile, profile_id)
    if not row: raise HTTPException(404, detail={"code": "PRINTER_PROFILE_NOT_FOUND"})
    get_renderer(payload.renderer); values=payload.model_dump();values["marketplace"]=Marketplace(payload.marketplace.casefold())
    for key, value in values.items(): setattr(row, key, value)
    row.layout_version += 1
    db.add(AuditEvent(actor_id=principal.id,entity_type="printer_profile", entity_id=str(row.id), action="updated", changes={"renderer":payload.renderer,"marketplace":payload.marketplace,"layout_version":row.layout_version}))
    db.commit(); return _profile(row,db)


@router.get("/printer-profiles/{profile_id}/approvals")
def approvals(profile_id: UUID, _:CurrentPrincipal=Depends(require_roles("Admin","QC")),db: Session = Depends(get_db)):
    return [{"id": str(row.id), "renderer_key": row.renderer_key, "renderer_version": row.renderer_version, "layout_version": row.layout_version,
        "format_key": row.format_key, "approved_at": row.approved_at, "revoked_at": row.revoked_at, "test_print_job_id": str(row.test_print_job_id)}
        for row in db.scalars(select(RendererProfileApproval).where(RendererProfileApproval.printer_profile_id == profile_id).order_by(RendererProfileApproval.approved_at.desc())).all()]


@router.post("/printer-profiles/{profile_id}/approvals", status_code=201)
def approve(profile_id: UUID, payload: RendererApprovalWrite, principal:CurrentPrincipal=Depends(require_roles("Admin","QC")),db: Session = Depends(get_db)):
    profile, job = db.get(PrinterProfile, profile_id), db.get(PrintJob, payload.test_print_job_id)
    if not profile or not job: raise HTTPException(404, detail={"code": "PROFILE_OR_TEST_JOB_NOT_FOUND"})
    try: row = RendererApprovalService(db).approve(profile, job, format_key=payload.format_key,actor_id=principal.id, notes=payload.notes); db.commit(); db.refresh(row)
    except RendererApprovalError as exc: raise HTTPException(422, detail={"code": "APPROVAL_PRECONDITION_FAILED", "message": str(exc)}) from exc
    return {"id": str(row.id), "renderer_key": row.renderer_key, "renderer_version": row.renderer_version, "layout_version": row.layout_version}


@router.post("/renderer-approvals/{approval_id}/revoke")
def revoke_approval(approval_id: UUID, principal:CurrentPrincipal=Depends(require_roles("Admin","QC")),db: Session = Depends(get_db)):
    row = db.get(RendererProfileApproval, approval_id)
    if not row: raise HTTPException(404, detail={"code": "APPROVAL_NOT_FOUND"})
    RendererApprovalService(db).revoke(row,actor_id=principal.id); db.commit(); return {"id": str(row.id), "revoked": True}
