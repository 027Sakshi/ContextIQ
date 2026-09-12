from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.commitment import Commitment
from backend.app.user_context import require_current_user

router = APIRouter(prefix="/commitments", tags=["Commitments"])


@router.get("/")
def list_commitments(status: str = "open", db: Session = Depends(get_db)):
    user = require_current_user()
    query = db.query(Commitment).filter(Commitment.user_email == user)
    if status != "all":
        query = query.filter(Commitment.status == status)
    return query.order_by(Commitment.due_at.asc(), Commitment.created_at.desc()).all()


@router.post("/{commitment_id}/complete")
def complete_commitment(commitment_id: int, db: Session = Depends(get_db)):
    user = require_current_user()
    item = db.query(Commitment).filter(
        Commitment.id == commitment_id,
        Commitment.user_email == user,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Commitment not found")
    item.status = "completed"
    db.commit()
    db.refresh(item)
    return item
