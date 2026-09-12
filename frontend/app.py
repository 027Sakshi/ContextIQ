from pathlib import Path
import os
import sys
import json
import re
import html
from datetime import datetime
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st

from frontend.auth import (
    initialize_auth,
    show_login_page,
    logout_user,
)

from backend.app.services.rag_service import run_rag
from backend.app.services.llm_service import (
    generate_business_insight,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

API_URL = os.getenv("CONTEXTIQ_API_URL", "http://127.0.0.1:8000").rstrip("/")


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="ContextIQ",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# AUTH
# ==========================================================

initialize_auth()

if not show_login_page():
    st.stop()


# ==========================================================
# USER CONTEXT
# ==========================================================

def current_user() -> str:
    return (
        st.session_state
        .get("user_email", "")
        .strip()
        .lower()
    )


def api_headers() -> dict:
    token = str(st.session_state.get("contextiq_session_token", "")).strip()
    if token:
        return {"Authorization": f"Bearer {token}"}

    # Explicit local-dev fallback only. Production never trusts this header.
    user = current_user()
    return {"X-ContextIQ-User": user} if user else {}


# ==========================================================
# SAFE TEXT / EMAIL BODY CLEANING
# ==========================================================

def clean_email_body(
    body: Any,
    max_chars: int | None = None,
) -> str:
    """
    Make HTML-heavy email bodies readable and safe for the UI.

    This specifically prevents HTML/CSS source from making the
    Intelligent Inbox look like a code dump.
    """

    if body is None:
        return ""

    text = str(body)

    # Decode HTML entities.
    text = html.unescape(text)

    # Remove scripts and styles completely.
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.I | re.S,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.I | re.S,
    )

    # Replace common block-level tags with line breaks.
    text = re.sub(
        r"<\s*(br|p|div|li|tr|h[1-6])[^>]*>",
        "\n",
        text,
        flags=re.I,
    )

    # Remove remaining tags.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Remove obvious CSS / HTML leftovers.
    text = re.sub(
        r"/\*.*?\*/",
        " ",
        text,
        flags=re.S,
    )

    text = re.sub(
        r"\b(?:font-family|background-color|color|padding|margin|"
        r"border|line-height|font-size)\s*:[^;{}]+;?",
        " ",
        text,
        flags=re.I,
    )

    # Normalize whitespace.
    lines = []

    for line in text.splitlines():
        cleaned = re.sub(
            r"\s+",
            " ",
            line,
        ).strip()

        if cleaned:
            lines.append(cleaned)

    cleaned = "\n".join(lines)

    # Collapse excessive blank lines.
    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    ).strip()

    if max_chars and len(cleaned) > max_chars:
        return (
            cleaned[:max_chars].rstrip()
            + "\n\n… Email preview truncated."
        )

    return cleaned


def money(value: Any) -> str:
    try:
        number = float(value)

        return f"₹{number:,.0f}"

    except (
        TypeError,
        ValueError,
    ):
        return "—"


def percentage(value: Any) -> str:
    try:
        number = float(value)

        if number <= 1:
            number *= 100

        return f"{number:.0f}%"

    except (
        TypeError,
        ValueError,
    ):
        return "—"


def title_case(value: Any) -> str:
    if value is None:
        return "—"

    return (
        str(value)
        .replace("_", " ")
        .strip()
        .title()
    )


# ==========================================================
# API HELPERS
# ==========================================================

