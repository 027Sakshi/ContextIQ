def decide_action(
    intent: str,
    spam_score: float,
    phishing_score: float,
    sender_trust: float,
    priority_score: float,
    business_context: dict,
    consequence: dict,
    process_dependency: dict
) -> dict:
    """
    Decide what ContextIQ should recommend
    based on the complete email intelligence.
    """

    # ==================================================
    # 1. SECURITY ACTION
    # ==================================================

    if (
        spam_score >= 0.80
        or phishing_score >= 0.80
    ):

        return {
            "action_type": "security_review",
            "risk_level": "HIGH",
            "confidence": 0.98,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Email has a high spam/phishing risk "
                "and should be reviewed before interaction."
            )
        }

    # ==================================================
    # 2. CUSTOMER RENEWAL
    # ==================================================

    if intent == "customer_renewal":

        impact_score = consequence.get(
            "score",
            0
        )

        if impact_score >= 80:

            return {
                "action_type": "escalate_account_manager",
                "risk_level": "HIGH",
                "confidence": 0.96,
                "approval_required": True,
                "status": "pending",
                "reason": (
                    "High-impact customer renewal detected. "
                    "The account should be escalated to the "
                    "account manager immediately."
                )
            }

        return {
            "action_type": "create_renewal_task",
            "risk_level": "MEDIUM",
            "confidence": 0.90,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Customer renewal detected. "
                "Create a follow-up task."
            )
        }

    # ==================================================
    # 3. SUPPORT REQUEST
    # ==================================================

    if intent == "support_request":

        if (
            process_dependency.get(
                "is_blocking"
            )
            or priority_score >= 80
        ):

            return {
                "action_type": "escalate_support",
                "risk_level": "HIGH",
                "confidence": 0.94,
                "approval_required": True,
                "status": "pending",
                "reason": (
                    "Urgent support issue may be "
                    "blocking business operations."
                )
            }

        return {
            "action_type": "create_support_ticket",
            "risk_level": "MEDIUM",
            "confidence": 0.91,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Support request detected. "
                "Create a support ticket."
            )
        }

    # ==================================================
    # 4. PRODUCT DEMO / MEETING
    # ==================================================

    if intent == "product_demo":

        calendar = business_context.get(
            "calendar",
            {}
        )

        if calendar.get(
            "meeting_requested"
        ):

            return {
                "action_type": "schedule_demo",
                "risk_level": "MEDIUM",
                "confidence": 0.93,
                "approval_required": True,
                "status": "pending",
                "reason": (
                    "Customer requested a product demo. "
                    "A calendar slot can be suggested."
                )
            }

        return {
            "action_type": "follow_up_demo_request",
            "risk_level": "LOW",
            "confidence": 0.86,
            "approval_required": False,
            "status": "recommended",
            "reason": (
                "Product demo request detected."
            )
        }

    # ==================================================
    # 5. SALES INQUIRY
    # ==================================================

    if intent == "sales_inquiry":

        return {
            "action_type": "create_or_update_lead",
            "risk_level": "MEDIUM",
            "confidence": 0.92,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Potential sales opportunity detected. "
                "CRM lead/opportunity should be created "
                "or updated."
            )
        }

    # ==================================================
    # 6. PARTNERSHIP
    # ==================================================

    if intent == "partnership":

        return {
            "action_type": "assign_to_partnerships",
            "risk_level": "MEDIUM",
            "confidence": 0.88,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Partnership or collaboration request detected."
            )
        }

    # ==================================================
    # 7. BILLING
    # ==================================================

    if intent == "billing":

        return {
            "action_type": "assign_to_finance",
            "risk_level": "MEDIUM",
            "confidence": 0.90,
            "approval_required": True,
            "status": "pending",
            "reason": (
                "Billing-related email should be "
                "reviewed by the finance team."
            )
        }

    # ==================================================
    # 8. GENERAL EMAIL
    # ==================================================

    return {
        "action_type": "categorize_and_monitor",
        "risk_level": "LOW",
        "confidence": 0.75,
        "approval_required": False,
        "status": "recommended",
        "reason": (
            "No high-impact action is required."
        )
    }