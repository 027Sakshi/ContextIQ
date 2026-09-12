def detect_process_dependency(
    intent: str,
    subject: str,
    body: str
) -> dict:

    text = f"{subject} {body}".lower()

    is_blocking = False
    blocked_process = None
    reason = None
    downstream_impact = None

    # Contract / agreement dependency
    if any(word in text for word in [
        "signed agreement",
        "signed contract",
        "agreement required",
        "contract approval"
    ]):
        is_blocking = True
        blocked_process = "Procurement"
        reason = "Required agreement has not been completed"
        downstream_impact = "Purchase order may be delayed"

    # Payment / invoice dependency
    elif any(word in text for word in [
        "invoice approval",
        "payment approval",
        "payment pending"
    ]):
        is_blocking = True
        blocked_process = "Finance"
        reason = "Payment-related action is pending"
        downstream_impact = "Payment processing may be delayed"

    # Demo / sales dependency
    elif intent == "product_demo" and any(word in text for word in [
        "schedule",
        "meeting",
        "demo"
    ]):
        is_blocking = True
        blocked_process = "Sales"
        reason = "Customer demo needs to be scheduled"
        downstream_impact = "Opportunity progression may be delayed"

    # Renewal dependency
    elif intent == "customer_renewal":
        is_blocking = True
        blocked_process = "Customer Renewal"
        reason = "Renewal confirmation is pending"
        downstream_impact = "Customer renewal may be delayed"

    return {
        "is_blocking": is_blocking,
        "blocked_process": blocked_process,
        "reason": reason,
        "downstream_impact": downstream_impact
    }