def api_get(
    path: str,
    timeout: int = 30,
):
    try:
        response = requests.get(
            f"{API_URL}{path}",
            headers=api_headers(),
            timeout=timeout,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        st.error(
            f"Backend request failed: {error}"
        )

        return None


def api_post(
    path: str,
    params: dict | None = None,
    json_body: dict | None = None,
    timeout: int = 120,
):
    try:
        response = requests.post(
            f"{API_URL}{path}",
            params=params,
            json=json_body,
            headers=api_headers(),
            timeout=timeout,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        st.error(
            f"Backend request failed: {error}"
        )

        return None


def get_emails():
    return (
        api_get(
            "/emails/",
            timeout=30,
        )
        or []
    )


def sync_gmail():
    return api_post(
        "/emails/gmail/import",
        params={
            "max_results": 10,
        },
        timeout=120,
    )


def analyze_emails():
    return api_post(
        "/emails/analyze",
        timeout=180,
    )


def get_actions(
    email_id: int,
):
    return (
        api_get(
            f"/emails/{email_id}/actions",
            timeout=30,
        )
        or []
    )


def approve_action(
    email_id: int,
    action_id: int,
):
    return api_post(
        f"/emails/{email_id}/actions/{action_id}/approve",
        timeout=30,
    )


def reject_action(
    email_id: int,
    action_id: int,
):
    return api_post(
        f"/emails/{email_id}/actions/{action_id}/reject",
        timeout=30,
    )


def execute_action(
    email_id: int,
    action_id: int,
):
    return api_post(
        f"/emails/{email_id}/actions/{action_id}/execute",
        timeout=60,
    )


def get_calendar_events():
    return (
        api_get(
            "/calendar/",
            timeout=30,
        )
        or []
    )


def get_attachments(
    email_id: int,
):
    return (
        api_get(
            f"/emails/{email_id}/attachments",
            timeout=30,
        )
        or []
    )


# ==========================================================
# SESSION STATE
# ==========================================================

defaults = {
    "analysis": None,
    "page": "Dashboard",
    "business_insights": {},
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================================
# GLOBAL STYLING
# ==========================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1500px;
        padding-top: 1.15rem;
        padding-bottom: 3rem;
    }

    .ctx-hero {
        padding: 1.6rem 1.8rem;
        border-radius: 22px;
        border: 1px solid rgba(128,128,128,.22);
        background:
            linear-gradient(
                135deg,
                rgba(77,101,255,.17),
                rgba(0,188,173,.10)
            );
        margin-bottom: 1rem;
    }

    .ctx-eyebrow {
        font-size: .75rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        opacity: .65;
    }

    .ctx-title {
        font-size: 2.7rem;
        font-weight: 900;
        letter-spacing: -.045em;
        margin: .2rem 0 .2rem;
    }

    .ctx-subtitle {
        opacity: .72;
        font-size: 1rem;
        margin: 0;
    }

    .ctx-user {
        display: inline-block;
        margin-top: .8rem;
        padding: .42rem .72rem;
        border-radius: 999px;
        background: rgba(128,128,128,.12);
        font-size: .82rem;
    }

    .ctx-flow {
        text-align: center;
        padding: .7rem 1rem;
        border: 1px solid rgba(128,128,128,.20);
        border-radius: 14px;
        margin-bottom: 1rem;
        opacity: .82;
        font-size: .84rem;
    }

    .ctx-card {
        padding: 1rem 1.05rem;
        border-radius: 16px;
        border: 1px solid rgba(128,128,128,.22);
        margin-bottom: .9rem;
    }

    .ctx-card-title {
        font-size: 1.12rem;
        font-weight: 800;
        margin-bottom: .3rem;
    }

    .ctx-muted {
        font-size: .84rem;
        opacity: .67;
    }

    .ctx-mini {
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,.18);
        padding: .75rem .85rem;
        min-height: 88px;
    }

    .ctx-mini-label {
        font-size: .75rem;
        opacity: .65;
    }

    .ctx-mini-value {
        margin-top: .18rem;
        font-size: 1.55rem;
        font-weight: 800;
    }

    .ctx-status {
        display: inline-block;
        padding: .28rem .6rem;
        border-radius: 999px;
        font-size: .73rem;
        font-weight: 800;
        border: 1px solid rgba(128,128,128,.25);
    }

    .ctx-email-body {
        border-left: 3px solid rgba(77,101,255,.48);
        padding: .55rem .8rem;
        margin: .45rem 0 .8rem;
        background: rgba(128,128,128,.045);
        border-radius: 0 10px 10px 0;
        line-height: 1.62;
        white-space: pre-wrap;
    }

    .ctx-date {
        font-size: 1.18rem;
        font-weight: 850;
    }

    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,.18);
    }

    section[data-testid="stSidebar"] .stRadio label {
        font-size: .93rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# LOAD DATA
# ==========================================================

emails = get_emails()

if (
    st.session_state.analysis is None
    and emails
):
    with st.spinner(
        "Preparing ContextIQ intelligence..."
    ):
        first_analysis = analyze_emails()

    if first_analysis:
        st.session_state.analysis = (
            first_analysis
        )

analysis_results = {}

if st.session_state.analysis:
    for item in st.session_state.analysis.get(
        "results",
        [],
    ):
        if item.get("id") is not None:
            analysis_results[
                item["id"]
            ] = item


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.markdown(
        "## 📧 ContextIQ"
    )

    st.caption(
        "From Inbox Noise to Business Intelligence"
    )

    st.divider()

    st.markdown(
        "**👤 Logged-in User**"
    )

    st.caption(
        current_user()
    )

    st.divider()

    nav_items = [
        "🏠 Dashboard",
        "🧠 Ask ContextIQ",
        "📥 Intelligent Inbox",
        "✅ Action Center",
        "🔥 Opportunity Radar",
        "📅 Calendar",
        "🗂️ CRM Intelligence",
        "🛡️ Security Center",
        "📎 Attachments",
    ]

    nav_values = {
        "🏠 Dashboard": "Dashboard",
        "🧠 Ask ContextIQ": "Ask ContextIQ",
        "📥 Intelligent Inbox": "Intelligent Inbox",
        "✅ Action Center": "Action Center",
        "🔥 Opportunity Radar": "Opportunity Radar",
        "📅 Calendar": "Calendar",
        "🗂️ CRM Intelligence": "CRM Intelligence",
        "🛡️ Security Center": "Security Center",
        "📎 Attachments": "Attachments",
    }

    display_page = next(
        (
            key
            for key, value in nav_values.items()
            if value == st.session_state.page
        ),
        nav_items[0],
    )

    selected = st.radio(
        "Navigation",
        nav_items,
        index=nav_items.index(
            display_page
        ),
    )

    st.session_state.page = nav_values[
        selected
    ]

    st.divider()

    if st.button(
        "🔄 Sync Gmail",
        use_container_width=True,
    ):
        with st.spinner(
            "Syncing Gmail..."
        ):
            result = sync_gmail()

        if result:
            imported = result.get(
                "imported",
                0,
            )

            skipped_value = result.get(
                "skipped",
                [],
            )

            skipped = (
                len(skipped_value)
                if isinstance(
                    skipped_value,
                    list,
                )
                else skipped_value
            )

            st.success(
                f"Imported {imported} • "
                f"Skipped {skipped}"
            )

            st.session_state.analysis = None

            st.rerun()

    if st.button(
        "🧠 Analyze Emails",
        use_container_width=True,
    ):
        with st.spinner(
            "Analyzing inbox..."
        ):
            result = analyze_emails()

        if result:
            st.session_state.analysis = (
                result
            )

            st.success(
                f"Analyzed "
                f"{result.get('processed', 0)} "
                "emails."
            )

            st.rerun()

    if st.button(
        "🔄 Refresh",
        use_container_width=True,
    ):
        st.rerun()

    st.divider()

    if st.button(
        "🚪 Logout",
        use_container_width=True,
    ):
        logout_user()
        st.rerun()


# ==========================================================
# HEADER
# ==========================================================

st.markdown(
    f"""
    <div class="ctx-hero">
        <div class="ctx-eyebrow">
            AI Business Email Intelligence
        </div>
        <div class="ctx-title">
            ContextIQ
        </div>
        <p class="ctx-subtitle">
            From Inbox Noise to Business Intelligence
        </p>
        <div class="ctx-user">
            👤 {current_user()}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ctx-flow">
        Inbox → Understanding → Business Context →
        Consequence → Decision → Action
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# ACTION COUNTS
# ==========================================================

all_actions = []

for email_item in emails:
    for action in get_actions(
        email_item.get("id")
    ):
        enriched = dict(action)
        enriched["_email"] = email_item
        all_actions.append(
            enriched
        )

pending_actions = [
    a for a in all_actions
    if a.get("status") == "pending"
]

approved_actions = [
    a for a in all_actions
    if a.get("status") == "approved"
]

executed_actions = [
    a for a in all_actions
    if a.get("status") == "executed"
]

rejected_actions = [
    a for a in all_actions
    if a.get("status") == "rejected"
]


# ==========================================================
# SHARED EMAIL INTELLIGENCE CARD
# ==========================================================

def render_email_card(
    email_item: dict,
    compact: bool = False,
):
    email_id = email_item.get(
        "id"
    )

    result = analysis_results.get(
        email_id,
        {},
    )

    decision = result.get(
        "decision",
        {},
    ) or {}

    context = result.get(
        "business_context",
        {},
    ) or {}

    consequence = result.get(
        "consequence",
        {},
    ) or {}

    company = (
        context.get("company")
        or {}
    )

    crm = (
        context.get("crm")
        or {}
    )

    opportunity = (
        context.get("opportunity")
        or {}
    )

    body_preview = clean_email_body(
        email_item.get("body"),
        max_chars=900,
    )

    with st.container(
        border=True
    ):
        top = st.columns(
            [4.4, 1.3, 1.3, 1.3]
        )

        with top[0]:
            st.markdown(
                f"### {email_item.get('subject', 'Untitled email')}"
            )

            st.caption(
                f"From: {email_item.get('sender', 'Unknown sender')}"
            )

        with top[1]:
            st.metric(
                "Priority",
                f"{float(email_item.get('priority_score') or 0):.0f}",
            )

        with top[2]:
            st.metric(
                "Impact",
                f"{float(consequence.get('score', email_item.get('consequence_score') or 0)):.0f}",
            )

        with top[3]:
            st.metric(
                "Trust",
                percentage(
                    result.get(
                        "sender_trust",
                        0,
                    )
                ),
            )

        if body_preview:
            st.markdown(
                f"""
                <div class="ctx-email-body">
                    {html.escape(body_preview)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        info = st.columns(3)

        with info[0]:
            st.write(
                "**Intent**"
            )

            st.info(
                title_case(
                    result.get(
                        "intent",
                        email_item.get(
                            "category"
                        ),
                    )
                )
            )

        with info[1]:
            st.write(
                "**Recommended Action**"
            )

            st.info(
                title_case(
                    decision.get(
                        "action_type"
                    )
                )
            )

        with info[2]:
            st.write(
                "**Risk Level**"
            )

            risk = (
                decision.get(
                    "risk_level",
                    "LOW",
                )
            )

            if risk == "HIGH":
                st.error(risk)
            elif risk == "MEDIUM":
                st.warning(risk)
            else:
                st.success(risk)

        if compact:
            return

        st.divider()

        st.markdown(
            "#### 🔗 Business Context Graph"
        )

        context_cols = st.columns(4)

        with context_cols[0]:
            st.markdown(
                "**Contact**"
            )

            contact = (
                context.get("contact")
                or {}
            )

            st.write(
                contact.get(
                    "name",
                    "Unknown",
                )
            )

            st.caption(
                contact.get(
                    "email",
                    "",
                )
            )

            st.write(
                contact.get(
                    "company",
                    company.get(
                        "name",
                        "Not linked",
                    ),
                )
            )

        with context_cols[1]:
            st.markdown(
                "**Company**"
            )

            st.write(
                company.get(
                    "name",
                    "Not linked",
                )
            )

            st.caption(
                company.get(
                    "industry",
                    "Industry not available",
                )
            )

        with context_cols[2]:
            st.markdown(
                "**CRM Account**"
            )

            st.write(
                money(
                    crm.get(
                        "deal_value"
                    )
                )
            )

            st.caption(
                f"Stage: "
                f"{crm.get('stage', 'Unknown')}"
            )

            st.caption(
                f"Status: "
                f"{crm.get('status', 'Unknown')}"
            )

        with context_cols[3]:
            st.markdown(
                "**Opportunity**"
            )

            st.write(
                opportunity.get(
                    "title",
                    "No linked opportunity",
                )
            )

            if opportunity.get(
                "value"
            ):
                st.caption(
                    money(
                        opportunity.get(
                            "value"
                        )
                    )
                )

            st.caption(
                f"Risk: "
                f"{opportunity.get('risk_level', 'Unknown')}"
            )

        st.markdown(
            "#### ⚠️ Consequence Intelligence"
        )

        consequence_cols = st.columns(
            4
        )

        consequence_cols[0].metric(
            "Business Impact",
            f"{consequence.get('score', 0)}/100",
        )

        consequence_cols[1].metric(
            "Revenue at Risk",
            money(
                consequence.get(
                    "potential_revenue_at_risk"
                )
            ),
        )

        consequence_cols[2].metric(
            "Deadline",
            (
                f"{consequence.get('deadline_hours')}h"
                if consequence.get(
                    "deadline_hours"
                ) is not None
                else "—"
            ),
        )

        consequence_cols[3].metric(
            "Deal Value",
            money(
                consequence.get(
                    "deal_value"
                )
                or crm.get(
                    "deal_value"
                )
            ),
        )

        for reason in consequence.get(
            "reasons",
            [],
        ):
            st.write(
                f"✓ {reason}"
            )

        dependency = result.get(
            "process_dependency",
            {},
        ) or {}

        st.markdown(
            "#### 🚧 Process Dependency"
        )

        if dependency.get(
            "is_blocking"
        ):
            st.warning(
                "This email is blocking a downstream process."
            )

            st.write(
                f"**Process:** "
                f"{dependency.get('blocked_process', 'Unknown')}"
            )

            st.write(
                f"**Impact:** "
                f"{dependency.get('downstream_impact', 'Unknown')}"
            )
        else:
            st.success(
                "No downstream process dependency detected."
            )

        calendar = context.get(
            "calendar",
            {},
        ) or {}

        st.markdown(
            "#### 📅 Calendar Intelligence"
        )

        if calendar.get(
            "meeting_requested"
        ):
            st.info(
                "This sender is requesting a meeting, call, demo, or discussion."
            )

            slot = calendar.get(
                "available_slot"
            )

            if slot:
                st.write(
                    f"**Suggested:** "
                    f"{slot.get('date')} · "
                    f"{slot.get('start')}–"
                    f"{slot.get('end')}"
                )
        else:
            st.caption(
                "No meeting request detected in this email."
            )

        st.markdown(
            "#### 🤖 Explainable Decision"
        )

        decision_cols = st.columns(
            3
        )

        decision_cols[0].write(
            title_case(
                decision.get(
                    "action_type"
                )
            )
        )

        decision_cols[1].metric(
            "Confidence",
            percentage(
                decision.get(
                    "confidence",
                    0,
                )
            ),
        )

        decision_cols[2].write(
            f"Risk: **{decision.get('risk_level', 'LOW')}**"
        )

        st.caption(
            decision.get(
                "reason",
                "No decision explanation available.",
            )
        )

        insight = st.session_state.business_insights.get(
            email_id
        )

        st.markdown(
            "#### 🧠 RAG + Gemini Business Insight"
        )

        if insight:
            provider = insight.get(
                "provider",
                "unknown",
            )

            model = insight.get(
                "model",
                "unknown",
            )

            st.caption(
                f"Provider: {provider} · Model: {model}"
            )

            st.write(
                insight.get(
                    "message",
                    "No insight available.",
                )
            )

        if st.button(
            "✨ Generate Business Insight",
            key=f"insight_{email_id}",
            use_container_width=True,
        ):
            with st.spinner(
                "Retrieving history and asking Gemini..."
            ):
                try:
                    rag_result = run_rag(
                        current_email=dict(
                            email_item
                        ),
                        all_emails=emails,
                        top_k=3,
                    )

                    analysis_for_llm = dict(
                        result
                    )

                    analysis_for_llm["rag"] = {
                        "retrieved_count": (
                            rag_result.get(
                                "retrieved_count",
                                0,
                            )
                        )
                    }

                    llm_result = (
                        generate_business_insight(
                            email=dict(
                                email_item
                            ),
                            analysis=analysis_for_llm,
                            rag_context=rag_result.get(
                                "context",
                                "",
                            ),
                        )
                    )

                    llm_result[
                        "retrieved_count"
                    ] = rag_result.get(
                        "retrieved_count",
                        0,
                    )

                    st.session_state.business_insights[
                        email_id
                    ] = llm_result

                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Business insight generation failed: {error}"
                    )


# ==========================================================
# DASHBOARD
# ==========================================================

def dashboard_page():
    total = len(emails)

    priority_count = sum(
        (
            e.get(
                "priority_score"
            )
            or 0
        ) >= 70
        for e in emails
    )

    lead_count = sum(
        e.get("category") in {
            "sales",
            "sales_inquiry",
            "customer_renewal",
            "product_demo",
            "partnership",
        }
        for e in emails
    )

    threat_count = sum(
        (
            e.get(
                "spam_score"
            )
            or 0
        ) >= 0.70
        for e in emails
    )

    impact_count = sum(
        (
            e.get(
                "consequence_score"
            )
            or 0
        ) >= 80
        for e in emails
    )

    cols = st.columns(
        7
    )

    metrics = [
        ("Total Emails", total),
        ("High Priority", priority_count),
        ("Business Leads", lead_count),
        ("Threats", threat_count),
        ("High Impact", impact_count),
        ("Pending", len(pending_actions)),
        ("Executed", len(executed_actions)),
    ]

    for col, (
        label,
        value,
    ) in zip(
        cols,
        metrics,
    ):
        with col:
            st.markdown(
                f"""
                <div class="ctx-mini">
                    <div class="ctx-mini-label">
                        {label}
                    </div>
                    <div class="ctx-mini-value">
                        {value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    st.markdown(
        "### 🚨 Business Attention Queue"
    )

    attention = []

    for email_item in emails:
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        consequence = result.get(
            "consequence",
            {},
        ) or {}

        impact = consequence.get(
            "score",
            email_item.get(
                "consequence_score"
            )
            or 0,
        )

        if (
            impact >= 80
            or (
                email_item.get(
                    "priority_score"
                )
                or 0
            ) >= 80
        ):
            attention.append(
                (
                    float(
                        impact
                        or 0
                    ),
                    email_item,
                    result,
                )
            )

    attention.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    if not attention:
        st.success(
            "No high-impact emails currently require attention."
        )
    else:
        for impact, email_item, result in attention[:5]:
            decision = result.get(
                "decision",
                {},
            ) or {}

            with st.container(
                border=True
            ):
                c1, c2, c3 = st.columns(
                    [4, 1.4, 2]
                )

                with c1:
                    st.markdown(
                        f"### {email_item.get('subject', 'Untitled')}"
                    )
                    st.caption(
                        email_item.get(
                            "sender",
                            "Unknown sender",
                        )
                    )

                with c2:
                    st.metric(
                        "Impact",
                        f"{impact:.0f}/100",
                    )

                with c3:
                    st.write(
                        "**Recommended Action**"
                    )
                    st.info(
                        title_case(
                            decision.get(
                                "action_type"
                            )
                        )
                    )


# ==========================================================
# INTELLIGENT INBOX
# ==========================================================

def inbox_page():
    st.title(
        "📥 Intelligent Inbox"
    )

    st.caption(
        "The inbox ranked by business meaning, risk, consequence, and action."
    )

    if not emails:
        st.info(
            "No emails found for this user."
        )
        return

    sort_mode = st.selectbox(
        "Rank emails by",
        [
            "Business Impact",
            "Priority",
            "Newest",
        ],
    )

    def sort_key(
        email_item,
    ):
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        if sort_mode == "Business Impact":
            consequence = result.get(
                "consequence",
                {},
            ) or {}

            return (
                consequence.get(
                    "score",
                    email_item.get(
                        "consequence_score"
                    )
                    or 0,
                )
                or 0
            )

        if sort_mode == "Priority":
            return (
                email_item.get(
                    "priority_score"
                )
                or 0
            )

        return (
            email_item.get(
                "received_at",
                "",
            )
        )

    ordered = sorted(
        emails,
        key=sort_key,
        reverse=True,
    )

    for email_item in ordered:
        render_email_card(
            email_item,
            compact=True,
        )

        with st.expander(
            "Open full intelligence"
        ):
            render_email_card(
                email_item,
                compact=False,
            )


# ==========================================================
# ACTION CENTER
# ==========================================================

def action_center_page():
    st.title(
        "✅ Action Center"
    )

    st.caption(
        "Every recommendation follows a controlled approval → execution workflow."
    )

    stats = st.columns(
        4
    )

    stats[0].metric(
        "Pending Approval",
        len(pending_actions),
    )

    stats[1].metric(
        "Approved",
        len(approved_actions),
    )

    stats[2].metric(
        "Executed",
        len(executed_actions),
    )

    stats[3].metric(
        "Rejected",
        len(rejected_actions),
    )

    st.divider()

    if not all_actions:
        st.success(
            "No AI actions have been generated yet."
        )
        return

    st.markdown(
        "### ⏳ Pending / Ready to Execute"
    )

    visible = [
        action
        for action in all_actions
        if action.get("status")
        in {
            "pending",
            "approved",
        }
    ]

    if not visible:
        st.success(
            "Nothing is waiting for approval or execution."
        )

    for action in visible:
        email_item = action[
            "_email"
        ]

        status = action.get(
            "status",
            "unknown",
        )

        with st.container(
            border=True
        ):
            c1, c2, c3 = st.columns(
                [4, 1.4, 1.6]
            )

            with c1:
                st.markdown(
                    f"### {email_item.get('subject', 'Untitled')}"
                )

                st.caption(
                    email_item.get(
                        "sender",
                        "Unknown sender",
                    )
                )

                st.write(
                    f"**Action:** "
                    f"{title_case(action.get('action_type'))}"
                )

                st.write(
                    action.get(
                        "reason",
                        "",
                    )
                )

            with c2:
                if status == "pending":
                    st.warning(
                        "PENDING"
                    )
                elif status == "approved":
                    st.info(
                        "APPROVED"
                    )

            with c3:
                st.metric(
                    "Confidence",
                    percentage(
                        action.get(
                            "confidence",
                            0,
                        )
                    ),
                )

            if status == "pending":
                a1, a2 = st.columns(
                    2
                )

                with a1:
                    if st.button(
                        "✅ Approve",
                        key=f"approve_{action['id']}",
                        use_container_width=True,
                    ):
                        result = approve_action(
                            email_item["id"],
                            action["id"],
                        )

                        if result:
                            st.success(
                                "Approved. The action is now ready to execute."
                            )
                            st.rerun()

                with a2:
                    if st.button(
                        "❌ Reject",
                        key=f"reject_{action['id']}",
                        use_container_width=True,
                    ):
                        result = reject_action(
                            email_item["id"],
                            action["id"],
                        )

                        if result:
                            st.warning(
                                "Action rejected."
                            )
                            st.rerun()

            elif status == "approved":
                st.success(
                    "Approval received. Execute the action when ready."
                )

                if st.button(
                    "▶️ Execute Action",
                    key=f"execute_{action['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    with st.spinner(
                        "Executing approved action..."
                    ):
                        result = execute_action(
                            email_item["id"],
                            action["id"],
                        )

                    if result:
                        st.success(
                            result.get(
                                "message",
                                "Action executed successfully.",
                            )
                        )
                        st.rerun()

    st.divider()

    st.markdown(
        "### ✅ Execution History"
    )

    if not executed_actions:
        st.info(
            "No action has been executed yet."
        )
    else:
        for action in executed_actions:
            email_item = action[
                "_email"
            ]

            with st.container(
                border=True
            ):
                c1, c2 = st.columns(
                    [4, 2]
                )

                with c1:
                    st.markdown(
                        f"**{title_case(action.get('action_type'))}**"
                    )
                    st.caption(
                        f"{email_item.get('subject', 'Untitled')} · "
                        f"{email_item.get('sender', '')}"
                    )

                with c2:
                    st.success(
                        "EXECUTED"
                    )


# ==========================================================
# OPPORTUNITY RADAR
# ==========================================================

def opportunity_page():
    st.title(
        "🔥 Opportunity Radar"
    )

    st.caption(
        "A revenue-focused view of opportunities discovered from email + CRM context."
    )

    opportunities = []
    seen = set()

    for email_item in emails:
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        context = result.get(
            "business_context",
            {},
        ) or {}

        opportunity = context.get(
            "opportunity"
        ) or {}

        crm = context.get(
            "crm"
        ) or {}

        company = context.get(
            "company"
        ) or {}

        if not opportunity:
            continue

        key = (
            opportunity.get(
                "id"
            ),
            opportunity.get(
                "company_name"
            )
            or company.get(
                "name"
            ),
            opportunity.get(
                "title"
            ),
        )

        if key in seen:
            continue

        seen.add(key)

        value = (
            opportunity.get(
                "value"
            )
            or crm.get(
                "deal_value"
            )
            or 0
        )

        impact = (
            result.get(
                "consequence",
                {},
            ) or {}
        ).get(
            "score",
            0,
        )

        opportunities.append(
            {
                "company": (
                    opportunity.get(
                        "company_name"
                    )
                    or company.get(
                        "name"
                    )
                    or "Unknown company"
                ),
                "title": opportunity.get(
                    "title",
                    "Opportunity",
                ),
                "value": value,
                "stage": opportunity.get(
                    "stage",
                    "Unknown",
                ),
                "risk": opportunity.get(
                    "risk_level",
                    "MEDIUM",
                ),
                "impact": impact,
                "contact": crm.get(
                    "contact_name",
                    "Unknown",
                ),
            }
        )

    opportunities.sort(
        key=lambda item: (
            item["impact"],
            item["value"],
        ),
        reverse=True,
    )

    summary = st.columns(
        4
    )

    summary[0].metric(
        "Tracked Opportunities",
        len(opportunities),
    )

    summary[1].metric(
        "Pipeline Value",
        money(
            sum(
                float(
                    item["value"]
                    or 0
                )
                for item in opportunities
            )
        ),
    )

    summary[2].metric(
        "High-Risk",
        sum(
            item["risk"] == "HIGH"
            for item in opportunities
        ),
    )

    summary[3].metric(
        "High Impact",
        sum(
            float(
                item["impact"]
                or 0
            ) >= 80
            for item in opportunities
        ),
    )

    st.divider()

    if not opportunities:
        st.info(
            "No linked opportunities are currently available."
        )
        return

    for item in opportunities:
        with st.container(
            border=True
        ):
            c1, c2, c3 = st.columns(
                [3.2, 2.2, 2.2]
            )

            with c1:
                st.markdown(
                    f"### {item['company']}"
                )
                st.write(
                    item["title"]
                )
                st.caption(
                    f"Contact: {item['contact']}"
                )

            with c2:
                st.metric(
                    "Opportunity Value",
                    money(
                        item["value"]
                    ),
                )
                st.caption(
                    f"Stage: {item['stage']}"
                )

            with c3:
                st.metric(
                    "Business Impact",
                    f"{item['impact']}/100",
                )

                if item["risk"] == "HIGH":
                    st.error(
                        "HIGH RISK"
                    )
                elif item["risk"] == "MEDIUM":
                    st.warning(
                        "MEDIUM RISK"
                    )
                else:
                    st.success(
                        "LOW RISK"
                    )


# ==========================================================
# CALENDAR INTELLIGENCE
# ==========================================================

def calendar_page():
    st.title(
        "📅 Calendar Intelligence"
    )

    st.caption(
        "Meeting dates, suggested slots, and the company context extracted from the email requesting the meeting."
    )

    stored_events = get_calendar_events()

    # ------------------------------------------------------
    # EMAIL-DERIVED MEETING REQUESTS
    # ------------------------------------------------------

    meeting_requests = []

    for email_item in emails:
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        context = result.get(
            "business_context",
            {},
        ) or {}

        calendar = context.get(
            "calendar",
            {},
        ) or {}

        if not calendar.get(
            "meeting_requested"
        ):
            continue

        company = (
            context.get(
                "company"
            )
            or {}
        )

        contact = (
            context.get(
                "contact"
            )
            or {}
        )

        crm = (
            context.get(
                "crm"
            )
            or {}
        )

        slot = calendar.get(
            "available_slot"
        ) or {}

        meeting_requests.append(
            {
                "subject": email_item.get(
                    "subject",
                    "Meeting request",
                ),
                "sender": email_item.get(
                    "sender",
                    "Unknown sender",
                ),
                "company": company.get(
                    "name",
                    contact.get(
                        "company",
                        "Company not detected",
                    ),
                ),
                "contact": contact.get(
                    "name",
                    crm.get(
                        "contact_name",
                        "Contact not detected",
                    ),
                ),
                "email": contact.get(
                    "email",
                    email_item.get(
                        "sender",
                        "",
                    ),
                ),
                "date": slot.get(
                    "date"
                ),
                "start": slot.get(
                    "start"
                ),
                "end": slot.get(
                    "end"
                ),
                "stage": crm.get(
                    "stage"
                ),
                "deal_value": crm.get(
                    "deal_value"
                ),
            }
        )

    st.markdown(
        "### 📨 Meeting Requests Detected in Email"
    )

    if meeting_requests:
        for meeting in meeting_requests:
            with st.container(
                border=True
            ):
                top = st.columns(
                    [2.5, 1.2, 1.3, 2]
                )

                with top[0]:
                    st.markdown(
                        f"### {meeting['subject']}"
                    )
                    st.caption(
                        f"Requested by {meeting['contact']} "
                        f"· {meeting['email']}"
                    )

                with top[1]:
                    st.write(
                        "**Company**"
                    )
                    st.write(
                        meeting["company"]
                    )

                with top[2]:
                    st.write(
                        "**Date**"
                    )
                    st.write(
                        meeting["date"]
                        or "Suggested"
                    )

                with top[3]:
                    if meeting["start"]:
                        st.metric(
                            "Suggested Time",
                            f"{meeting['start']}–{meeting['end']}",
                        )
                    else:
                        st.info(
                            "Time not specified"
                        )

                details = st.columns(
                    3
                )

                with details[0]:
                    st.caption(
                        "CRM Stage"
                    )
                    st.write(
                        meeting["stage"]
                        or "Not linked"
                    )

                with details[1]:
                    st.caption(
                        "Account Value"
                    )
                    st.write(
                        money(
                            meeting[
                                "deal_value"
                            ]
                        )
                    )

                with details[2]:
                    st.caption(
                        "Source"
                    )
                    st.write(
                        "Email intelligence"
                    )
    else:
        st.info(
            "No meeting requests were detected in the analyzed emails."
        )

    st.divider()

    # ------------------------------------------------------
    # STORED CALENDAR
    # ------------------------------------------------------

    st.markdown(
        "### 🗓️ Stored Calendar Events"
    )

    if not stored_events:
        st.info(
            "No stored calendar events match this user yet."
        )

        if meeting_requests:
            st.success(
                "Meeting requests were still detected from email context above."
            )

        return

    events_by_date = {}

    for event in stored_events:
        event_date = event.get(
            "event_date",
            "",
        )

        date_key = (
            event_date[:10]
            if event_date
            else "Unknown date"
        )

        events_by_date.setdefault(
            date_key,
            [],
        ).append(
            event
        )

    for date_key in sorted(
        events_by_date
    ):
        st.markdown(
            f"### {date_key}"
        )

        for event in events_by_date[
            date_key
        ]:
            with st.container(
                border=True
            ):
                c1, c2, c3 = st.columns(
                    [3, 2, 2]
                )

                with c1:
                    st.markdown(
                        f"**{event.get('title', 'Untitled')}**"
                    )
                    st.caption(
                        f"Owner: {event.get('owner', 'Unknown')}"
                    )

                with c2:
                    st.write(
                        f"Start: {event.get('event_date', '—')}"
                    )
                    st.write(
                        f"End: {event.get('end_date', '—')}"
                    )

                with c3:
                    st.write(
                        "Attendees"
                    )
                    st.caption(
                        event.get(
                            "attendees",
                            "—",
                        )
                    )

                    st.write(
                        f"Status: {event.get('status', 'Unknown')}"
                    )


# ==========================================================
# CRM INTELLIGENCE
# ==========================================================

def crm_page():
    st.title(
        "🗂️ CRM Intelligence"
    )

    st.caption(
        "A dedicated account view connecting companies, contacts, deal value, stages, risks, and related email context."
    )

    accounts = {}
    seen_opportunities = {}

    for email_item in emails:
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        context = result.get(
            "business_context",
            {},
        ) or {}

        company = (
            context.get(
                "company"
            )
            or {}
        )

        crm = (
            context.get(
                "crm"
            )
            or {}
        )

        opportunity = (
            context.get(
                "opportunity"
            )
            or {}
        )

        if not crm and not company:
            continue

        company_name = (
            company.get(
                "name"
            )
            or crm.get(
                "company_name"
            )
            or opportunity.get(
                "company_name"
            )
        )

        if not company_name:
            continue

        record = accounts.setdefault(
            company_name,
            {
                "company": company,
                "crm": crm,
                "contacts": set(),
                "opportunities": [],
                "emails": [],
                "highest_impact": 0,
            },
        )

        contact = context.get(
            "contact"
        ) or {}

        contact_email = contact.get(
            "email"
        )

        contact_name = contact.get(
            "name"
        )

        if contact_email or contact_name:
            record["contacts"].add(
                (
                    contact_name
                    or "Unknown",
                    contact_email
                    or "",
                )
            )

        record["emails"].append(
            email_item
        )

        impact = (
            result.get(
                "consequence",
                {},
            ) or {}
        ).get(
            "score",
            0,
        )

        record["highest_impact"] = max(
            record[
                "highest_impact"
            ],
            float(
                impact
                or 0
            ),
        )

        if opportunity:
            opportunity_key = (
                opportunity.get(
                    "id"
                ),
                opportunity.get(
                    "title"
                ),
            )

            if opportunity_key not in seen_opportunities.get(
                company_name,
                set(),
            ):
                seen_opportunities.setdefault(
                    company_name,
                    set(),
                ).add(
                    opportunity_key
                )

                record[
                    "opportunities"
                ].append(
                    opportunity
                )

    st.markdown(
        "### 📊 Account Portfolio"
    )

    total_accounts = len(
        accounts
    )

    total_deal_value = sum(
        float(
            (
                item["crm"].get(
                    "deal_value"
                )
                or 0
            )
        )
        for item in accounts.values()
    )

    high_impact_accounts = sum(
        item["highest_impact"] >= 80
        for item in accounts.values()
    )

    stats = st.columns(
        3
    )

    stats[0].metric(
        "Accounts",
        total_accounts,
    )

    stats[1].metric(
        "Visible Deal Value",
        money(
            total_deal_value
        ),
    )

    stats[2].metric(
        "High-Impact Accounts",
        high_impact_accounts,
    )

    st.divider()

    if not accounts:
        st.info(
            "No CRM accounts are linked to the analyzed inbox yet."
        )
        return

    for company_name, item in sorted(
        accounts.items()
    ):
        crm = item["crm"]
        company = item["company"]

        with st.container(
            border=True
        ):
            st.markdown(
                f"## {company_name}"
            )

            header = st.columns(
                [2.2, 1.5, 1.5, 1.5]
            )

            with header[0]:
                st.caption(
                    "Industry"
                )
                st.write(
                    company.get(
                        "industry",
                        "Not available",
                    )
                )

            with header[1]:
                st.caption(
                    "Deal Value"
                )
                st.write(
                    money(
                        crm.get(
                            "deal_value"
                        )
                    )
                )

            with header[2]:
                st.caption(
                    "Stage"
                )
                st.write(
                    crm.get(
                        "stage",
                        "Unknown",
                    )
                )

            with header[3]:
                st.caption(
                    "Status"
                )
                st.write(
                    crm.get(
                        "status",
                        "Unknown",
                    )
                )

            st.markdown(
                "### 👥 Contacts"
            )

            contacts = sorted(
                item["contacts"]
            )

            if contacts:
                for name, email_address in contacts:
                    st.write(
                        f"**{name}** · {email_address}"
                    )
            else:
                st.caption(
                    "No contact record connected."
                )

            if item["opportunities"]:
                st.markdown(
                    "### 🔥 Opportunities"
                )

                for opportunity in item[
                    "opportunities"
                ]:
                    c1, c2, c3 = st.columns(
                        [3, 1.5, 1.5]
                    )

                    with c1:
                        st.write(
                            f"**{opportunity.get('title', 'Opportunity')}**"
                        )

                    with c2:
                        st.write(
                            money(
                                opportunity.get(
                                    "value"
                                )
                            )
                        )

                    with c3:
                        st.write(
                            f"Risk: {opportunity.get('risk_level', 'Unknown')}"
                        )

            st.markdown(
                "### 📧 Related Email Activity"
            )

            st.write(
                f"{len(item['emails'])} related email(s) "
                f"connected to this account."
            )

            st.caption(
                f"Highest observed business impact: "
                f"{item['highest_impact']:.0f}/100"
            )


# ==========================================================
# SECURITY CENTER
# ==========================================================

def security_page():
    st.title(
        "🛡️ Security Center"
    )

    st.caption(
        "A focused threat posture view for spam, phishing, sender trust, and security review."
    )

    threat_items = []

    for email_item in emails:
        result = analysis_results.get(
            email_item.get("id"),
            {},
        )

        spam = float(
            result.get(
                "spam_score",
                email_item.get(
                    "spam_score"
                )
                or 0,
            )
            or 0
        )

        phishing = float(
            result.get(
                "phishing_score",
                0,
            )
            or 0
        )

        trust = float(
            result.get(
                "sender_trust",
                0,
            )
            or 0
        )

        threat_score = max(
            spam,
            phishing,
            1 - trust,
        )

        if (
            threat_score >= 0.40
        ):
            threat_items.append(
                (
                    threat_score,
                    email_item,
                    result,
                    spam,
                    phishing,
                    trust,
                )
            )

    threat_items.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    cards = st.columns(
        4
    )

    cards[0].metric(
        "Emails Requiring Review",
        len(threat_items),
    )

    cards[1].metric(
        "High Threat",
        sum(
            item[0] >= .80
            for item in threat_items
        ),
    )

    cards[2].metric(
        "Medium Threat",
        sum(
            .50 <= item[0] < .80
            for item in threat_items
        ),
    )

    cards[3].metric(
        "Low Sender Trust",
        sum(
            item[5] < .50
            for item in threat_items
        ),
    )

    st.divider()

    if not threat_items:
        st.success(
            "No significant security issues require review."
        )
        return

    for (
        threat_score,
        email_item,
        result,
        spam,
        phishing,
        trust,
    ) in threat_items:

        with st.container(
            border=True
        ):
            st.markdown(
                f"### {email_item.get('subject', 'Suspicious email')}"
            )

            st.caption(
                email_item.get(
                    "sender",
                    "Unknown sender",
                )
            )

            cols = st.columns(
                3
            )

            cols[0].metric(
                "Spam",
                percentage(
                    spam
                ),
            )

            cols[1].metric(
                "Phishing",
                percentage(
                    phishing
                ),
            )

            cols[2].metric(
                "Sender Trust",
                percentage(
                    trust
                ),
            )

            if phishing >= .80:
                st.error(
                    "🚨 HIGH PHISHING RISK — Security review required before interaction."
                )

            elif spam >= .80:
                st.error(
                    "🚨 HIGH SPAM RISK — Keep isolated until reviewed."
                )

            elif trust < .50:
                st.warning(
                    "⚠️ Low sender trust — verify identity before acting."
                )

            else:
                st.info(
                    "Manual security review recommended."
                )

            st.caption(
                f"Overall threat score: {threat_score * 100:.0f}%"
            )

            st.markdown(
                "#### Email Preview"
            )

            st.write(
                clean_email_body(
                    email_item.get(
                        "body"
                    ),
                    max_chars=500,
                )
            )


# ==========================================================
# ATTACHMENT INTELLIGENCE
# ==========================================================

def parse_business_information(
    value,
) -> dict:
    if not value:
        return {}

    if isinstance(
        value,
        dict,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        try:
            parsed = json.loads(
                value
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except Exception:
            return {
                "details": value
            }

    return {
        "details": str(
            value
        )
    }


def render_attachments():
    st.title(
        "📎 Attachment Intelligence"
    )

    st.caption(
        "Every document is connected to its source email, risk profile, business information, and extracted summary."
    )

    attachment_rows = []

    for email_item in emails:
        for attachment in get_attachments(
            email_item.get("id")
        ):
            row = dict(
                attachment
            )

            row[
                "email_subject"
            ] = email_item.get(
                "subject",
                "Untitled email",
            )

            row[
                "sender"
            ] = email_item.get(
                "sender",
                "Unknown sender",
            )

            attachment_rows.append(
                row
            )

    summary_cols = st.columns(
        3
    )

    summary_cols[0].metric(
        "Documents",
        len(attachment_rows),
    )

    summary_cols[1].metric(
        "High-Risk",
        sum(
            float(
                item.get(
                    "attachment_risk"
                )
                or 0
            ) >= .70
            for item in attachment_rows
        ),
    )

    summary_cols[2].metric(
        "Formats",
        len(
            {
                str(
                    item.get(
                        "file_type",
                        "",
                    )
                ).lower()
                for item in attachment_rows
                if item.get(
                    "file_type"
                )
            }
        ),
    )

    st.divider()

    if not attachment_rows:
        st.info(
            "No analyzed attachments are currently available."
        )
        return

    for index, item in enumerate(
        attachment_rows
    ):
        risk = float(
            item.get(
                "attachment_risk"
            )
            or 0
        )

        business = parse_business_information(
            item.get(
                "business_information"
            )
        )

        with st.container(
            border=True
        ):
            top = st.columns(
                [3.4, 1.4, 1.6]
            )

            with top[0]:
                st.markdown(
                    f"### 📄 {item.get('filename', 'Unnamed file')}"
                )

                st.caption(
                    f"From: {item.get('sender', 'Unknown sender')}"
                )

                st.caption(
                    f"Email: {item.get('email_subject', 'Untitled email')}"
                )

            with top[1]:
                st.write(
                    "**Type**"
                )
                st.info(
                    str(
                        item.get(
                            "file_type",
                            "Unknown",
                        )
                    ).upper()
                )

            with top[2]:
                st.metric(
                    "Risk",
                    percentage(
                        risk
                    ),
                )

            if risk >= .70:
                st.error(
                    "High attachment risk"
                )
            elif risk >= .40:
                st.warning(
                    "Moderate attachment risk"
                )
            else:
                st.success(
                    "Low attachment risk"
                )

            if business:
                st.markdown(
                    "#### 🧾 Extracted Business Information"
                )

                business_cols = st.columns(
                    min(
                        3,
                        max(
                            1,
                            len(
                                business
                            )
                        ),
                    )
                )

                for col, (
                    key,
                    value,
                ) in zip(
                    business_cols,
                    business.items(),
                ):
                    with col:
                        st.caption(
                            title_case(
                                key
                            )
                        )
                        st.write(
                            str(
                                value
                            )
                        )

            summary = clean_email_body(
                item.get(
                    "summary"
                )
            )

            if summary:
                st.markdown(
                    "#### 📝 Extracted Summary"
                )

                st.write(
                    summary
                )

            extracted_text = clean_email_body(
                item.get(
                    "extracted_text"
                ),
                max_chars=1800,
            )

            if extracted_text:
                with st.expander(
                    "View extracted document text"
                ):
                    st.write(
                        extracted_text
                    )

            file_path = item.get(
                "file_path"
            )

            try:
                path = (
                    Path(
                        str(
                            file_path
                        )
                    )
                    if file_path
                    else None
                )

                if (
                    path
                    and path.exists()
                    and path.is_file()
                ):
                    with open(
                        path,
                        "rb",
                    ) as document:
                        st.download_button(
                            "⬇️ Download Document",
                            data=document.read(),
                            file_name=(
                                item.get(
                                    "filename"
                                )
                                or path.name
                            ),
                            key=(
                                f"download_attachment_{item.get('id', index)}"
                            ),
                            use_container_width=True,
                        )

            except (
                OSError,
                ValueError,
            ):
                pass


# ==========================================================
# ASK CONTEXTIQ
# ==========================================================

def ask_contextiq_page():
    st.markdown("## 🧠 Ask ContextIQ")
    st.caption("Ask decision-oriented questions across your connected email, documents, CRM, opportunities, contacts, companies, and calendar. Answers are grounded in retrieved evidence.")

    suggestions = [
        "What should I prioritize today?",
        "Which revenue or customer relationships appear at risk?",
        "Which customers are waiting for a response?",
        "What should I prepare for my upcoming meetings?",
    ]
    cols = st.columns(2)
    for index, suggestion in enumerate(suggestions):
        with cols[index % 2]:
            if st.button(suggestion, key=f"ask_suggestion_{index}", use_container_width=True):
                st.session_state["assistant_question"] = suggestion

    question = st.text_area(
        "Business question",
        value=st.session_state.get("assistant_question", ""),
        placeholder="Example: What deals are most at risk and why?",
        height=110,
    )

    if st.button("Ask ContextIQ →", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Enter a business question first.")
        else:
            with st.spinner("Retrieving evidence and reasoning across your business context..."):
                result = api_post(
                    "/assistant/ask",
                    json_body={"question": question.strip(), "top_k": 8},
                    timeout=180,
                )
            if result:
                st.session_state["assistant_result"] = result
                st.session_state["assistant_question"] = question.strip()

    result = st.session_state.get("assistant_result")
    if not result:
        st.info("Sync Gmail or seed the demo workspace, then ask a question. ContextIQ will show the evidence behind its answer.")
        return

    with st.container(border=True):
        st.markdown("### ContextIQ answer")
        st.write(result.get("answer", ""))
        metrics = st.columns(3)
        metrics[0].metric("Confidence", percentage(result.get("confidence", 0)))
        metrics[1].metric("Evidence", len(result.get("evidence", [])))
        metrics[2].metric("Knowledge items", result.get("document_count", 0))
        st.caption(f"Reasoning: {result.get('provider', 'local')} • Retrieval: {result.get('retrieval_model', 'unknown')}")

        next_steps = result.get("recommended_next_steps") or []
        if next_steps:
            st.markdown("#### Recommended next steps")
            for item in next_steps:
                st.write(f"• {item}")

    st.markdown("### Evidence")
    used = set(result.get("used_evidence") or [])
    for item in result.get("evidence", []):
        label = f"{item.get('evidence_id')} · {title_case(item.get('source_type'))} · {item.get('title')}"
        with st.expander(("✅ " if item.get("evidence_id") in used else "") + label):
            st.write(item.get("excerpt", ""))
            st.caption(f"Hybrid relevance: {float(item.get('score') or 0):.3f}")


# ==========================================================
# ROUTING
# ==========================================================

pages = {
    "Dashboard": dashboard_page,
    "Ask ContextIQ": ask_contextiq_page,
    "Intelligent Inbox": inbox_page,
    "Action Center": action_center_page,
    "Opportunity Radar": opportunity_page,
    "Calendar": calendar_page,
    "CRM Intelligence": crm_page,
    "Security Center": security_page,
    "Attachments": render_attachments,
}

pages.get(
    st.session_state.page,
    dashboard_page,
)()
