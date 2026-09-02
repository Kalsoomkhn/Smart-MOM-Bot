from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUser, Db
from app.repositories import user_dict
from app.schemas import LoginRequest, RegisterRequest, RoleRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=201)
def register(request: RegisterRequest, db: Db): return AuthService(db).register(request)


@router.post("/login")
def login(request: LoginRequest, db: Db): return AuthService(db).login(request)


@router.get("/me")
def me(user: CurrentUser): return user_dict(user)


@router.put("/me/role")
def update_role(request: RoleRequest, user: CurrentUser, db: Db):
    user.role = request.role; db.commit(); return user_dict(user)
