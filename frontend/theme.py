import streamlit as st


def apply_app_theme() -> None:
    """Compact dark product shell for ContextIQ."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #07090d;
            --sidebar: #090c11;
            --panel: #0f131a;
            --panel-2: #121720;
            --panel-3: #171d27;
            --text: #f5f7fb;
            --muted: #8e99aa;
            --subtle: #657083;
            --border: #202733;
            --border-2: #2a3341;
            --accent: #6d5dfc;
            --accent-2: #8b7cff;
            --accent-soft: rgba(109,93,252,.13);
            --green: #36c692;
            --amber: #f3b862;
            --red: #f06f73;
        }

        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
        }

        html, body, .stApp {
            background: var(--bg) !important;
            color: var(--text) !important;
        }

        header[data-testid="stHeader"], footer, #MainMenu {
            visibility: hidden;
            height: 0 !important;
        }

        .block-container {
            max-width: 1580px;
            padding: .72rem 1.15rem 2rem 1.15rem !important;
        }

        h1, h2, h3, h4, h5, h6, p, label, span { color: inherit; }

        h1 {
            font-size: 1.72rem !important;
            line-height: 1.08 !important;
            font-weight: 720 !important;
            letter-spacing: -.04em !important;
            margin: 0 !important;
        }

        h2 {
            font-size: 1.22rem !important;
            letter-spacing: -.025em !important;
        }

        h3 {
            font-size: 1rem !important;
            letter-spacing: -.02em !important;
        }

        [data-testid="stCaptionContainer"], .stCaption {
            color: var(--muted) !important;
            font-size: .75rem !important;
        }

        hr {
            border-color: var(--border) !important;
            margin: .75rem 0 !important;
        }

        section[data-testid="stSidebar"] {
            width: 232px !important;
            min-width: 232px !important;
            background: var(--sidebar) !important;
            border-right: 1px solid var(--border) !important;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: .55rem !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding: 0 .55rem 1rem !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] {
            gap: .12rem !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            min-height: 34px !important;
            padding: .35rem .58rem !important;
            border-radius: 8px !important;
            font-size: .79rem !important;
            color: #b3bdca !important;
            transition: background .12s ease, color .12s ease;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: #121720 !important;
            color: #fff !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: #171c28 !important;
            color: white !important;
            box-shadow: inset 2px 0 0 var(--accent);
        }

        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #566171 !important;
            font-size: .64rem !important;
            font-weight: 700 !important;
            letter-spacing: .09em !important;
            text-transform: uppercase !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            box-shadow: none !important;
        }

        [data-testid="stMetric"] {
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: .64rem .72rem !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted) !important;
            font-size: .67rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--text) !important;
            font-size: 1.22rem !important;
            font-weight: 720 !important;
            letter-spacing: -.035em !important;
        }

        .stButton > button,
        .stLinkButton > a,
        .stDownloadButton > button {
            min-height: 2.2rem !important;
            border-radius: 8px !important;
            border: 1px solid var(--border-2) !important;
            background: var(--panel-2) !important;
            color: #e8ecf3 !important;
            font-size: .76rem !important;
            font-weight: 650 !important;
            box-shadow: none !important;
            transition: background .12s ease, border-color .12s ease, transform .12s ease;
        }

        .stButton > button:hover,
        .stLinkButton > a:hover,
        .stDownloadButton > button:hover {
            background: var(--panel-3) !important;
            border-color: #3a4657 !important;
            transform: translateY(-1px);
        }

        .stButton > button[kind="primary"],
        .stLinkButton > a[kind="primary"] {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
            color: white !important;
        }

        button:disabled, [aria-disabled="true"] {
            opacity: .45 !important;
            cursor: not-allowed !important;
        }

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {
            background: #0c1016 !important;
            border-color: var(--border-2) !important;
            border-radius: 8px !important;
            color: var(--text) !important;
        }

        input, textarea {
            color: var(--text) !important;
            caret-color: white !important;
        }

        [data-testid="stExpander"] {
            background: var(--panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
        }

        .ctx-brand {
            display: flex;
            align-items: center;
            gap: .65rem;
            padding: .2rem .25rem .72rem;
        }

        .ctx-logo {
            width: 31px;
            height: 31px;
            border-radius: 9px;
            display: grid;
            place-items: center;
            background: linear-gradient(145deg, #7a6cff, #5544ed);
            color: #fff !important;
            font-size: .72rem;
            font-weight: 800;
            box-shadow: 0 5px 18px rgba(109,93,252,.22);
        }

        .ctx-brand-title {
            color: #fff !important;
            font-size: .94rem;
            font-weight: 720;
            letter-spacing: -.025em;
        }

        .ctx-brand-sub {
            color: #586475 !important;
            font-size: .61rem;
            margin-top: .03rem;
        }

        .ctx-workspace {
            padding: .55rem .62rem;
            border-radius: 9px;
            background: #0e1218;
            border: 1px solid var(--border);
            margin: .1rem 0 .65rem;
        }

        .ctx-workspace-name {
            color: #dce2ea !important;
            font-size: .72rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .ctx-workspace-status {
            display: flex;
            align-items: center;
            gap: .35rem;
            color: #647084 !important;
            font-size: .62rem;
            margin-top: .22rem;
        }

        .ctx-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
            background: var(--green);
        }

        .ctx-dot.off { background: var(--amber); }

        .ctx-topbar {
            height: 42px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            margin: -.72rem -1.15rem .72rem;
            padding: 0 1.15rem;
            background: rgba(7,9,13,.94);
            backdrop-filter: blur(12px);
        }

        .ctx-topbar-path {
            color: #768194 !important;
            font-size: .72rem;
        }

        .ctx-topbar-account {
            color: #9ca7b7 !important;
            font-size: .69rem;
        }

        .ctx-page-head {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .65rem;
        }

        .ctx-page-title {
            color: #f8fafc !important;
            font-size: 1.52rem;
            line-height: 1.08;
            letter-spacing: -.04em;
            font-weight: 730;
        }

        .ctx-page-sub {
            color: #727e90 !important;
            font-size: .73rem;
            margin-top: .18rem;
        }

        .ctx-kpi {
            min-height: 76px;
            padding: .65rem .72rem;
            border-radius: 10px;
            background: var(--panel);
            border: 1px solid var(--border);
        }

        .ctx-kpi-label {
            color: #768194 !important;
            font-size: .65rem;
            font-weight: 600;
        }

        .ctx-kpi-value {
            color: #f7f8fb !important;
            font-size: 1.36rem;
            line-height: 1.05;
            font-weight: 740;
            letter-spacing: -.04em;
            margin-top: .24rem;
        }

        .ctx-panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 11px;
            padding: .72rem .8rem;
        }

        .ctx-panel-title {
            color: #e9edf4 !important;
            font-size: .78rem;
            font-weight: 680;
            margin-bottom: .5rem;
        }

        .ctx-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .65rem;
            min-height: 45px;
            padding: .46rem .08rem;
            border-top: 1px solid #1a2029;
        }

        .ctx-row:first-of-type { border-top: 0; }

        .ctx-row-main { min-width: 0; }

        .ctx-row-title {
            color: #e7ebf1 !important;
            font-size: .74rem;
            font-weight: 630;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 520px;
        }

        .ctx-row-sub {
            color: #657083 !important;
            font-size: .64rem;
            margin-top: .12rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 520px;
        }

        .ctx-score {
            flex: 0 0 auto;
            min-width: 46px;
            text-align: right;
            color: #aaa0ff !important;
            font-size: .72rem;
            font-weight: 700;
        }

        .ctx-pill {
            display: inline-flex;
            align-items: center;
            padding: .2rem .42rem;
            border-radius: 999px;
            background: #171c28;
            border: 1px solid #262f3c;
            color: #9fa9b7 !important;
            font-size: .61rem;
            font-weight: 650;
        }

        .ctx-brief {
            border-left: 2px solid var(--accent);
            background: #0d1118;
            border-radius: 0 9px 9px 0;
            padding: .58rem .7rem;
            color: #bac2cf !important;
            font-size: .7rem;
            line-height: 1.5;
        }

        .ctx-empty {
            color: #626e80 !important;
            font-size: .7rem;
            padding: .55rem .1rem;
        }

        .ctx-email-body {
            border-left: 2px solid #5d53d9;
            padding: .5rem .7rem;
            margin: .35rem 0 .6rem;
            background: #0b0f15;
            border-radius: 0 8px 8px 0;
            line-height: 1.55;
            white-space: pre-wrap;
            color: #aeb7c5 !important;
            font-size: .74rem;
        }

        .ctx-login-wordmark {
            display: inline-flex;
            align-items: center;
            gap: .55rem;
            color: white !important;
            font-size: .92rem;
            font-weight: 720;
        }

        .ctx-login-heading {
            color: white !important;
            font-size: 2.55rem;
            line-height: 1.01;
            letter-spacing: -.055em;
            font-weight: 750;
            max-width: 620px;
            margin: 1.1rem 0 .7rem;
        }

        .ctx-login-copy {
            color: #788497 !important;
            font-size: .84rem;
            line-height: 1.6;
            max-width: 540px;
        }

        .ctx-proof {
            margin-top: 1.35rem;
            max-width: 520px;
        }

        .ctx-proof-row {
            display: flex;
            gap: .6rem;
            padding: .48rem 0;
            border-top: 1px solid #151b24;
        }

        .ctx-proof-row:first-child { border-top: 0; }

        .ctx-proof-index {
            color: #6e60ff !important;
            font-size: .65rem;
            font-weight: 750;
            min-width: 25px;
        }

        .ctx-proof-text strong {
            display: block;
            color: #dfe4eb !important;
            font-size: .74rem;
            margin-bottom: .1rem;
        }

        .ctx-proof-text span {
            color: #616d80 !important;
            font-size: .67rem;
            line-height: 1.4;
        }

        .ctx-login-card-title {
            color: white !important;
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -.03em;
        }

        .ctx-login-card-copy {
            color: #717d8f !important;
            font-size: .72rem;
            line-height: 1.5;
            margin: .2rem 0 .7rem;
        }

        .ctx-oauth-note {
            color: #566274 !important;
            font-size: .62rem;
            line-height: 1.45;
            margin-top: .55rem;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: .7rem !important;
                padding-right: .7rem !important;
            }
            .ctx-login-heading { font-size: 2rem; }
            .ctx-page-head {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_login_theme() -> None:
    apply_app_theme()
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        .block-container {
            max-width: 1080px !important;
            min-height: 100vh;
            padding-top: 2.3rem !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .stLinkButton > a {
            background: #f7f8fa !important;
            color: #11151b !important;
            border-color: #d6dae0 !important;
            min-height: 2.55rem !important;
            font-size: .8rem !important;
        }
        .stLinkButton > a:hover {
            background: #ffffff !important;
            border-color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
