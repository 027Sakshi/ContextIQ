import json
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile
)

from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.user_context import require_current_user

from backend.app.models.email import Email
from backend.app.models.attachment import Attachment
from backend.app.models.action import Action

from backend.app.services.ai_service import analyze_email
from backend.app.services.threat_service import analyze_threat
from backend.app.services.context_service import build_business_context
from backend.app.services.consequence_service import calculate_consequence
from backend.app.services.dependency_service import detect_process_dependency
from backend.app.services.attachment_service import analyze_attachment
from backend.app.services.decision_service import decide_action

from backend.app.services.gmail_service import (
    get_gmail_service,
    list_gmail_messages,
    get_gmail_message,
    parse_gmail_message,
    download_attachment
)

from backend.app.services.action_service import execute_action


router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)


# ==========================================================
# PROJECT PATHS
# ==========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

ATTACHMENT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "attachments"
)


# ==========================================================
# GET EMAILS
# ==========================================================

@router.get("/")
def get_emails(
    db: Session = Depends(get_db)
):
    current_user = require_current_user()

    emails = (
        db.query(Email)
        .filter(
            Email.user_email == current_user
        )
        .order_by(
            Email.received_at.desc()
        )
        .all()
    )

    return emails


# ==========================================================
# GMAIL IMPORT
# ==========================================================

