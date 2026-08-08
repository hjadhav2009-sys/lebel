import hashlib

import pytest

from mms_print_agent.spooler import FakeSpooler, SpoolError
from mms_print_agent.worker import IntegrityError, PrintWorker


class FakeApi:
    def __init__(self, data=b"SIZE 100 mm,50 mm\r\nPRINT 1\r\n"): self.data, self.reports = data, []
    def download(self, job_id, token): return self.data
    def report(self, job_id, payload): self.reports.append(payload); return {}


def claim(data: bytes):
    return {"job_id": "job-1", "claim_token": "claim", "printer_name": "TSC TE244", "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def test_exact_bytes_are_written_once():
    api, spooler = FakeApi(), FakeSpooler()
    assert PrintWorker(api, spooler, transport_allowed=True).process(claim(api.data)) == "spooled"
    assert spooler.writes == [("TSC TE244", api.data, "MMS job-1")]
    assert [r["status"] for r in api.reports] == ["downloaded", "spooling", "spooled"]


def test_hash_mismatch_never_spools():
    api, spooler = FakeApi(), FakeSpooler()
    bad = claim(api.data); bad["sha256"] = "0" * 64
    with pytest.raises(IntegrityError): PrintWorker(api, spooler, transport_allowed=True).process(bad)
    assert spooler.writes == []
    assert api.reports[-1]["error_code"] == "ARTIFACT_INTEGRITY_FAILED"


def test_unknown_spool_outcome_is_not_retried_as_safe_failure():
    api, spooler = FakeApi(), FakeSpooler(fail=SpoolError("connection dropped after StartDoc", uncertain=True))
    assert PrintWorker(api, spooler, transport_allowed=True).process(claim(api.data)) == "uncertain"
    assert api.reports[-1]["status"] == "uncertain"


def test_transport_disabled_never_spools():
    api, spooler = FakeApi(), FakeSpooler()
    assert PrintWorker(api, spooler, transport_allowed=False).process(claim(api.data)) == "disabled"
    assert not spooler.writes
