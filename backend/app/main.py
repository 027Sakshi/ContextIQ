from fastapi import FastAPI
from sqlalchemy import text
from backend.app.user_middleware import ContextIQUserMiddleware
from backend.app.database.base import Base
from backend.app.database.connection import engine
from backend.app.routes.calendar import router as calendar_router
from backend.app.models import (
    Email,
    Contact,
    Company,
    CRMRecord,
    Opportunity,
    CalendarEvent,
    Attachment,
    Action,
)

from backend.app.routes.emails import router as email_router


app = FastAPI(
    title="ContextIQ API",
    description="AI-Powered Business Email Intelligence System",
    version="1.0.0"
)
app.include_router(
    calendar_router
)
app.add_middleware(
    ContextIQUserMiddleware
)

# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

Base.metadata.create_all(
    bind=engine
)


# ==========================================================
# DATABASE MIGRATION
# ==========================================================

with engine.begin() as connection:

    connection.execute(
        text(
            """
            ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS gmail_message_id
            VARCHAR(255);
            """
        )
    )


# ==========================================================
# ROUTES
# ==========================================================

app.include_router(
    email_router
)


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():

    return {
        "message": "ContextIQ backend is running",
        "status": "success"
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }