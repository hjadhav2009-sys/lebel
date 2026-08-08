from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, minutes: int = 30) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": subject, "exp": expires}, get_settings().secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM]).get("sub")
    except JWTError:
        return None
