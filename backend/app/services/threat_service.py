def analyze_threat(
    sender: str,
    subject: str,
    body: str
) -> dict:

    text = f"{sender} {subject} {body}".lower()

    spam_score = 0.05
    phishing_score = 0.02
    sender_trust = 0.80

    suspicious_words = [
        "winner",
        "won a prize",
        "claim now",
        "urgent",
        "click the link",
        "verify your account",
        "password",
        "gift",
        "lottery"
    ]

    suspicious_count = sum(
        1
        for word in suspicious_words
        if word in text
    )

    if suspicious_count >= 3:
        spam_score = 0.95
        phishing_score = 0.90
        sender_trust = 0.15

    elif suspicious_count >= 1:
        spam_score = 0.55
        phishing_score = 0.40
        sender_trust = 0.45

    # Basic corporate-domain signal
    if sender.endswith(".com"):
        sender_trust += 0.05

    sender_trust = min(sender_trust, 1.0)

    return {
        "spam_score": spam_score,
        "phishing_score": phishing_score,
        "sender_trust": sender_trust
    }