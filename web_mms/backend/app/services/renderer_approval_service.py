from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, BarcodeVerification, Marketplace, PrintJob, PrintJobLine, PrinterProfile, RendererProfileApproval
from app.renderers import get_renderer
from app.renderers.font_registry import resolve_font


class RendererApprovalError(ValueError):
    pass


class RendererApprovalService:
    def __init__(self, db: Session): self.db = db

    def approve(self, profile: PrinterProfile, test_job: PrintJob, *, format_key: str | None, actor_id=None, notes: str | None = None):
        renderer = get_renderer(profile.renderer)
        if not test_job.is_test or test_job.is_simulation or test_job.printer_profile_id != profile.id or test_job.marketplace!=profile.marketplace or test_job.status != "completed":
            raise RendererApprovalError("A completed test print for this profile is required.")
        if (test_job.renderer_key,test_job.renderer_version,test_job.layout_version)!=(renderer.key,renderer.version,profile.layout_version):raise RendererApprovalError("The test job renderer/profile/layout identity does not match.")
        lines=list(self.db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id==test_job.id)).all())
        if profile.marketplace==Marketplace.FLIPKART:
            if not format_key:raise RendererApprovalError("Flipkart approval requires one exact format key.")
            lines=[line for line in lines if line.data_snapshot.get("format")==format_key]
        else:
            format_key=None
        if not lines:raise RendererApprovalError("The test job does not contain the requested representative format.")
        line_ids=[line.id for line in lines]
        if not self.db.scalar(select(BarcodeVerification.id).where(BarcodeVerification.print_job_id==test_job.id,BarcodeVerification.print_job_line_id.in_(line_ids),BarcodeVerification.passed.is_(True))):raise RendererApprovalError("A passing server-derived barcode scan for the representative line is required.")
        fingerprint=None
        if renderer.key=="flipkart_hybrid_tspl_v2":fingerprint=resolve_font(str((profile.config or {}).get("font_key") or "mms_default_sans"))["font_sha256"]
        row = RendererProfileApproval(printer_profile_id=profile.id, renderer_key=renderer.key, renderer_version=renderer.version,
            layout_version=profile.layout_version, format_key=format_key, marketplace=profile.marketplace, approved_by_id=actor_id, test_print_job_id=test_job.id, notes=notes,font_fingerprint=fingerprint)
        self.db.add(row)
        self.db.add(AuditEvent(actor_id=actor_id, entity_type="printer_profile", entity_id=str(profile.id), action="renderer_approved", changes={"renderer": renderer.key, "version": renderer.version, "layout_version": profile.layout_version, "format_key": format_key}))
        return row

    def revoke(self, approval: RendererProfileApproval, actor_id=None):
        approval.revoked_at = datetime.now(timezone.utc)
        self.db.add(AuditEvent(actor_id=actor_id, entity_type="renderer_approval", entity_id=str(approval.id), action="revoked", changes={}))

    def verify_barcode(self, job: PrintJob, expected: str, scanned: str, *, line_id=None, actor_id=None):
        row = BarcodeVerification(print_job_id=job.id, print_job_line_id=line_id, expected_value=expected, scanned_value=scanned, passed=expected == scanned, verified_by_id=actor_id)
        self.db.add(row)
        return row
