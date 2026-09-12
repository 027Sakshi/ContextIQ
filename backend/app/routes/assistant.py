from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.services.knowledge_service import retrieve_business_knowledge
from backend.app.services.llm_service import answer_business_question
from backend.app.user_context import require_current_user

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=8, ge=3, le=15)


@router.post("/ask")
def ask_contextiq(payload: AskRequest, db: Session = Depends(get_db)):
    user_email = require_current_user()
    retrieval = retrieve_business_knowledge(db, user_email, payload.question, payload.top_k)
    response = answer_business_question(payload.question, retrieval["evidence"])
    return {
        "question": payload.question,
        "answer": response["answer"],
        "confidence": response.get("confidence", 0.0),
        "provider": response.get("provider", "local-fallback"),
        "model": response.get("model"),
        "used_evidence": response.get("used_evidence", []),
        "recommended_next_steps": response.get("recommended_next_steps", []),
        "retrieval_model": retrieval["retrieval_model"],
        "document_count": retrieval["document_count"],
        "evidence": retrieval["evidence"],
    }
