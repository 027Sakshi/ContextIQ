from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.config import settings
from backend.app.database.base import Base
from backend.app.database.connection import engine
from backend.app.database.schema import ensure_schema_compatibility
from backend.app.models import (
    Action,
    Attachment,
    CalendarEvent,
    Company,
    Contact,
    CRMRecord,
    Email,
    Opportunity,
)
from backend.app.routes.calendar import router as calendar_router
from backend.app.routes.emails import router as email_router
from backend.app.user_context import MissingUserContextError
from backend.app.user_middleware import ContextIQUserMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
    yield


app = FastAPI(
    title="ContextIQ API",
    description="AI-powered business context and action intelligence",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(ContextIQUserMiddleware)
app.include_router(calendar_router)
app.include_router(email_router)


@app.exception_handler(MissingUserContextError)
async def missing_user_handler(_: Request, error: MissingUserContextError):
    return JSONResponse(
        status_code=401,
        content={"detail": str(error)},
    )


@app.get("/")
def root():
    return {
        "message": "ContextIQ backend is running",
        "status": "success",
        "environment": settings.app_env,
    }


@app.get("/health")
def health_check():
    database_status = "healthy"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unhealthy"

    status = (
        "healthy"
        if database_status == "healthy"
        else "degraded"
    )

    return {
        "status": status,
        "database": database_status,
        "environment": settings.app_env,
        "dev_user_header_enabled": settings.allow_dev_user_header,
    }
