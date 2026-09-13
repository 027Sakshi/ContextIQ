import streamlit as st


DARK = {
    "bg": "#0b1016",
    "sidebar": "#0f151d",
    "panel": "#131a23",
    "panel2": "#18212c",
    "panel3": "#1d2835",
    "text": "#f3f6fb",
    "muted": "#95a1b2",
    "subtle": "#69778a",
    "border": "#263240",
    "border2": "#334154",
    "accent": "#6c5ce7",
    "accent2": "#8c7cf6",
    "accent_soft": "rgba(108,92,231,.14)",
    "green": "#38c793",
    "amber": "#e7ad54",
    "red": "#ef7277",
    "shadow": "0 10px 34px rgba(0,0,0,.18)",
    "topbar": "rgba(11,16,22,.94)",
    "input": "#0f151d",
    "login_button_bg": "#f7f8fa",
    "login_button_text": "#11151b",
}

LIGHT = {
    "bg": "#f5f7fb",
    "sidebar": "#ffffff",
    "panel": "#ffffff",
    "panel2": "#f8fafc",
    "panel3": "#eef2f7",
    "text": "#182235",
    "muted": "#66758a",
    "subtle": "#8a97a8",
    "border": "#dde4ed",
    "border2": "#cbd5e1",
    "accent": "#6557e8",
    "accent2": "#7d6df0",
    "accent_soft": "rgba(101,87,232,.10)",
    "green": "#249b70",
    "amber": "#b9781d",
    "red": "#c94f59",
    "shadow": "0 10px 30px rgba(15,23,42,.07)",
    "topbar": "rgba(245,247,251,.94)",
    "input": "#ffffff",
    "login_button_bg": "#182235",
    "login_button_text": "#ffffff",
}


