from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, Db
from app.repositories import user_dict
from app.schemas import LoginRequest, RegisterRequest, RoleRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Db) -> dict[str, Any]:
    return AuthService(db).register(request)


@router.post("/login")
def login(request: LoginRequest, db: Db) -> dict[str, Any]:
    return AuthService(db).login(request)


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return user_dict(user)


@router.put("/me/role")
def update_role(request: RoleRequest, user: CurrentUser, db: Db) -> dict[str, Any]:
    user.role = request.role
    db.commit()
    return user_dict(user)
