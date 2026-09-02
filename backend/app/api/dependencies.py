from typing import Annotated

from fastapi import Depends, Header, HTTPException
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db

Db = Annotated[Session, Depends(get_db)]


def current_user(db: Db, authorization: Annotated[str | None, Header()] = None) -> User:
    try:
        scheme, token = (authorization or "").split(" ", 1)
        if scheme.lower() != "bearer": raise ValueError
        user_id = decode_token(token)["sub"]
    except (ValueError, KeyError, InvalidTokenError):
        raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, "Authentication required.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