def apply_app_theme(mode: str = "dark") -> None:
    palette = LIGHT if str(mode).lower() == "light" else DARK

    st.markdown(
        f"""
        <style>
        :root {{
            --bg: {palette["bg"]};
            --sidebar: {palette["sidebar"]};
            --panel: {palette["panel"]};
            --panel-2: {palette["panel2"]};
            --panel-3: {palette["panel3"]};
            --text: {palette["text"]};
            --muted: {palette["muted"]};
            --subtle: {palette["subtle"]};
            --border: {palette["border"]};
            --border-2: {palette["border2"]};
            --accent: {palette["accent"]};
            --accent-2: {palette["accent2"]};
            --accent-soft: {palette["accent_soft"]};
            --green: {palette["green"]};
            --amber: {palette["amber"]};
            --red: {palette["red"]};
            --shadow: {palette["shadow"]};
            --topbar: {palette["topbar"]};
            --input: {palette["input"]};
        }}

        html, body, [class*="css"] {{
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
        }}

        html, body, .stApp {{
            background: var(--bg) !important;
            color: var(--text) !important;
        }}

        header[data-testid="stHeader"], footer, #MainMenu {{
            visibility: hidden;
            height: 0 !important;
        }}

        .block-container {{
            max-width: 1500px;
            padding: .68rem 1.05rem 1.35rem 1.05rem !important;
        }}

        h1, h2, h3, h4, h5, h6, p, label, span {{ color: inherit; }}

        h1 {{
            font-size: 1.48rem !important;
            line-height: 1.08 !important;
            font-weight: 720 !important;
            letter-spacing: -.035em !important;
            margin: 0 !important;
        }}

        h2 {{
            font-size: 1.16rem !important;
            letter-spacing: -.025em !important;
        }}

        h3 {{
            font-size: .96rem !important;
            letter-spacing: -.02em !important;
        }}

        [data-testid="stCaptionContainer"], .stCaption {{
            color: var(--muted) !important;
            font-size: .72rem !important;
        }}

        hr {{
            border-color: var(--border) !important;
            margin: .62rem 0 !important;
        }}

        section[data-testid="stSidebar"] {{
            width: 228px !important;
            min-width: 228px !important;
            background: var(--sidebar) !important;
            border-right: 1px solid var(--border) !important;
        }}

        section[data-testid="stSidebar"] > div {{ padding-top: .52rem !important; }}

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding: 0 .55rem .8rem !important;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: .08rem !important; }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            min-height: 33px !important;
            padding: .32rem .55rem !important;
            border-radius: 8px !important;
            font-size: .77rem !important;
            color: var(--muted) !important;
            transition: background .12s ease, color .12s ease;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: var(--panel-2) !important;
            color: var(--text) !important;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background: var(--accent-soft) !important;
            color: var(--text) !important;
            box-shadow: inset 2px 0 0 var(--accent);
        }}

        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
            color: var(--subtle) !important;
            font-size: .62rem !important;
            font-weight: 700 !important;
            letter-spacing: .08em !important;
            text-transform: uppercase !important;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: var(--shadow) !important;
        }}

        [data-testid="stMetric"] {{
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: .58rem .68rem !important;
            box-shadow: var(--shadow) !important;
        }}

        [data-testid="stMetricLabel"] {{
            color: var(--muted) !important;
            font-size: .65rem !important;
            font-weight: 600 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: var(--text) !important;
            font-size: 1.16rem !important;
            font-weight: 720 !important;
            letter-spacing: -.03em !important;
        }}

        .stButton > button,
        .stLinkButton > a,
        .stDownloadButton > button {{
            min-height: 2.08rem !important;
            border-radius: 8px !important;
            border: 1px solid var(--border-2) !important;
            background: var(--panel-2) !important;
            color: var(--text) !important;
            font-size: .74rem !important;
            font-weight: 650 !important;
            box-shadow: none !important;
            transition: background .12s ease, border-color .12s ease, transform .12s ease;
        }}

        .stButton > button:hover,
        .stLinkButton > a:hover,
        .stDownloadButton > button:hover {{
            background: var(--panel-3) !important;
            border-color: var(--accent) !important;
            transform: translateY(-1px);
        }}

        .stButton > button[kind="primary"],
        .stLinkButton > a[kind="primary"] {{
            background: var(--accent) !important;
            border-color: var(--accent) !important;
            color: #fff !important;
        }}

        button:disabled, [aria-disabled="true"] {{
            opacity: .45 !important;
            cursor: not-allowed !important;
        }}

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {{
            background: var(--input) !important;
            border-color: var(--border-2) !important;
            border-radius: 8px !important;
            color: var(--text) !important;
        }}

        input, textarea {{
            color: var(--text) !important;
            caret-color: var(--text) !important;
        }}

        [data-baseweb="popover"],
        [role="listbox"],
        [data-baseweb="menu"] {{
            background: var(--panel) !important;
            color: var(--text) !important;
        }}

        [data-testid="stExpander"],
        [data-testid="stAlert"] {{
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            color: var(--text) !important;
        }}

        button[data-baseweb="tab"] {{
            color: var(--muted) !important;
            font-size: .73rem !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] {{ color: var(--text) !important; }}

        .ctx-brand {{
            display: flex;
            align-items: center;
            gap: .62rem;
            padding: .18rem .25rem .64rem;
        }}

        .ctx-logo {{
            width: 31px;
            height: 31px;
            border-radius: 9px;
            display: inline-grid;
            place-items: center;
            background: linear-gradient(145deg, #7a6cff, #5544ed);
            color: #fff !important;
            font-size: .7rem;
            font-weight: 800;
            box-shadow: 0 5px 18px rgba(109,93,252,.22);
        }}

        .ctx-brand-title {{
            color: var(--text) !important;
            font-size: .92rem;
            font-weight: 720;
            letter-spacing: -.025em;
        }}

        .ctx-brand-sub {{
            color: var(--subtle) !important;
            font-size: .6rem;
            margin-top: .02rem;
        }}

        .ctx-workspace {{
            padding: .52rem .58rem;
            border-radius: 9px;
            background: var(--panel-2);
            border: 1px solid var(--border);
            margin: .08rem 0 .6rem;
        }}

        .ctx-workspace-name {{
            color: var(--text) !important;
            font-size: .7rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .ctx-workspace-status {{
            display: flex;
            align-items: center;
            gap: .34rem;
            color: var(--muted) !important;
            font-size: .61rem;
            margin-top: .2rem;
        }}

        .ctx-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
            background: var(--green);
        }}

        .ctx-dot.off {{ background: var(--amber); }}

        .ctx-topbar {{
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            margin: -.68rem -1.05rem .66rem;
            padding: 0 1.05rem;
            background: var(--topbar);
            backdrop-filter: blur(12px);
        }}

        .ctx-topbar-path {{
            color: var(--muted) !important;
            font-size: .69rem;
        }}

        .ctx-topbar-account {{
            color: var(--muted) !important;
            font-size: .67rem;
        }}

        .ctx-page-head {{
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .58rem;
        }}

        .ctx-page-title {{
            color: var(--text) !important;
            font-size: 1.38rem;
            line-height: 1.08;
            letter-spacing: -.035em;
            font-weight: 730;
        }}

        .ctx-page-sub {{
            color: var(--muted) !important;
            font-size: .7rem;
            margin-top: .16rem;
        }}

        .ctx-kpi {{
            min-height: 70px;
            padding: .6rem .68rem;
            border-radius: 10px;
            background: var(--panel);
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }}

        .ctx-kpi-label {{
            color: var(--muted) !important;
            font-size: .63rem;
            font-weight: 600;
        }}

        .ctx-kpi-value {{
            color: var(--text) !important;
            font-size: 1.25rem;
            line-height: 1.05;
            font-weight: 740;
            letter-spacing: -.035em;
            margin-top: .22rem;
        }}

        .ctx-panel {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 11px;
            padding: .68rem .76rem;
            box-shadow: var(--shadow);
        }}

        .ctx-panel-title {{
            color: var(--text) !important;
            font-size: .76rem;
            font-weight: 680;
            margin-bottom: .46rem;
        }}

        .ctx-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .62rem;
            min-height: 42px;
            padding: .4rem .04rem;
            border-top: 1px solid var(--border);
        }}

        .ctx-row:first-child {{ border-top: 0; }}
        .ctx-row-main {{ min-width: 0; }}

        .ctx-row-title {{
            color: var(--text) !important;
            font-size: .72rem;
            font-weight: 630;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 520px;
        }}

        .ctx-row-sub {{
            color: var(--muted) !important;
            font-size: .62rem;
            margin-top: .1rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 520px;
        }}

        .ctx-score {{
            flex: 0 0 auto;
            min-width: 42px;
            text-align: right;
            color: var(--accent-2) !important;
            font-size: .7rem;
            font-weight: 700;
        }}

        .ctx-pill {{
            display: inline-flex;
            align-items: center;
            padding: .18rem .4rem;
            border-radius: 999px;
            background: var(--panel-3);
            border: 1px solid var(--border);
            color: var(--muted) !important;
            font-size: .59rem;
            font-weight: 650;
        }}

        .ctx-brief {{
            border-left: 2px solid var(--accent);
            background: var(--panel-2);
            border-radius: 0 9px 9px 0;
            padding: .54rem .64rem;
            color: var(--text) !important;
            font-size: .68rem;
            line-height: 1.48;
        }}

        .ctx-empty {{
            color: var(--muted) !important;
            font-size: .68rem;
            padding: .48rem .08rem;
        }}

        .ctx-email-body {{
            border-left: 2px solid var(--accent);
            padding: .48rem .64rem;
            margin: .32rem 0 .52rem;
            background: var(--panel-2);
            border-radius: 0 8px 8px 0;
            line-height: 1.5;
            white-space: pre-wrap;
            color: var(--text) !important;
            font-size: .72rem;
        }}

        .ctx-map {{
            display: grid;
            grid-template-columns: minmax(130px,1fr) 24px minmax(130px,1fr) 24px minmax(130px,1fr) 24px minmax(130px,1fr);
            align-items: stretch;
            gap: .2rem;
            margin: .35rem 0 .72rem;
        }}

        .ctx-map-node {{
            min-height: 74px;
            padding: .55rem .62rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border-radius: 10px;
            background: var(--panel-2);
            border: 1px solid var(--border-2);
            box-shadow: var(--shadow);
        }}

        .ctx-map-node strong {{
            color: var(--text) !important;
            font-size: .71rem;
            font-weight: 700;
        }}

        .ctx-map-node span {{
            color: var(--muted) !important;
            font-size: .63rem;
            line-height: 1.35;
            margin-top: .14rem;
        }}

        .ctx-map-arrow {{
            display: grid;
            place-items: center;
            color: var(--subtle) !important;
            font-size: 1rem;
        }}

        .ctx-insight {{
            border: 1px solid var(--border);
            background: var(--panel-2);
            border-radius: 10px;
            padding: .62rem .68rem;
            color: var(--text) !important;
            font-size: .72rem;
            line-height: 1.5;
        }}

        .ctx-login-wordmark {{
            display: inline-flex;
            align-items: center;
            gap: .55rem;
            color: var(--text) !important;
            font-size: .92rem;
            font-weight: 720;
        }}

        .ctx-login-heading {{
            color: var(--text) !important;
            font-size: 2.45rem;
            line-height: 1.01;
            letter-spacing: -.055em;
            font-weight: 750;
            max-width: 620px;
            margin: 1.05rem 0 .68rem;
        }}

        .ctx-login-copy {{
            color: var(--muted) !important;
            font-size: .82rem;
            line-height: 1.58;
            max-width: 540px;
        }}

        .ctx-proof {{
            margin-top: 1.25rem;
            max-width: 520px;
        }}

        .ctx-proof-row {{
            display: flex;
            gap: .58rem;
            padding: .44rem 0;
            border-top: 1px solid var(--border);
        }}

        .ctx-proof-row:first-child {{ border-top: 0; }}

        .ctx-proof-index {{
            color: var(--accent) !important;
            font-size: .63rem;
            font-weight: 750;
            min-width: 25px;
        }}

        .ctx-proof-text strong {{
            display: block;
            color: var(--text) !important;
            font-size: .72rem;
            margin-bottom: .08rem;
        }}

        .ctx-proof-text span {{
            color: var(--muted) !important;
            font-size: .65rem;
            line-height: 1.4;
        }}

        .ctx-login-card-title {{
            color: var(--text) !important;
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -.03em;
        }}

        .ctx-login-card-copy {{
            color: var(--muted) !important;
            font-size: .7rem;
            line-height: 1.48;
            margin: .18rem 0 .65rem;
        }}

        .ctx-oauth-note {{
            color: var(--muted) !important;
            font-size: .61rem;
            line-height: 1.4;
            margin-top: .5rem;
        }}

        @media (max-width: 1080px) {{
            .ctx-map {{ grid-template-columns: 1fr; }}
            .ctx-map-arrow {{
                transform: rotate(90deg);
                min-height: 16px;
            }}
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-left: .65rem !important;
                padding-right: .65rem !important;
            }}
            .ctx-login-heading {{ font-size: 1.9rem; }}
            .ctx-page-head {{
                align-items: flex-start;
                flex-direction: column;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_login_theme(mode: str = "dark") -> None:
    apply_app_theme(mode)
    palette = LIGHT if str(mode).lower() == "light" else DARK
    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] {{ display: none !important; }}
        .block-container {{
            max-width: 1080px !important;
            min-height: 100vh;
            padding-top: 2.2rem !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .stLinkButton > a {{
            background: {palette["login_button_bg"]} !important;
            color: {palette["login_button_text"]} !important;
            border-color: {palette["border2"]} !important;
            min-height: 2.5rem !important;
            font-size: .79rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
