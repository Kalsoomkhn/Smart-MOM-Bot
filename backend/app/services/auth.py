from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, new_id, verify_password
from app.db.models import User
from app.repositories import UserRepository, user_dict
from app.schemas import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, request: RegisterRequest) -> dict[str, Any]:
        email = request.email.lower().strip()
        if self.users.by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered. Sign in or use another email.",
            )
        user = self.users.add(
            User(
                id=new_id(),
                name=request.name.strip(),
                email=email,
                role=request.role,
                password_hash=hash_password(request.password),
            )
        )
        self.db.commit()
        token = create_token(user.id, user.email)
        return {
            "access_token": token,
            "token_type": "bearer",
            "token": token,
            "user": user_dict(user),
        }

    def login(self, request: LoginRequest) -> dict[str, Any]:
        return self.login_credentials(request.email, request.password)

    def login_credentials(self, email: str, password: str) -> dict[str, Any]:
        user = self.users.by_email(email.lower().strip())
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        token = create_token(user.id, user.email)
        return {
            "access_token": token,
            "token_type": "bearer",
            "token": token,
            "user": user_dict(user),
        }
