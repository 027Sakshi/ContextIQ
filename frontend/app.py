from pathlib import Path
import os
import sys
import json
import re
import html
import time
from datetime import datetime
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st

from frontend.theme import apply_app_theme
from frontend.auth import (
    initialize_auth,
    show_login_page,
    logout_user,
    google_oauth_configured,
    google_workspace_connected,
    create_google_authorization_url,
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
    page_icon="◈",
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


def render_html_fragment(value: str) -> None:
    """Render app-owned HTML without Markdown treating indentation as code."""
    fragment = re.sub(r">\s+<", "><", str(value).strip())
    st.markdown(fragment, unsafe_allow_html=True)


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

def _api_error(response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            return str(payload["detail"])
    except Exception:
        pass
    return f"Request failed with status {response.status_code}."


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
        if not response.ok:
            message = _api_error(response)
            if response.status_code in {401, 403, 409}:
                st.warning(message)
            else:
                st.error(message)
            return None
        return response.json()
    except requests.RequestException as error:
        st.error(f"ContextIQ backend is unavailable: {error}")
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
        if not response.ok:
            message = _api_error(response)
            if response.status_code in {401, 403, 409}:
                st.warning(message)
            else:
                st.error(message)
            return None
        return response.json()
    except requests.RequestException as error:
        st.error(f"ContextIQ backend is unavailable: {error}")
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


def get_commitments():
    return api_get("/commitments/?status=open", timeout=30) or []


def complete_commitment(commitment_id: int):
    return api_post(f"/commitments/{commitment_id}/complete", timeout=30)


def generate_email_insight(email_id: int, analysis: dict):
    return api_post(
        f"/emails/{email_id}/insight",
        json_body={"analysis": analysis},
        timeout=35,
    )


def suggest_reply(email_id: int):
    return api_post(f"/emails/{email_id}/reply/suggest", timeout=60)


def create_reply_draft(email_id: int, subject: str, body: str):
    return api_post(
        f"/emails/{email_id}/reply/create",
        json_body={"subject": subject, "body": body},
        timeout=90,
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
    "reply_drafts": {},
    "selected_email_id": None,
    "ctx_light_mode": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================================
# GLOBAL STYLING
# ==========================================================

apply_app_theme("light" if st.session_state.get("ctx_light_mode") else "dark")


# ==========================================================
# LOAD DATA
# ==========================================================

emails = get_emails()
open_commitments = get_commitments()

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

google_connected = google_workspace_connected(current_user())

with st.sidebar:
    render_html_fragment(
        '<div class="ctx-brand"><span class="ctx-logo">CQ</span><div>'
        '<div class="ctx-brand-title">ContextIQ</div>'
        '<div class="ctx-brand-sub">Decision workspace</div></div></div>'
    )

    connection_label = "Google connected" if google_connected else "Google not connected"
    connection_class = "" if google_connected else " off"

    render_html_fragment(
        '<div class="ctx-workspace">'
        f'<div class="ctx-workspace-name">{html.escape(current_user())}</div>'
        '<div class="ctx-workspace-status">'
        f'<span class="ctx-dot{connection_class}"></span>{connection_label}'
        '</div></div>'
    )

    nav_items = [
        "Command Center",
        "Ask ContextIQ",
        "Inbox",
        "Actions",
        "Opportunities",
        "Calendar",
        "CRM",
        "Security",
        "Documents",
    ]

    nav_values = {
        "Command Center": "Dashboard",
        "Ask ContextIQ": "Ask ContextIQ",
        "Inbox": "Intelligent Inbox",
        "Actions": "Action Center",
        "Opportunities": "Opportunity Radar",
        "Calendar": "Calendar",
        "CRM": "CRM Intelligence",
        "Security": "Security Center",
        "Documents": "Attachments",
    }

    display_page = next(
        (key for key, value in nav_values.items() if value == st.session_state.page),
        nav_items[0],
    )

    st.caption("Workspace")
    selected = st.radio(
        "Navigation",
        nav_items,
        index=nav_items.index(display_page),
        label_visibility="collapsed",
    )
    st.session_state.page = nav_values[selected]

    st.divider()

    if google_connected:
        if st.button("Sync Gmail", use_container_width=True, type="primary"):
            with st.spinner("Syncing Gmail…"):
                result = sync_gmail()
            if result:
                imported = result.get("imported", 0)
                skipped_value = result.get("skipped", [])
                skipped = len(skipped_value) if isinstance(skipped_value, list) else skipped_value
                st.toast(f"Imported {imported} · Skipped {skipped}")
                st.session_state.analysis = None
                st.rerun()
    elif google_oauth_configured():
        try:
            st.link_button(
                "Connect Google",
                create_google_authorization_url(),
                use_container_width=True,
                type="primary",
            )
        except Exception:
            st.button("Connect Google", disabled=True, use_container_width=True)
    else:
        st.button("Sync Gmail", disabled=True, use_container_width=True)
        st.caption("Configure Google OAuth to enable sync.")

    side_a, side_b = st.columns(2)
    with side_a:
        if st.button("Analyze", use_container_width=True):
            with st.spinner("Refreshing context…"):
                result = analyze_emails()
            if result:
                st.session_state.analysis = result
                st.rerun()

    with side_b:
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    st.divider()
    st.caption("Appearance")
    st.toggle("Light mode", key="ctx_light_mode")

    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout_user()
        st.rerun()


# ==========================================================
# PRODUCT BAR
# ==========================================================

page_label = next(
    (
        label
        for label, value in {
            "Command Center": "Dashboard",
            "Ask ContextIQ": "Ask ContextIQ",
            "Inbox": "Intelligent Inbox",
            "Actions": "Action Center",
            "Opportunities": "Opportunity Radar",
            "Calendar": "Calendar",
            "CRM": "CRM Intelligence",
            "Security": "Security Center",
            "Documents": "Attachments",
        }.items()
        if value == st.session_state.page
    ),
    "Command Center",
)

st.markdown(
    f"""
    <div class="ctx-topbar">
        <div class="ctx-topbar-path">ContextIQ / {html.escape(page_label)}</div>
        <div class="ctx-topbar-account">{html.escape(current_user())}</div>
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


def page_header(title: str, subtitle: str = "") -> None:
    render_html_fragment(
        f'<div class="ctx-page-head"><div>'
        f'<div class="ctx-page-title">{html.escape(title)}</div>'
        f'<div class="ctx-page-sub">{html.escape(subtitle)}</div>'
        f'</div></div>'
    )


def _graph_label(value: Any) -> str:
    return str(value or "Unknown").strip()[:90]


def render_context_relationship_map(email_item: dict, result: dict) -> None:
    context = result.get("business_context", {}) or {}
    contact = context.get("contact") or {}
    company = context.get("company") or {}
    crm = context.get("crm") or {}
    opportunity = context.get("opportunity") or {}

    nodes = [
        ("Email", email_item.get("subject") or "Untitled"),
        ("Contact", contact.get("name") or email_item.get("sender") or "Unknown"),
        ("Company", company.get("name") or contact.get("company") or "Unlinked"),
        (
            "Account",
            crm.get("stage")
            or crm.get("status")
            or opportunity.get("stage")
            or "No CRM stage",
        ),
    ]

    pieces = []
    for index, (label, value) in enumerate(nodes):
        pieces.append(
            '<div class="ctx-map-node">'
            f'<strong>{html.escape(_graph_label(label))}</strong>'
            f'<span>{html.escape(_graph_label(value))}</span>'
            '</div>'
        )
        if index < len(nodes) - 1:
            pieces.append('<div class="ctx-map-arrow">→</div>')

    render_html_fragment('<div class="ctx-map">' + "".join(pieces) + "</div>")


def render_email_card(
    email_item: dict,
    compact: bool = False,
):
    email_id = email_item.get("id")
    result = analysis_results.get(email_id, {})
    decision = result.get("decision", {}) or {}
    context = result.get("business_context", {}) or {}
    consequence = result.get("consequence", {}) or {}
    company = context.get("company") or {}
    crm = context.get("crm") or {}
    opportunity = context.get("opportunity") or {}
    contact = context.get("contact") or {}
    calendar = context.get("calendar", {}) or {}
    dependency = result.get("process_dependency", {}) or {}

    body_preview = clean_email_body(
        email_item.get("body"),
        max_chars=700 if compact else 1800,
    )

    if compact:
        with st.container(border=True):
            top = st.columns([4.8, 1.1, 1.1])
            with top[0]:
                st.markdown(f"**{email_item.get('subject', 'Untitled email')}**")
                st.caption(email_item.get("sender", "Unknown sender"))
            with top[1]:
                st.metric("Priority", f"{float(email_item.get('priority_score') or 0):.0f}")
            with top[2]:
                st.metric(
                    "Impact",
                    f"{float(consequence.get('score', email_item.get('consequence_score') or 0)):.0f}",
                )
        return

    with st.container(border=True):
        top = st.columns([4.4, 1.15, 1.15, 1.15])
        with top[0]:
            st.markdown(f"### {email_item.get('subject', 'Untitled email')}")
            st.caption(f"From {email_item.get('sender', 'Unknown sender')}")
        with top[1]:
            st.metric("Priority", f"{float(email_item.get('priority_score') or 0):.0f}")
        with top[2]:
            st.metric(
                "Impact",
                f"{float(consequence.get('score', email_item.get('consequence_score') or 0)):.0f}",
            )
        with top[3]:
            st.metric("Trust", percentage(result.get("sender_trust", 0)))

        if body_preview:
            render_html_fragment(
                f'<div class="ctx-email-body">{html.escape(body_preview)}</div>'
            )

        overview_tab, context_tab, actions_tab = st.tabs(
            ["Overview", "Context", "Actions"]
        )

        with overview_tab:
            info = st.columns(3)
            info[0].metric(
                "Intent",
                title_case(result.get("intent", email_item.get("category"))),
            )
            info[1].metric(
                "Decision",
                title_case(decision.get("action_type")),
            )
            info[2].metric(
                "Risk",
                str(decision.get("risk_level", "LOW")).title(),
            )

            consequence_cols = st.columns(4)
            consequence_cols[0].metric(
                "Business impact",
                f"{consequence.get('score', 0)}/100",
            )
            consequence_cols[1].metric(
                "Revenue at risk",
                money(consequence.get("potential_revenue_at_risk")),
            )
            consequence_cols[2].metric(
                "Deadline",
                (
                    f"{consequence.get('deadline_hours')}h"
                    if consequence.get("deadline_hours") is not None
                    else "—"
                ),
            )
            consequence_cols[3].metric(
                "Deal value",
                money(consequence.get("deal_value") or crm.get("deal_value")),
            )

            reasons = consequence.get("reasons", []) or []
            if reasons:
                st.markdown("**Why it matters**")
                for reason in reasons[:5]:
                    st.write(f"• {reason}")

            if dependency.get("is_blocking"):
                st.warning(
                    f"Blocking {dependency.get('blocked_process', 'a downstream process')}: "
                    f"{dependency.get('downstream_impact', 'downstream impact detected')}."
                )
            elif dependency:
                st.caption("No downstream process dependency detected.")

            st.markdown("**Decision rationale**")
            st.write(decision.get("reason", "No decision explanation available."))
            st.caption(
                f"Confidence {percentage(decision.get('confidence', 0))} · "
                f"Risk {decision.get('risk_level', 'LOW')}"
            )

        with context_tab:
            st.markdown("**Relationship map**")
            render_context_relationship_map(email_item, result)

            context_cols = st.columns(4)
            with context_cols[0]:
                st.caption("Contact")
                st.write(contact.get("name", "Unknown"))
                st.caption(contact.get("email", ""))
            with context_cols[1]:
                st.caption("Company")
                st.write(company.get("name", "Not linked"))
                st.caption(company.get("industry", "Industry not available"))
            with context_cols[2]:
                st.caption("CRM")
                st.write(crm.get("stage", crm.get("status", "No record")))
                st.caption(money(crm.get("deal_value")))
            with context_cols[3]:
                st.caption("Opportunity")
                st.write(opportunity.get("title", "No active link"))
                st.caption(money(opportunity.get("value")))

            if calendar.get("meeting_requested"):
                slot = calendar.get("available_slot") or {}
                when = " · ".join(
                    value
                    for value in [
                        str(slot.get("date") or ""),
                        (
                            f"{slot.get('start')}–{slot.get('end')}"
                            if slot.get("start") and slot.get("end")
                            else ""
                        ),
                    ]
                    if value
                )
                st.info(
                    "Meeting intent detected"
                    + (f" · Suggested {when}" if when else "")
                )
            else:
                st.caption("No meeting request detected in this email.")

        with actions_tab:
            insight = st.session_state.business_insights.get(email_id)

            insight_head, insight_action = st.columns([2.5, 1])
            with insight_head:
                st.markdown("**Business insight**")
                st.caption(
                    "Uses connected context and retrieved evidence to explain business impact."
                )
            with insight_action:
                generate_clicked = st.button(
                    "Generate insight",
                    key=f"insight_{email_id}",
                    use_container_width=True,
                )

            if generate_clicked:
                started = time.perf_counter()
                with st.status(
                    "Building business insight…",
                    expanded=False,
                ) as status:
                    status.write("Retrieving relevant business context")
                    generated = generate_email_insight(email_id, result)
                    elapsed = time.perf_counter() - started
                    if generated:
                        generated["latency_seconds"] = round(elapsed, 2)
                        st.session_state.business_insights[email_id] = generated
                        status.update(
                            label=f"Insight ready in {elapsed:.1f}s",
                            state="complete",
                        )
                        st.rerun()
                    else:
                        status.update(
                            label="Insight could not be generated",
                            state="error",
                        )

            insight = st.session_state.business_insights.get(email_id)
            if insight:
                message = str(insight.get("message") or "No insight available.").strip()
                render_html_fragment(
                    f'<div class="ctx-insight">{html.escape(message)}</div>'
                )
                timing = insight.get("timing") or {}
                total_ms = timing.get("total_ms")
                timing_label = (
                    f"{float(total_ms) / 1000:.1f}s"
                    if total_ms is not None
                    else (
                        f"{float(insight.get('latency_seconds')):.1f}s"
                        if insight.get("latency_seconds") is not None
                        else "—"
                    )
                )
                st.caption(
                    f"{insight.get('retrieved_count', 0)} evidence items · "
                    f"{timing_label} · "
                    f"{title_case(insight.get('provider', 'local'))}"
                )

            st.divider()
            st.markdown("**Review & draft reply**")
            st.caption(
                "Prepare a context-aware reply, review it, then create a Gmail draft. "
                "ContextIQ never sends automatically."
            )

            draft = st.session_state.reply_drafts.get(email_id)
            if st.button(
                "Generate reply draft",
                key=f"reply_suggest_{email_id}",
                use_container_width=True,
            ):
                with st.spinner("Drafting from email and business evidence…"):
                    generated = suggest_reply(email_id)
                if generated:
                    st.session_state.reply_drafts[email_id] = generated
                    st.rerun()

            if draft:
                draft_subject = st.text_input(
                    "Draft subject",
                    value=draft.get("subject", ""),
                    key=f"reply_subject_{email_id}",
                )
                draft_body = st.text_area(
                    "Draft body — review before creating",
                    value=draft.get("body", ""),
                    height=180,
                    key=f"reply_body_{email_id}",
                )
                st.caption(
                    f"{title_case(draft.get('provider', 'local'))} · "
                    f"Confidence {percentage(draft.get('confidence', 0))}"
                )
                if st.button(
                    "Approve & create Gmail draft",
                    key=f"reply_create_{email_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Creating draft in Gmail…"):
                        created = create_reply_draft(
                            email_id,
                            draft_subject,
                            draft_body,
                        )
                    if created:
                        st.success(created.get("message", "Draft created in Gmail."))
                        st.session_state.reply_drafts.pop(email_id, None)


# ==========================================================
# DASHBOARD
# ==========================================================

def dashboard_page():
    first_name = (
        str(st.session_state.get("user_name", "")).strip().split(" ")[0]
        or current_user().split("@")[0]
    )

    page_header(
        f"Good to see you, {first_name}.",
        "A concise view of the work, relationships and decisions that need attention.",
    )

    priority_count = sum((e.get("priority_score") or 0) >= 70 for e in emails)
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
    impact_count = sum((e.get("consequence_score") or 0) >= 80 for e in emails)

    metrics = [
        ("Priority", priority_count),
        ("High impact", impact_count),
        ("Commitments", len(open_commitments)),
        ("Approvals", len(pending_actions)),
        ("Opportunities", lead_count),
    ]

    cols = st.columns(5)
    for col, (label, value) in zip(cols, metrics):
        with col:
            render_html_fragment(
                f'<div class="ctx-kpi">'
                f'<div class="ctx-kpi-label">{html.escape(label)}</div>'
                f'<div class="ctx-kpi-value">{value}</div>'
                f'</div>'
            )

    st.markdown("<div style='height:.48rem'></div>", unsafe_allow_html=True)

    attention = []
    for email_item in emails:
        result = analysis_results.get(email_item.get("id"), {})
        consequence = result.get("consequence", {}) or {}
        impact = consequence.get(
            "score",
            email_item.get("consequence_score") or 0,
        ) or 0

        if impact >= 70 or (email_item.get("priority_score") or 0) >= 75:
            attention.append((float(impact), email_item, result))

    attention.sort(key=lambda item: item[0], reverse=True)

    left, right = st.columns([1.62, 1], gap="medium")

    with left:
        st.markdown("**Priority queue**")

        if not attention:
            render_html_fragment(
                '<div class="ctx-panel"><div class="ctx-empty">'
                'Nothing urgent is competing for attention right now.'
                '</div></div>'
            )
        else:
            rows = []
            for impact, email_item, result in attention[:5]:
                decision = result.get("decision", {}) or {}
                action = title_case(decision.get("action_type"))
                subject = html.escape(str(email_item.get("subject") or "Untitled"))
                sender = html.escape(str(email_item.get("sender") or "Unknown sender"))
                rows.append(
                    '<div class="ctx-row"><div class="ctx-row-main">'
                    f'<div class="ctx-row-title">{subject}</div>'
                    f'<div class="ctx-row-sub">{sender} · {html.escape(action)}</div>'
                    '</div>'
                    f'<div class="ctx-score">{impact:.0f}</div></div>'
                )

            render_html_fragment('<div class="ctx-panel">' + "".join(rows) + "</div>")

        if st.button("Open ranked inbox", use_container_width=True):
            st.session_state.page = "Intelligent Inbox"
            st.rerun()

    with right:
        top_r1, top_r2 = st.columns([1.45, 1])

        with top_r1:
            st.markdown("**Today**")

        with top_r2:
            generate_brief = st.button("Build brief", use_container_width=True)

        if generate_brief:
            with st.spinner("Building operating brief…"):
                brief = api_post(
                    "/assistant/ask",
                    json_body={
                        "question": (
                            "What should I prioritize today? Focus on urgent customer or revenue risk, "
                            "open commitments, approvals and upcoming meetings. Keep the answer concise."
                        ),
                        "top_k": 8,
                    },
                    timeout=60,
                )
            if brief:
                st.session_state["morning_brief"] = brief

        brief = st.session_state.get("morning_brief")
        if brief:
            answer = str(brief.get("answer", "")).strip()
            if len(answer) > 520:
                answer = answer[:517].rstrip() + "..."
            render_html_fragment(f'<div class="ctx-brief">{html.escape(answer)}</div>')
            st.markdown("<div style='height:.36rem'></div>", unsafe_allow_html=True)

        commitment_rows = []
        for item in open_commitments[:3]:
            action = html.escape(str(item.get("action_text") or "Commitment"))
            due = item.get("due_at")
            due_label = due[:10] if isinstance(due, str) and due else "No due date"
            commitment_rows.append(
                '<div class="ctx-row"><div class="ctx-row-main">'
                f'<div class="ctx-row-title">{action}</div>'
                f'<div class="ctx-row-sub">{html.escape(title_case(item.get("direction")))}</div>'
                '</div>'
                f'<span class="ctx-pill">{html.escape(due_label)}</span></div>'
            )

        commitment_content = (
            "".join(commitment_rows)
            if commitment_rows
            else '<div class="ctx-empty">No open commitments.</div>'
        )
        render_html_fragment(
            '<div class="ctx-panel"><div class="ctx-panel-title">Open commitments</div>'
            + commitment_content
            + '</div>'
        )

        st.markdown("<div style='height:.32rem'></div>", unsafe_allow_html=True)

        render_html_fragment(
            '<div class="ctx-panel"><div class="ctx-panel-title">Action control</div>'
            '<div class="ctx-row"><div class="ctx-row-main">'
            f'<div class="ctx-row-title">{len(pending_actions)} awaiting approval</div>'
            f'<div class="ctx-row-sub">{len(executed_actions)} actions executed with human approval</div>'
            '</div><span class="ctx-pill">Human-in-loop</span></div></div>'
        )

        if st.button("Review action queue", use_container_width=True):
            st.session_state.page = "Action Center"
            st.rerun()


# ==========================================================
# INTELLIGENT INBOX
# ==========================================================

def inbox_page():
    page_header(
        "Inbox",
        "Rank communication by business impact, urgency and relationship context.",
    )

    if not emails:
        st.info("No emails found for this user.")
        return

    controls = st.columns([1.25, 2.2])
    with controls[0]:
        sort_mode = st.selectbox(
            "Rank by",
            ["Business Impact", "Priority", "Newest"],
            label_visibility="collapsed",
        )
    with controls[1]:
        search_text = st.text_input(
            "Search inbox",
            placeholder="Search sender or subject…",
            label_visibility="collapsed",
        ).strip().lower()

    def sort_key(email_item):
        result = analysis_results.get(email_item.get("id"), {})
        if sort_mode == "Business Impact":
            consequence = result.get("consequence", {}) or {}
            return consequence.get(
                "score",
                email_item.get("consequence_score") or 0,
            ) or 0
        if sort_mode == "Priority":
            return email_item.get("priority_score") or 0
        return email_item.get("received_at", "")

    filtered = []
    for email_item in emails:
        haystack = (
            f"{email_item.get('subject', '')} "
            f"{email_item.get('sender', '')}"
        ).lower()
        if not search_text or search_text in haystack:
            filtered.append(email_item)

    ordered = sorted(filtered, key=sort_key, reverse=True)

    if not ordered:
        st.info("No messages match the current search.")
        return

    valid_ids = [item.get("id") for item in ordered if item.get("id") is not None]
    selected_id = st.session_state.get("selected_email_id")
    if selected_id not in valid_ids:
        st.session_state.selected_email_id = valid_ids[0]
        selected_id = valid_ids[0]

    list_col, detail_col = st.columns([0.82, 1.72], gap="medium")

    with list_col:
        st.caption(f"{len(ordered)} messages")
        for email_item in ordered[:40]:
            email_id = email_item.get("id")
            result = analysis_results.get(email_id, {})
            consequence = result.get("consequence", {}) or {}
            impact = float(
                consequence.get(
                    "score",
                    email_item.get("consequence_score") or 0,
                )
                or 0
            )
            subject = str(email_item.get("subject") or "Untitled email")
            selected = email_id == selected_id

            label = subject if len(subject) <= 42 else subject[:39].rstrip() + "…"
            if st.button(
                label,
                key=f"inbox_select_{email_id}",
                type="primary" if selected else "secondary",
                use_container_width=True,
            ):
                st.session_state.selected_email_id = email_id
                st.rerun()

            sender = str(email_item.get("sender") or "Unknown sender")
            sender = sender if len(sender) <= 42 else sender[:39].rstrip() + "…"
            st.caption(
                f"{sender} · Impact {impact:.0f} · "
                f"Priority {float(email_item.get('priority_score') or 0):.0f}"
            )

    with detail_col:
        selected = next(
            (item for item in ordered if item.get("id") == selected_id),
            ordered[0],
        )
        render_email_card(selected, compact=False)


# ==========================================================
# ACTION CENTER
# ==========================================================

def action_center_page():
    page_header(
        "Actions",
        "Review recommendations, approvals and executed actions in one controlled queue.",
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
            "No recommended actions have been generated yet."
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
    page_header(
        "Opportunities",
        "Track revenue signals, account momentum and risk discovered from connected context.",
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
    page_header(
        "Calendar",
        "Connect meeting intent, suggested availability and account context.",
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
    page_header(
        "CRM",
        "A unified account view across companies, contacts, deal value, stages and communication.",
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
    page_header(
        "Security",
        "Review sender trust, suspicious communication and messages that need security attention.",
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
    page_header(
        "Documents",
        "Review extracted documents alongside their source communication and business context.",
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
    page_header(
        "Ask ContextIQ",
        "Ask decision-oriented questions across connected communication, CRM, documents and calendar evidence.",
    )

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
