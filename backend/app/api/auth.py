from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import CurrentUser, Db
from app.repositories import user_dict
from app.schemas import LoginRequest, RegisterRequest, RoleRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Db) -> dict[str, Any]:
    return AuthService(db).register(request)


@router.post("/login")
async def login(request: Request, db: Db) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "").strip()
        password = str(form.get("password") or "")
    else:
        try:
            body = await request.json()
            email = str(body.get("email") or body.get("username") or "").strip()
            password = str(body.get("password") or "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login request body.",
            )
    return AuthService(db).login_credentials(email, password)


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return user_dict(user)


@router.put("/me/role")
def update_role(request: RoleRequest, user: CurrentUser, db: Db) -> dict[str, Any]:
    user.role = request.role
    db.commit()
    return user_dict(user)
