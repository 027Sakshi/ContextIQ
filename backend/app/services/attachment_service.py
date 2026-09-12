import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader
from docx import Document


# ==========================================================
# TEXT EXTRACTION
# ==========================================================

def extract_text_from_file(
    file_path: str,
    file_type: str
) -> str:
    """
    Extract readable text from PDF, DOCX or TXT.
    """

    file_type = file_type.lower()

    # ------------------------------------------------------
    # PDF
    # ------------------------------------------------------

    if file_type == "pdf":

        reader = PdfReader(file_path)

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n".join(pages).strip()

    # ------------------------------------------------------
    # DOCX
    # ------------------------------------------------------

    if file_type == "docx":

        document = Document(file_path)

        paragraphs = []

        for paragraph in document.paragraphs:

            text = paragraph.text.strip()

            if text:
                paragraphs.append(text)

        return "\n".join(paragraphs).strip()

    # ------------------------------------------------------
    # TXT
    # ------------------------------------------------------

    if file_type == "txt":

        return Path(file_path).read_text(
            encoding="utf-8"
        ).strip()

    return ""


# ==========================================================
# BUSINESS INFORMATION EXTRACTION
# ==========================================================

def extract_business_information(
    text: str
) -> dict:
    """
    Extract useful business fields from an attachment.
    """

    information = {
        "company": None,
        "product": None,
        "quantity": None,
        "value": None,
        "validity": None,
        "contact": None
    }

    if not text:
        return information

    # ------------------------------------------------------
    # Company
    # ------------------------------------------------------

    company_match = re.search(
        r"(?:company|organization)\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if company_match:

        information["company"] = (
            company_match.group(1).strip()
        )

    # ------------------------------------------------------
    # Product
    # ------------------------------------------------------

    product_match = re.search(
        r"product\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if product_match:

        information["product"] = (
            product_match.group(1).strip()
        )

    # ------------------------------------------------------
    # Quantity
    # ------------------------------------------------------

    quantity_match = re.search(
        r"(\d+)\s+"
        r"(licenses|license|users|units|seats|items)",
        text,
        re.IGNORECASE
    )

    if quantity_match:

        information["quantity"] = (
            f"{quantity_match.group(1)} "
            f"{quantity_match.group(2)}"
        )

    # ------------------------------------------------------
    # Value
    # ------------------------------------------------------

    value_match = re.search(
        r"(?:total value|amount|value)"
        r"\s*:\s*"
        r"(₹\s?[\d,]+(?:\.\d+)?"
        r"\s?(?:lakh|L|crore|Cr)?)",
        text,
        re.IGNORECASE
    )

    if value_match:

        information["value"] = (
            value_match.group(1).strip()
        )

    # ------------------------------------------------------
    # Validity
    # ------------------------------------------------------

    validity_match = re.search(
        r"(?:quotation )?"
        r"validity"
        r"\s*:\s*"
        r"(.+)",
        text,
        re.IGNORECASE
    )

    if validity_match:

        information["validity"] = (
            validity_match.group(1).strip()
        )

    # ------------------------------------------------------
    # Contact
    # ------------------------------------------------------

    contact_match = re.search(
        r"contact\s*:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if contact_match:

        information["contact"] = (
            contact_match.group(1).strip()
        )

    return information


# ==========================================================
# ATTACHMENT RISK
# ==========================================================

def calculate_attachment_risk(
    text: str,
    filename: str
) -> float:
    """
    Basic attachment-risk detection.

    0.0 = low risk
    1.0 = high risk
    """

    combined_text = (
        f"{filename} {text}"
    ).lower()

    suspicious_terms = [
        "macro",
        "enable content",
        "enable macros",
        ".exe",
        "executable",
        "password required",
        "urgent payment",
        "click this link",
        "malware",
        "ransomware"
    ]

    matches = sum(
        1
        for term in suspicious_terms
        if term in combined_text
    )

    if matches >= 3:

        return 0.90

    if matches == 2:

        return 0.70

    if matches == 1:

        return 0.45

    return 0.05


# ==========================================================
# MAIN ATTACHMENT ANALYSIS
# ==========================================================

def analyze_attachment(
    filename: str,
    file_path: str,
    file_type: str
) -> dict:
    """
    Complete attachment analysis.
    """

    extracted_text = extract_text_from_file(
        file_path=file_path,
        file_type=file_type
    )

    business_information = (
        extract_business_information(
            extracted_text
        )
    )

    attachment_risk = calculate_attachment_risk(
        text=extracted_text,
        filename=filename
    )

    # ------------------------------------------------------
    # Summary
    # ------------------------------------------------------

    if extracted_text:

        summary = extracted_text[:600]

        if len(extracted_text) > 600:
            summary += "..."

    else:

        summary = (
            "No readable text could be extracted."
        )

    return {
        "filename": filename,
        "file_type": file_type,
        "extracted_text": extracted_text,
        "summary": summary,
        "attachment_risk": attachment_risk,
        "business_information": business_information,
        "extracted_at": datetime.utcnow().isoformat()
    }