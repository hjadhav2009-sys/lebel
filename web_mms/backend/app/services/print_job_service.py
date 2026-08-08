from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import ConsignmentIssue, ConsignmentLine, PrintJob, PrintJobEvent, PrintJobLine
from app.services.label_data_service import ConsignmentLabelDataService


class PrintJobValidationError(ValueError):
    def __init__(self, code: str, message: str): self.code, self.message = code, message


class PrintJobService:
    def __init__(self, db: Session): self.db = db

    def prepare(self, consignment_id, actor_id=None, printer_profile_id=None, line_ids=None, test_labels: bool = False) -> PrintJob:
        query = select(ConsignmentLine).where(ConsignmentLine.consignment_id == consignment_id,
            ConsignmentLine.selected_for_print.is_(True), ConsignmentLine.workflow_state == "to_print")
        if line_ids: query = query.where(ConsignmentLine.id.in_(line_ids))
        lines = list(self.db.scalars(query.options(selectinload(ConsignmentLine.product), selectinload(ConsignmentLine.consignment))).all())
        if not lines: raise PrintJobValidationError("NO_PRINTABLE_LINES", "Select at least one To Print row.")
        blocked = set(self.db.scalars(select(ConsignmentIssue.consignment_line_id).where(
            ConsignmentIssue.consignment_line_id.in_([line.id for line in lines]), ConsignmentIssue.severity == "blocking", ConsignmentIssue.resolved.is_(False))).all())
        if blocked: raise PrintJobValidationError("BLOCKING_CONSIGNMENT_ERRORS", "Resolve blocking line errors before preparing a job.")
        if any(line.print_quantity <= 0 for line in lines): raise PrintJobValidationError("INVALID_PRINT_QTY", "Print quantity must be positive.")
        consignment = lines[0].consignment
        job = PrintJob(consignment_id=consignment.id, account_id=consignment.account_id, marketplace=consignment.marketplace,
            status="ready", printer_profile_id=printer_profile_id, created_by_id=actor_id, is_test=test_labels)
        self.db.add(job); self.db.flush()
        resolver = ConsignmentLabelDataService(self.db)
        for line in lines:
            count = min(line.print_quantity, 2) if test_labels else line.print_quantity
            snapshot = resolver.snapshot(line); snapshot["print_quantity"] = count
            self.db.add(PrintJobLine(print_job_id=job.id, consignment_line_id=line.id, label_count=count, data_snapshot=deepcopy(snapshot), status="ready"))
        self.db.add(PrintJobEvent(print_job_id=job.id, event_type="created", actor_id=actor_id, payload={"test_job": test_labels}))
        self.db.add(PrintJobEvent(print_job_id=job.id, event_type="validated", actor_id=actor_id, payload={"line_count": len(lines)}))
        return job

    def simulate_success(self, job: PrintJob, actor_id=None, *, enabled: bool, is_admin: bool) -> PrintJob:
        if not enabled or not is_admin: raise PrintJobValidationError("PRINT_SIMULATION_DISABLED", "Print simulation is disabled.")
        if job.status not in {"ready", "waiting_for_agent"}: raise PrintJobValidationError("INVALID_PRINT_JOB_STATE", "Only prepared jobs can be simulated.")
        now = datetime.now(timezone.utc); job.status, job.completed_at, job.is_simulation = "completed", now, True
        lines = list(self.db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id == job.id)).all())
        for job_line in lines:
            job_line.status, job_line.result, job_line.completed_at = "completed", "success", now
            if job_line.consignment_line_id:
                source = self.db.get(ConsignmentLine, job_line.consignment_line_id)
                if source:
                    source.workflow_state, source.last_printed_at = "printed", now
                    source.successful_print_count += 1; source.selected_for_print = False
        self.db.add(PrintJobEvent(print_job_id=job.id, event_type="simulation", actor_id=actor_id, payload={"marker": "SIMULATION"}))
        self.db.add(PrintJobEvent(print_job_id=job.id, event_type="completed", actor_id=actor_id, payload={"result": "success"}))
        return job

    def reprint_exact(self, job: PrintJob, actor_id=None, source_line_ids=None) -> PrintJob:
        sources = list(self.db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id == job.id, PrintJobLine.result == "success")).all())
        if source_line_ids: sources = [line for line in sources if line.id in source_line_ids]
        if not sources: raise PrintJobValidationError("NO_SUCCESSFUL_LINES", "Choose successful historical lines to reprint.")
        replacement = PrintJob(consignment_id=job.consignment_id, account_id=job.account_id, marketplace=job.marketplace,
            status="ready", printer_profile_id=job.printer_profile_id, renderer_key=job.renderer_key, renderer_version=job.renderer_version,
            layout_version=job.layout_version, created_by_id=actor_id)
        self.db.add(replacement); self.db.flush()
        for line in sources:
            self.db.add(PrintJobLine(print_job_id=replacement.id, consignment_line_id=line.consignment_line_id,
                label_count=line.label_count, data_snapshot=deepcopy(line.data_snapshot), status="ready", source_print_job_line_id=line.id))
        self.db.add(PrintJobEvent(print_job_id=replacement.id, event_type="created", actor_id=actor_id, payload={"reprint_of": str(job.id), "mode": "exact_snapshot"}))
        return replacement

    def confirm_physical_output(self, job: PrintJob, actor_id=None) -> PrintJob:
        if job.status != "spooled": raise PrintJobValidationError("INVALID_PRINT_JOB_STATE", "Only a spooled job can be physically confirmed.")
        now=datetime.now(timezone.utc); job.status="completed"; job.completed_at=now
        for job_line in self.db.scalars(select(PrintJobLine).where(PrintJobLine.print_job_id==job.id)).all():
            job_line.status,job_line.result,job_line.completed_at="completed","success",now
            if job_line.consignment_line_id:
                source=self.db.get(ConsignmentLine,job_line.consignment_line_id)
                if source: source.workflow_state,source.last_printed_at,source.selected_for_print="printed",now,False;source.successful_print_count+=1
        self.db.add(PrintJobEvent(print_job_id=job.id,event_type="completed",actor_id=actor_id,payload={"signal":"operator_confirmed_physical_output"}))
        return job
