import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AgentPairingCode, PrintAgent


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AgentAuthenticationError(ValueError):
    pass


class AgentAuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_pairing_code(self, actor_id=None) -> tuple[str, AgentPairingCode]:
        code = "-".join(str(secrets.randbelow(9000) + 1000) for _ in range(3))
        row = AgentPairingCode(code_hash=_hash(code), expires_at=datetime.now(timezone.utc) + timedelta(seconds=get_settings().agent_pairing_ttl_seconds), created_by_id=actor_id)
        self.db.add(row)
        return code, row

    def pair(self, code: str, *, machine_name: str, name: str, version: str | None = None) -> tuple[PrintAgent, str]:
        now = datetime.now(timezone.utc)
        row = self.db.scalar(select(AgentPairingCode).where(AgentPairingCode.code_hash == _hash(code), AgentPairingCode.used_at.is_(None), AgentPairingCode.expires_at > now).with_for_update())
        if not row:
            raise AgentAuthenticationError("PAIRING_CODE_INVALID_OR_EXPIRED")
        if self.db.scalar(select(PrintAgent).where(PrintAgent.machine_name == machine_name, PrintAgent.revoked_at.is_(None))):
            raise AgentAuthenticationError("MACHINE_ALREADY_PAIRED")
        token = "mms_agent_" + secrets.token_urlsafe(40)
        agent = PrintAgent(name=name, machine_name=machine_name, token_hash=_hash(token), token_hint=token[-6:], version=version, status="online", last_seen_at=now)
        row.used_at = now
        self.db.add(agent)
        return agent, token

    def authenticate(self, token: str) -> PrintAgent:
        if not token:
            raise AgentAuthenticationError("AGENT_TOKEN_REQUIRED")
        digest = _hash(token)
        for agent in self.db.scalars(select(PrintAgent).where(PrintAgent.revoked_at.is_(None), PrintAgent.token_hash == digest)).all():
            if hmac.compare_digest(agent.token_hash, digest):
                return agent
        raise AgentAuthenticationError("AGENT_TOKEN_INVALID")

    @staticmethod
    def revoke(agent: PrintAgent) -> None:
        agent.revoked_at = datetime.now(timezone.utc)
        agent.status = "revoked"
