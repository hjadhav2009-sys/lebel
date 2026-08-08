from app.models import PrintJob, PrintJobEvent

ALLOWED = {
    "draft":{"ready","cancelled"}, "ready":{"rendering","cancelled"},
    "rendering":{"artifact_ready","render_failed"}, "artifact_ready":{"waiting_for_agent","cancelled"},
    "waiting_for_agent":{"claimed","cancelled"}, "claimed":{"downloaded","waiting_for_agent","transport_failed","uncertain"},
    "downloaded":{"spooling","transport_failed","uncertain"}, "spooling":{"spooled","transport_failed","uncertain"}, "spooled":{"completed","uncertain"},
    "partially_completed":{"completed","cancelled"},
}


class InvalidPrintJobState(ValueError): pass


def transition(db, job: PrintJob, target: str, *, actor_id=None, payload: dict | None=None):
    if target not in ALLOWED.get(job.status,set()):
        raise InvalidPrintJobState("INVALID_PRINT_JOB_STATE")
    previous=job.status; job.status=target
    db.add(PrintJobEvent(print_job_id=job.id,event_type=target,actor_id=actor_id,payload={"from":previous,**(payload or {})}))
    return job
