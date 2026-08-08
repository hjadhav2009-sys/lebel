from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, BarcodeVerification, PrintJob, PrinterProfile, RendererProfileApproval
from app.renderers import get_renderer


class RendererApprovalError(ValueError):
    pass


class RendererApprovalService:
    def __init__(self, db: Session): self.db = db

    def approve(self, profile: PrinterProfile, test_job: PrintJob, *, format_key: str | None, actor_id=None, notes: str | None = None):
        renderer = get_renderer(profile.renderer)
        if not test_job.is_test or test_job.printer_profile_id != profile.id or test_job.status != "completed":
            raise RendererApprovalError("A completed test print for this profile is required.")
        if not self.db.scalar(select(BarcodeVerification.id).where(BarcodeVerification.print_job_id==test_job.id,BarcodeVerification.passed.is_(True))):
            raise RendererApprovalError("A passing barcode scan for the test print is required.")
        row = RendererProfileApproval(printer_profile_id=profile.id, renderer_key=renderer.key, renderer_version=renderer.version,
            layout_version=profile.layout_version, format_key=format_key, marketplace=profile.marketplace, approved_by_id=actor_id, test_print_job_id=test_job.id, notes=notes)
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
