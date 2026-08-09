import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (PrintArtifact, PrintJob, PrintJobLine, Printer,
    PrinterProfile, RendererProfileApproval)
from app.renderers import get_renderer
from app.renderers.base import RendererError
from app.renderers.font_registry import resolve_font
from app.services.artifact_store import FileSystemPrintArtifactStore
from app.services.print_state_service import transition


class PrintCompilationError(ValueError):
    def __init__(self,code:str,message:str,diagnostics:dict|None=None):self.code,self.message,self.diagnostics=code,message,diagnostics or {}


class PrintCompilationService:
    def __init__(self,db:Session,store=None):
        self.db=db; self.settings=get_settings(); self.store=store or FileSystemPrintArtifactStore(Path(self.settings.print_artifact_root))

    @staticmethod
    def _profile(profile:PrinterProfile,printer:Printer)->dict:
        return {"id":str(profile.id),"dpi":printer.dpi,"media_width_mm":str(profile.media_width_mm),"media_height_mm":str(profile.media_height_mm),
            "gap_mm":str(profile.gap_mm or 0),"renderer":profile.renderer,"layout_version":profile.layout_version,"config":profile.config or {}}

    def _approved(self,job:PrintJob,profile:PrinterProfile,renderer,formats:set[str])->bool:
        if job.is_test and self.settings.allow_unapproved_test_prints:return True
        approvals=self.db.scalars(select(RendererProfileApproval).where(RendererProfileApproval.printer_profile_id==profile.id,
            RendererProfileApproval.renderer_key==renderer.key,RendererProfileApproval.renderer_version==renderer.version,
            RendererProfileApproval.layout_version==profile.layout_version,RendererProfileApproval.revoked_at.is_(None))).all()
        if renderer.key=="flipkart_hybrid_tspl_v2":
            fingerprint=resolve_font(str((profile.config or {}).get("font_key") or "mms_default_sans"))["font_sha256"]
            approvals=[row for row in approvals if row.font_fingerprint==fingerprint]
        approved={row.format_key for row in approvals}
        return all(value in approved or None in approved for value in formats)

    def compile(self,job:PrintJob,actor_id=None)->PrintArtifact:
        job=self.db.scalar(select(PrintJob).where(PrintJob.id==job.id).with_for_update()) or job
        if not job.printer_profile_id:raise PrintCompilationError("MISSING_PRINTER_PROFILE","Choose a printer profile.")
        profile=self.db.get(PrinterProfile,job.printer_profile_id); printer=self.db.get(Printer,profile.printer_id) if profile else None
        if not profile or not printer:raise PrintCompilationError("MISSING_PRINTER_PROFILE","Printer profile is unavailable.")
        if profile.marketplace!=job.marketplace or profile.account_id not in {None,job.account_id}:raise PrintCompilationError("INVALID_PRINTER_PROFILE","Profile scope does not match the job.")
        if int(profile.config.get("approved_dpi",printer.dpi))!=printer.dpi:raise PrintCompilationError("PRINTER_DPI_MISMATCH","Printer and approved profile DPI differ.")
        try: renderer=get_renderer(profile.renderer)
        except ValueError as exc: raise PrintCompilationError("HISTORICAL_RENDERER_UNAVAILABLE","The required renderer is not installed.") from exc
        if job.renderer_key and (job.renderer_key!=renderer.key or job.renderer_version!=renderer.version or job.layout_version!=profile.layout_version):
            raise PrintCompilationError("HISTORICAL_RENDERER_UNAVAILABLE","Exact reprint requires its original renderer and layout version.")
        lines=list(self.db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id==job.id).order_by(PrintJobLine.id)).all())
        if sum(line.label_count for line in lines)>self.settings.max_labels_per_job: raise PrintCompilationError("PRINT_JOB_TOO_LARGE","Job exceeds the configured label limit.")
        snapshots=[line.data_snapshot for line in lines]; formats={str(item.get("format") or "") for item in snapshots}
        if not self._approved(job,profile,renderer,formats):raise PrintCompilationError("RENDERER_PROFILE_NOT_APPROVED","Renderer/profile/layout approval is required for bulk print.")
        existing=self.db.scalar(select(PrintArtifact).where(PrintArtifact.print_job_id==job.id,PrintArtifact.artifact_type=="raw_tspl",
            PrintArtifact.renderer_key==renderer.key,PrintArtifact.renderer_version==renderer.version,PrintArtifact.layout_version==profile.layout_version,
            PrintArtifact.printer_profile_id==profile.id,PrintArtifact.status=="ready"))
        if existing and self.store.exists(existing.storage_key):return existing
        if job.status=="ready":transition(self.db,job,"rendering",actor_id=actor_id)
        elif job.status!="rendering":raise PrintCompilationError("INVALID_PRINT_JOB_STATE","Job is not ready for compilation.")
        try: result=renderer.render(snapshots,self._profile(profile,printer))
        except RendererError as exc:
            transition(self.db,job,"render_failed",actor_id=actor_id,payload={"code":exc.code,"diagnostics":exc.diagnostics});self.db.flush()
            raise PrintCompilationError(exc.code,exc.message,exc.diagnostics) from exc
        if len(result.raw_bytes)>self.settings.max_print_artifact_bytes:raise PrintCompilationError("ARTIFACT_TOO_LARGE","Raw print artifact exceeds the configured limit.")
        digest=hashlib.sha256(result.raw_bytes).hexdigest(); key=f"{job.id}/{renderer.key}-layout-{profile.layout_version}-{digest[:16]}.tspl"
        if self.store.save(key,result.raw_bytes)!=digest:raise PrintCompilationError("ARTIFACT_HASH_MISMATCH","Stored artifact failed integrity verification.")
        artifact=PrintArtifact(print_job_id=job.id,artifact_type=result.artifact_type,renderer_key=renderer.key,renderer_version=renderer.version,
            layout_version=profile.layout_version,printer_profile_id=profile.id,sha256=digest,byte_size=len(result.raw_bytes),storage_key=key,
            content_type=result.content_type,encoding="binary",status="ready",created_by_id=actor_id,metadata_=result.diagnostics)
        self.db.add(artifact);job.renderer_key=renderer.key;job.renderer_version=renderer.version;job.layout_version=profile.layout_version
        job.printer_name=printer.name;job.idempotency_key=hashlib.sha256(f"{job.id}:{digest}".encode()).hexdigest()
        transition(self.db,job,"artifact_ready",actor_id=actor_id,payload={"sha256":digest,"artifact_type":result.artifact_type});transition(self.db,job,"waiting_for_agent",actor_id=actor_id)
        return artifact

    def preview(self,job:PrintJob)->tuple[bytes,dict]:
        if not job.printer_profile_id:raise PrintCompilationError("MISSING_PRINTER_PROFILE","Choose a printer profile.")
        profile=self.db.get(PrinterProfile,job.printer_profile_id);printer=self.db.get(Printer,profile.printer_id) if profile else None
        if not profile or not printer:raise PrintCompilationError("MISSING_PRINTER_PROFILE","Printer profile is unavailable.")
        snapshots=list(self.db.scalars(select(PrintJobLine.data_snapshot).where(PrintJobLine.print_job_id==job.id).order_by(PrintJobLine.id)).all())
        result=get_renderer(profile.renderer).preview(snapshots,self._profile(profile,printer))
        if len(result.png_bytes)>self.settings.max_preview_bytes:raise PrintCompilationError("PREVIEW_TOO_LARGE","Preview exceeds the configured limit.")
        return result.png_bytes,result.diagnostics

    def diagnostics(self,job:PrintJob)->dict:
        artifact=self.db.scalar(select(PrintArtifact).where(PrintArtifact.print_job_id==job.id,PrintArtifact.artifact_type=="raw_tspl").order_by(PrintArtifact.created_at.desc()))
        return {"job_id":str(job.id),"renderer_key":job.renderer_key,"renderer_version":job.renderer_version,"layout_version":job.layout_version,
            "status":job.status,"artifact":None if not artifact else {"id":str(artifact.id),"sha256":artifact.sha256,"byte_size":artifact.byte_size,"metadata":artifact.metadata_}}
