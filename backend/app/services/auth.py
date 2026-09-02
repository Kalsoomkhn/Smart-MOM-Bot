from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, new_id, verify_password
from app.db.models import User
from app.repositories import UserRepository, user_dict
from app.schemas import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: Session): self.db, self.users = db, UserRepository(db)

    def register(self, request: RegisterRequest) -> dict:
        email = request.email.lower().strip()
        if self.users.by_email(email):
            raise HTTPException(status.HTTP_409_CONFLICT, "This email is already registered. Sign in or use another email.")
        user = self.users.add(User(id=new_id(), name=request.name.strip(), email=email, role=request.role, password_hash=hash_password(request.password)))
        self.db.commit()
        return {"token": create_token(user.id, user.email), "user": user_dict(user)}

    def login(self, request: LoginRequest) -> dict:
        user = self.users.by_email(request.email.lower().strip())
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
        return {"token": create_token(user.id, user.email), "user": user_dict(user)}
