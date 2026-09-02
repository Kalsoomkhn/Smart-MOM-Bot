from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base

settings = get_settings()
if settings.database_url.startswith("sqlite"):
    Path(".data").mkdir(exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