@router.post("/gmail/import")
def import_gmail_emails(
    max_results: int = 10,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    if max_results < 1:

        raise HTTPException(
            status_code=400,
            detail="max_results must be at least 1"
        )

    max_results = min(
        max_results,
        50
    )

    service = get_gmail_service()

    message_ids = list_gmail_messages(
        service=service,
        max_results=max_results
    )

    imported = []

    skipped = []

    errors = []

    for message_id in message_ids:

        try:

            existing_email = (
                db.query(Email)
                .filter(
                    Email.gmail_message_id
                    == message_id,
                    Email.user_email
                    == user_email
                )
                .first()
            )

            if existing_email:

                skipped.append(
                    message_id
                )

                continue

            parsed = get_gmail_message(
                service,
                message_id
            )

            email_record = Email(

                user_email=user_email,

                gmail_message_id=(
                    parsed[
                        "gmail_message_id"
                    ]
                ),

                sender=(
                    parsed["sender"]
                    or "unknown"
                ),

                recipient=(
                    parsed["recipient"]
                    or ""
                ),

                subject=(
                    parsed["subject"]
                    or "(No Subject)"
                ),

                body=(
                    parsed["body"]
                    or ""
                ),

                received_at=(
                    parsed["received_at"]
                )
            )

            db.add(
                email_record
            )

            db.commit()

            db.refresh(
                email_record
            )

            saved_attachments = []

            for attachment in parsed[
                "attachments"
            ]:

                filename = (
                    attachment.get(
                        "filename"
                    )
                    or "attachment"
                )

                extension = (
                    Path(filename)
                    .suffix
                    .lower()
                )

                if extension not in {
                    ".pdf",
                    ".docx",
                    ".txt"
                }:

                    continue

                attachment_id = (
                    attachment.get(
                        "attachment_id"
                    )
                )

                if not attachment_id:

                    continue

                try:

                    file_bytes = (
                        download_attachment(
                            service=service,
                            message_id=message_id,
                            attachment_id=(
                                attachment_id
                            )
                        )
                    )

                    email_directory = (
                        ATTACHMENT_ROOT
                        / f"email_{email_record.id}"
                    )

                    email_directory.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    safe_filename = (
                        Path(filename).name
                    )

                    file_path = (
                        email_directory
                        / safe_filename
                    )

                    file_path.write_bytes(
                        file_bytes
                    )

                    file_type = (
                        extension
                        .replace(".", "")
                    )

                    attachment_analysis = (
                        analyze_attachment(
                            filename=safe_filename,
                            file_path=str(
                                file_path
                            ),
                            file_type=file_type
                        )
                    )

                    db.add(
                        Attachment(

                            email_id=(
                                email_record.id
                            ),

                            filename=safe_filename,

                            file_type=file_type,

                            file_path=str(
                                file_path
                            ),

                            extracted_text=(
                                attachment_analysis[
                                    "extracted_text"
                                ]
                            ),

                            summary=(
                                attachment_analysis[
                                    "summary"
                                ]
                            ),

                            attachment_risk=(
                                attachment_analysis[
                                    "attachment_risk"
                                ]
                            ),

                            business_information=(
                                json.dumps(
                                    attachment_analysis[
                                        "business_information"
                                    ]
                                )
                            )
                        )
                    )

                    saved_attachments.append(
                        safe_filename
                    )

                except Exception as attachment_error:

                    errors.append({

                        "message_id": message_id,

                        "attachment": filename,

                        "error": str(
                            attachment_error
                        )
                    })

            db.commit()

            imported.append({

                "email_id": email_record.id,

                "gmail_message_id": message_id,

                "subject": email_record.subject,

                "sender": email_record.sender,

                "attachments": (
                    saved_attachments
                )
            })

        except Exception as error:

            db.rollback()

            errors.append({

                "message_id": message_id,

                "error": str(error)
            })

    return {

        "message": "Gmail import completed",

        "requested": max_results,

        "found": len(message_ids),

        "imported": len(imported),

        "skipped": len(skipped),

        "errors": len(errors),

        "emails": imported,

        "error_details": errors
    }


# ==========================================================
# UPLOAD ATTACHMENT
# ==========================================================

@router.post("/{email_id}/attachments")
async def upload_attachment(
    email_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    filename = (
        file.filename
        or "unknown_file"
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt"
    }

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Allowed: PDF, DOCX, TXT."
            )
        )

    file_type = (
        extension.replace(
            ".",
            ""
        )
    )

    ATTACHMENT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    email_directory = (
        ATTACHMENT_ROOT
        / f"email_{email_id}"
    )

    email_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_filename = Path(
        filename
    ).name

    file_path = (
        email_directory
        / safe_filename
    )

    contents = await file.read()

    if not contents:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    file_path.write_bytes(
        contents
    )

    analysis = analyze_attachment(
        filename=safe_filename,
        file_path=str(file_path),
        file_type=file_type
    )

    existing = (
        db.query(Attachment)
        .filter(
            Attachment.email_id == email_id,
            Attachment.filename == safe_filename
        )
        .first()
    )

    if existing:

        existing.file_path = str(
            file_path
        )

        existing.extracted_text = (
            analysis["extracted_text"]
        )

        existing.summary = (
            analysis["summary"]
        )

        existing.attachment_risk = (
            analysis["attachment_risk"]
        )

        existing.business_information = (
            json.dumps(
                analysis[
                    "business_information"
                ]
            )
        )

        db.commit()

        db.refresh(existing)

        attachment_id = existing.id

    else:

        record = Attachment(

            email_id=email_id,

            filename=safe_filename,

            file_type=file_type,

            file_path=str(file_path),

            extracted_text=(
                analysis["extracted_text"]
            ),

            summary=(
                analysis["summary"]
            ),

            attachment_risk=(
                analysis["attachment_risk"]
            ),

            business_information=(
                json.dumps(
                    analysis[
                        "business_information"
                    ]
                )
            )
        )

        db.add(record)

        db.commit()

        db.refresh(record)

        attachment_id = record.id

    return {

        "message": (
            "Attachment uploaded and analyzed"
        ),

        "attachment_id": attachment_id,

        "email_id": email_id,

        "filename": safe_filename,

        "analysis": analysis
    }


# ==========================================================
# GET ATTACHMENTS
# ==========================================================

