from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, meetings
from app.core.config import get_settings
from app.db.session import SessionLocal, create_tables
from app.seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    create_tables()
    with SessionLocal() as db: seed_demo_data(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.client_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api")
app.include_router(meetings.router, prefix="/api")


@app.get("/health")
def health(): return {"status": "ok", "database": settings.database_mode}


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException): return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse({"error": exc.errors()[0].get("msg", "Invalid request.")}, status_code=400)


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    return JSONResponse({"error": str(exc) or "Unexpected server error. Please try again."}, status_code=500)
