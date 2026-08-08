import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (BarcodeVerification, Marketplace, MarketplaceAccount, PrintAgent, PrintArtifact,
    Printer, PrinterProfile, PrintJob)
from app.services.agent_auth_service import AgentAuthenticationError, AgentAuthService
from app.services.agent_job_service import AgentJobService
from app.services.renderer_approval_service import RendererApprovalError, RendererApprovalService


@pytest.fixture
def db():
    engine=create_engine("sqlite+pysqlite:///:memory:");Base.metadata.create_all(engine)
    with Session(engine) as session: yield session


def test_pairing_code_is_one_time_and_agent_token_is_revocable(db):
    auth=AgentAuthService(db);code,_=auth.create_pairing_code();db.flush()
    agent,token=auth.pair(code,machine_name="PRINT-PC-1",name="Packing desk");db.flush()
    assert auth.authenticate(token).id==agent.id and agent.token_hash!=token
    with pytest.raises(AgentAuthenticationError): auth.pair(code,machine_name="PRINT-PC-2",name="Second")
    auth.revoke(agent);db.flush()
    with pytest.raises(AgentAuthenticationError): auth.authenticate(token)


def print_setup(db):
    account=MarketplaceAccount(marketplace=Marketplace.AMAZON,name="Primary");agent=PrintAgent(name="Desk",machine_name="PC",token_hash="hash")
    db.add_all([account,agent]);db.flush();printer=Printer(agent_id=agent.id,name="TSC TE244",driver_name="TSC",dpi=203,status="online",is_enabled=True)
    db.add(printer);db.flush();profile=PrinterProfile(printer_id=printer.id,marketplace=Marketplace.AMAZON,media_width_mm=101.5,media_height_mm=50,gap_mm=2,renderer="amazon_dynamic_tspl_v1",config={"approved_dpi":203})
    db.add(profile);db.flush();return account,agent,printer,profile


def test_only_assigned_agent_can_claim_once_and_claim_contains_immutable_artifact(db):
    account,agent,_,profile=print_setup(db);job=PrintJob(account_id=account.id,marketplace=Marketplace.AMAZON,status="waiting_for_agent",printer_profile_id=profile.id,printer_name="TSC TE244")
    db.add(job);db.flush();payload=b"PRINT 1,1\r\n";artifact=PrintArtifact(print_job_id=job.id,artifact_type="raw_tspl",renderer_key="amazon_dynamic_tspl_v1",renderer_version="1.0.0",layout_version=1,printer_profile_id=profile.id,sha256=hashlib.sha256(payload).hexdigest(),byte_size=len(payload),storage_key="job/file.tspl",content_type="application/vnd.tsc-tspl",status="ready",metadata_={})
    db.add(artifact);db.flush();claimed=AgentJobService(db).claim(agent)
    assert claimed and claimed[0].status=="claimed" and claimed[1].sha256==artifact.sha256 and claimed[2]
    assert AgentJobService(db).claim(agent) is None


def test_renderer_approval_requires_completed_test_and_passing_scan(db):
    account,_,_,profile=print_setup(db);job=PrintJob(account_id=account.id,marketplace=Marketplace.AMAZON,status="completed",printer_profile_id=profile.id,is_test=True)
    db.add(job);db.flush();service=RendererApprovalService(db)
    with pytest.raises(RendererApprovalError): service.approve(profile,job,format_key="key_chain")
    db.add(BarcodeVerification(print_job_id=job.id,expected_value="X001",scanned_value="X001",passed=True));db.flush()
    approval=service.approve(profile,job,format_key="key_chain");assert approval.renderer_version=="1.0.0" and approval.layout_version==1