@router.get("/{email_id}/attachments")
def get_attachments(
    email_id: int,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    return (
        db.query(Attachment)
        .filter(
            Attachment.email_id == email_id
        )
        .all()
    )


# ==========================================================
# GET ACTIONS
# ==========================================================

@router.get("/{email_id}/actions")
def get_actions(
    email_id: int,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    return (
        db.query(Action)
        .filter(
            Action.email_id == email_id
        )
        .order_by(
            Action.created_at.desc()
        )
        .all()
    )


# ==========================================================
# APPROVE ACTION
# ==========================================================

@router.post(
    "/{email_id}/actions/{action_id}/approve"
)
def approve_action(
    email_id: int,
    action_id: int,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    action = (
        db.query(Action)
        .filter(
            Action.id == action_id,
            Action.email_id == email_id
        )
        .first()
    )

    if not action:

        raise HTTPException(
            status_code=404,
            detail="Action not found"
        )

    action.status = "approved"

    db.commit()

    return {

        "message": "Action approved",

        "action_id": action.id,

        "status": action.status
    }


# ==========================================================
# REJECT ACTION
# ==========================================================

@router.post(
    "/{email_id}/actions/{action_id}/reject"
)
def reject_action(
    email_id: int,
    action_id: int,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    action = (
        db.query(Action)
        .filter(
            Action.id == action_id,
            Action.email_id == email_id
        )
        .first()
    )

    if not action:

        raise HTTPException(
            status_code=404,
            detail="Action not found"
        )

    action.status = "rejected"

    db.commit()

    return {

        "message": "Action rejected",

        "action_id": action.id,

        "status": action.status
    }


# ==========================================================
# EXECUTE APPROVED ACTION
# ==========================================================

@router.post(
    "/{email_id}/actions/{action_id}/execute"
)
def execute_approved_action(
    email_id: int,
    action_id: int,
    db: Session = Depends(get_db)
):

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    action = (
        db.query(Action)
        .filter(
            Action.id == action_id,
            Action.email_id == email_id
        )
        .first()
    )

    if not action:

        raise HTTPException(
            status_code=404,
            detail="Action not found"
        )

    if action.status != "approved":

        raise HTTPException(
            status_code=400,
            detail=(
                "Action must be approved "
                "before execution."
            )
        )

    result = execute_action(
        action=action,
        db=db
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )

    return result


# ==========================================================
# ANALYZE ALL EMAILS
# ==========================================================

@router.post("/analyze")
def analyze_all_emails(
    db: Session = Depends(get_db)
):
    user_email = require_current_user()

    emails = (
        db.query(Email)
        .filter(
            Email.user_email == user_email
        )
        .order_by(
            Email.received_at.desc()
        )
        .all()
    )

    results = []

    for email in emails:

        # --------------------------------------------------
        # AI
        # --------------------------------------------------

        ai_result = analyze_email(
            subject=email.subject,
            body=email.body,
            sender=email.sender
        )

        # --------------------------------------------------
        # THREAT
        # --------------------------------------------------

        threat_result = analyze_threat(
            sender=email.sender,
            subject=email.subject,
            body=email.body
        )

        # --------------------------------------------------
        # BUSINESS CONTEXT
        # --------------------------------------------------

        business_context = (
            build_business_context(
                sender=email.sender,
                body=email.body,
                db=db
            )
        )

        # --------------------------------------------------
        # PRIORITY
        # --------------------------------------------------

        priority = calculate_priority(
            intent=ai_result["intent"],
            sentiment=ai_result["sentiment"],
            spam_score=(
                threat_result["spam_score"]
            )
        )

        # --------------------------------------------------
        # CONSEQUENCE
        # --------------------------------------------------

        consequence_result = (
            calculate_consequence(
                intent=ai_result["intent"],
                business_context=business_context,
                entities=ai_result["entities"],
                priority_score=priority
            )
        )

        # --------------------------------------------------
        # DEPENDENCY
        # --------------------------------------------------

        dependency_result = (
            detect_process_dependency(
                intent=ai_result["intent"],
                subject=email.subject,
                body=email.body
            )
        )

        # --------------------------------------------------
        # ATTACHMENTS
        # --------------------------------------------------

        attachment_records = (
            db.query(Attachment)
            .filter(
                Attachment.email_id == email.id
            )
            .all()
        )

        attachment_results = []

        for attachment in attachment_records:

            business_information = {}

            if attachment.business_information:

                try:

                    business_information = (
                        json.loads(
                            attachment.business_information
                        )
                    )

                except json.JSONDecodeError:

                    business_information = {}

            attachment_results.append({

                "id": attachment.id,

                "filename": attachment.filename,

                "file_type": attachment.file_type,

                "summary": attachment.summary,

                "attachment_risk": (
                    attachment.attachment_risk
                ),

                "business_information": (
                    business_information
                )
            })

        # --------------------------------------------------
        # DECISION
        # --------------------------------------------------

        decision = decide_action(

            intent=ai_result["intent"],

            spam_score=(
                threat_result["spam_score"]
            ),

            phishing_score=(
                threat_result["phishing_score"]
            ),

            sender_trust=(
                threat_result["sender_trust"]
            ),

            priority_score=priority,

            business_context=(
                business_context
            ),

            consequence=(
                consequence_result
            ),

            process_dependency=(
                dependency_result
            )
        )

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        email.category = (
            ai_result["intent"]
        )

        email.spam_score = (
            threat_result["spam_score"]
        )

        email.priority_score = priority

        email.consequence_score = (
            consequence_result["score"]
        )

        # --------------------------------------------------
        # ACTION RECORD
        # --------------------------------------------------

        existing_action = (
            db.query(Action)
            .filter(
                Action.email_id == email.id
            )
            .order_by(
                Action.created_at.desc()
            )
            .first()
        )

        if existing_action:

            # Don't overwrite an already executed action
            if existing_action.status != "executed":

                existing_action.action_type = (
                    decision["action_type"]
                )

                existing_action.risk_level = (
                    decision["risk_level"]
                )

                existing_action.confidence = (
                    decision["confidence"]
                )

                existing_action.reason = (
                    decision["reason"]
                )

                existing_action.status = (
                    decision["status"]
                )

        else:

            db.add(

                Action(

                    email_id=email.id,

                    action_type=(
                        decision["action_type"]
                    ),

                    risk_level=(
                        decision["risk_level"]
                    ),

                    confidence=(
                        decision["confidence"]
                    ),

                    reason=(
                        decision["reason"]
                    ),

                    status=(
                        decision["status"]
                    )
                )
            )

        # --------------------------------------------------
        # RESPONSE
        # --------------------------------------------------

        results.append({

            "id": email.id,

            "subject": email.subject,

            "sender": email.sender,

            "intent": ai_result["intent"],

            "confidence": (
                ai_result["confidence"]
            ),

            "entities": (
                ai_result["entities"]
            ),

            "sentiment": (
                ai_result["sentiment"]
            ),

            "spam_score": (
                threat_result["spam_score"]
            ),

            "phishing_score": (
                threat_result["phishing_score"]
            ),

            "sender_trust": (
                threat_result["sender_trust"]
            ),

            "priority_score": priority,

            "business_context": (
                business_context
            ),

            "consequence": (
                consequence_result
            ),

            "process_dependency": (
                dependency_result
            ),

            "attachments": (
                attachment_results
            ),

            "decision": decision
        })

    db.commit()

    return {

        "message": (
            "Email analysis completed"
        ),

        "processed": len(results),

        "results": results
    }


# ==========================================================
# PRIORITY
# ==========================================================

def calculate_priority(
    intent: str,
    sentiment: str,
    spam_score: float
) -> float:

    if spam_score >= 0.80:

        return 90.0

    score = 40.0

    if intent == "customer_renewal":

        score += 45

    elif intent == "support_request":

        score += 40

    elif intent == "sales_inquiry":

        score += 30

    elif intent == "product_demo":

        score += 25

    elif intent == "partnership":

        score += 20

    elif intent == "billing":

        score += 25

    elif intent == "complaint":

        score += 35

    elif intent == "spam_or_phishing":

        score += 40

    if sentiment == "negative":

        score += 10

    return min(
        score,
        100.0
    )