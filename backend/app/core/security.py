from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


def new_id() -> str:
    return str(uuid4())


def hash_password(password: str) -> str:
    return passwords.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return passwords.verify(password, password_hash)


def create_token(user_id: str, email: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    return jwt.encode({"sub": user_id, "email": email, "exp": expires}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
