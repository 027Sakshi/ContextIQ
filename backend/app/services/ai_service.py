import re


# ==========================================================
# INTENT DETECTION
# ==========================================================

def detect_intent(
    subject: str,
    body: str
) -> tuple[str, float]:

    text = f"{subject} {body}".lower()

    # Customer renewal
    if any(
        word in text
        for word in [
            "contract expires",
            "renewal",
            "renew",
            "subscription expires"
        ]
    ):
        return "customer_renewal", 0.95

    # Sales inquiry
    if any(
        word in text
        for word in [
            "purchase",
            "buy",
            "pricing",
            "quotation",
            "quote",
            "licenses",
            "requirement",
            "interested in your"
        ]
    ):
        return "sales_inquiry", 0.92

    # Product demo
    if any(
        word in text
        for word in [
            "demo",
            "demonstration",
            "product demonstration"
        ]
    ):
        return "product_demo", 0.90

    # Support
    if any(
        word in text
        for word in [
            "production system",
            "not working",
            "down",
            "issue",
            "problem",
            "urgent help"
        ]
    ):
        return "support_request", 0.94

    # Partnership
    if any(
        word in text
        for word in [
            "partnership",
            "partner with",
            "collaboration"
        ]
    ):
        return "partnership", 0.90

    # Spam / phishing
    if any(
        word in text
        for word in [
            "won a prize",
            "claim your prize",
            "click the link",
            "congratulations! you have won"
        ]
    ):
        return "spam_or_phishing", 0.98

    return "general_inquiry", 0.70


# ==========================================================
# SENDER ENTITY EXTRACTION
# ==========================================================

def extract_sender_entities(
    sender: str
) -> dict:

    result = {
        "person": None,
        "company": None
    }

    if not sender:
        return result

    # ------------------------------------------------------
    # Extract email address
    # ------------------------------------------------------

    email_match = re.search(
        r"[\w\.-]+@([\w\.-]+\.\w+)",
        sender
    )

    if not email_match:
        return result

    domain = email_match.group(1)

    # ------------------------------------------------------
    # Extract username
    # ------------------------------------------------------

    username = sender.split("@")[0]

    # Convert common formats:
    # rahul.sharma -> Rahul Sharma
    # rahul_sharma -> Rahul Sharma
    # rahul-sharma -> Rahul Sharma

    person_name = re.sub(
        r"[._-]+",
        " ",
        username
    ).strip()

    if person_name:

        result["person"] = person_name.title()

    # ------------------------------------------------------
    # Extract company from domain
    # ------------------------------------------------------

    domain_parts = domain.split(".")

    if domain_parts:

        company_name = domain_parts[0]

        # Ignore common providers
        common_domains = {
            "gmail",
            "yahoo",
            "hotmail",
            "outlook",
            "icloud"
        }

        if company_name.lower() not in common_domains:

            company_name = re.sub(
                r"[-_]+",
                " ",
                company_name
            )

            result["company"] = company_name.title()

    return result


# ==========================================================
# TEXT ENTITY EXTRACTION
# ==========================================================

def extract_entities(
    subject: str,
    body: str,
    sender: str = ""
) -> dict:

    text = f"{subject} {body}"

    sender_entities = extract_sender_entities(
        sender
    )

    entities = {
        "company": sender_entities["company"],
        "person": sender_entities["person"],
        "budget": None,
        "quantity": None,
        "deadline": None
    }

    # ------------------------------------------------------
    # Budget
    # ------------------------------------------------------

    budget_match = re.search(
        r"(₹\s?[\d,]+(?:\.\d+)?\s?(?:lakh|L|crore|Cr)?)",
        text,
        re.IGNORECASE
    )

    if budget_match:

        entities["budget"] = (
            budget_match.group(1)
        )

    # ------------------------------------------------------
    # Quantity
    # ------------------------------------------------------

    quantity_match = re.search(
        r"(\d+)\s+(?:licenses|users|units|seats|items)",
        text,
        re.IGNORECASE
    )

    if quantity_match:

        entities["quantity"] = (
            quantity_match.group(1)
        )

    # ------------------------------------------------------
    # Deadline
    # ------------------------------------------------------

    deadline_patterns = [
        r"expires tomorrow",
        r"before Friday",
        r"next week",
        r"within \d+ days",
        r"by tomorrow",
        r"by Friday"
    ]

    for pattern in deadline_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            entities["deadline"] = (
                match.group(0)
            )

            break

    return entities


# ==========================================================
# SENTIMENT DETECTION
# ==========================================================

def detect_sentiment(
    body: str
) -> str:

    text = body.lower()

    negative_words = [
        "urgent",
        "problem",
        "issue",
        "failed",
        "down",
        "blocked",
        "not working"
    ]

    positive_words = [
        "interested",
        "thank",
        "renew",
        "great",
        "looking forward"
    ]

    if any(
        word in text
        for word in negative_words
    ):

        return "negative"

    if any(
        word in text
        for word in positive_words
    ):

        return "positive"

    return "neutral"


# ==========================================================
# MAIN EMAIL ANALYSIS
# ==========================================================

def analyze_email(
    subject: str,
    body: str,
    sender: str = ""
) -> dict:

    # ------------------------------------------------------
    # Intent
    # ------------------------------------------------------

    intent, confidence = detect_intent(
        subject,
        body
    )

    # ------------------------------------------------------
    # Entities
    # ------------------------------------------------------

    entities = extract_entities(
        subject,
        body,
        sender
    )

    # ------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------

    sentiment = detect_sentiment(
        body
    )

    return {
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "sentiment": sentiment
    }