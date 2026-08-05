import html
import re

import altair as alt
import pandas as pd
import streamlit as st

from db import (
    get_default_engine,
    create_engine_from_url,
    get_dialect_name,
    get_dialect_note,
    introspect_schema,
    run_query,
)
from nl_to_sql import generate_sql, DEFAULT_SCHEMA_DESCRIPTION, DEFAULT_DIALECT_NOTE

st.set_page_config(page_title="Sales NL-to-SQL Chatbot", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# THEME — dark navy "data terminal" look: teal/amber accents, Space Grotesk
# for display type, IBM Plex Sans for body, IBM Plex Mono for SQL/data.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #0B1220;
        --surface: #131B2E;
        --surface-alt: #1B2540;
        --border: #232D45;
        --teal: #22D3B0;
        --amber: #F2A93B;
        --text: #E7ECF5;
        --muted: #8A93A8;
    }

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
        color: var(--text);
    }

    [data-testid="stAppViewContainer"] {
        background: radial-gradient(ellipse 120% 80% at 50% -10%, #16213B 0%, var(--bg) 55%);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] h2 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.78rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--teal);
        font-weight: 600;
        margin-top: 0.5rem;
    }
    [data-testid="stSidebar"] .stButton>button {
        background: var(--surface-alt);
        border: 1px solid var(--border);
        border-left: 3px solid var(--teal);
        border-radius: 8px;
        color: var(--text);
        font-size: 0.85rem;
        text-align: left;
        padding: 0.6rem 0.8rem;
        transition: all 0.15s ease;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background: #223054;
        border-left: 3px solid var(--amber);
        color: #fff;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] hr {
        border-color: var(--border);
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] .stCaption {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.5;
    }

    /* ---- Titles / eyebrow ---- */
    .eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--amber);
        margin-bottom: 0.4rem;
    }
    h1 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #F5F8FF 0%, var(--teal) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.01em;
    }
    [data-testid="stCaptionContainer"] {
        color: var(--muted) !important;
        font-size: 0.95rem;
    }

    /* ---- Chat messages ---- */
    [data-testid="stChatMessage"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
    }

    /* ---- Chat input ---- */
    [data-testid="stChatInput"] textarea {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-family: 'IBM Plex Sans', sans-serif;
    }
    [data-testid="stChatInput"] {
        border-color: var(--border) !important;
    }

    /* ---- Results table (custom, since st.dataframe ignores app theme) ---- */
    .table-wrap {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--surface);
        overflow: auto;
        max-height: 420px;
        margin-bottom: 0.5rem;
    }
    table.data-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.88rem;
    }
    table.data-table thead th {
        position: sticky;
        top: 0;
        background: var(--surface-alt);
        color: var(--teal);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        text-align: left;
        padding: 0.6rem 0.9rem;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
    }
    table.data-table tbody td {
        color: var(--text);
        padding: 0.5rem 0.9rem;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
    }
    table.data-table tbody tr:last-child td {
        border-bottom: none;
    }
    table.data-table tbody tr:hover td {
        background: var(--surface-alt);
    }

    /* ---- Chart container ---- */
    [data-testid="stArrowVegaLiteChart"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem;
        background: var(--surface);
    }

    /* ---- Expander (View generated SQL) ---- */
    [data-testid="stExpander"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--surface);
    }
    [data-testid="stExpander"] summary {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: var(--teal);
    }

    /* ---- SQL terminal window ---- */
    .sql-terminal {
        background: #0D1526;
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
        margin-top: 0.4rem;
    }
    .sql-terminal-bar {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 0.5rem 0.75rem;
        background: var(--surface-alt);
        border-bottom: 1px solid var(--border);
    }
    .sql-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .sql-terminal-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: var(--muted);
        margin-left: 0.5rem;
    }
    .sql-terminal-body {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.6;
        padding: 0.9rem 1.1rem;
        white-space: pre-wrap;
        color: #C9D3E8;
        overflow-x: auto;
    }
    .sql-kw { color: var(--teal); font-weight: 600; }

    /* ---- Alerts ---- */
    [data-testid="stAlert"] {
        border-radius: 10px;
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* ---- Status widget (live "thinking" indicator) ---- */
    [data-testid="stStatusWidget"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stStatusWidget"] p {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.85rem !important;
        color: var(--teal) !important;
    }
    [data-testid="stStatusWidget"] svg {
        color: var(--teal) !important;
    }
    /* ---- Text inputs (connection string field) ---- */
    .stTextInput input {
        background: var(--surface-alt) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
    }
    .stTextInput input:focus {
        border-color: var(--teal) !important;
        box-shadow: 0 0 0 1px var(--teal) !important;
    }

    /* ---- Connection status badge ---- */
    .db-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        padding: 0.3rem 0.6rem;
        border-radius: 20px;
        margin-bottom: 0.5rem;
    }
    .db-badge-connected {
        background: rgba(34, 211, 176, 0.12);
        border: 1px solid var(--teal);
        color: var(--teal);
    }
    .db-badge-default {
        background: rgba(138, 147, 168, 0.12);
        border: 1px solid var(--border);
        color: var(--muted);
    }
    .db-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: currentColor;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------

st.markdown('<div class="eyebrow">NATURAL LANGUAGE → SQL · ANY DATABASE</div>', unsafe_allow_html=True)
st.title("📊 NL-to-SQL Chatbot")
st.caption(
    "Ask questions about your data in plain English. Your question is turned "
    "into SQL by Gemini and run against a database of your choice — "
    "connect your own in the sidebar, or try it on the built-in demo data."
)

SAMPLE_QUESTIONS = [
    "What were the total sales by country?",
    "Who are the top 5 customers by total sales amount?",
    "What are the top 5 best-selling products by quantity?",
    "What is the monthly sales trend for the last year?",
    "What is the average order value by product category?",
]

SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "LEFT JOIN", "INNER JOIN", "JOIN", "ON",
    "GROUP BY", "ORDER BY", "LIMIT", "WITH", "HAVING", "AS", "AND", "OR",
    "DESC", "ASC", "DISTINCT", "IN", "NOT", "NULL", "IS", "BETWEEN",
    "CASE", "WHEN", "THEN", "ELSE", "END", "SUM", "COUNT", "AVG", "MAX", "MIN",
]
_KW_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(SQL_KEYWORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def render_sql_terminal(sql: str, title: str = "query.sql"):
    """Renders SQL inside a styled mock terminal window with light keyword highlighting."""
    escaped = html.escape(sql)
    highlighted = _KW_PATTERN.sub(lambda m: f'<span class="sql-kw">{m.group(0)}</span>', escaped)
    st.markdown(
        f"""
        <div class="sql-terminal">
            <div class="sql-terminal-bar">
                <span class="sql-dot" style="background:#FF5F57;"></span>
                <span class="sql-dot" style="background:#FEBC2E;"></span>
                <span class="sql-dot" style="background:#28C840;"></span>
                <span class="sql-terminal-title">{title}</span>
            </div>
            <div class="sql-terminal-body">{highlighted}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- SESSION STATE for custom DB connection ----
if "custom_engine" not in st.session_state:
    st.session_state["custom_engine"] = None
    st.session_state["custom_schema"] = None
    st.session_state["custom_dialect_note"] = None
    st.session_state["custom_db_label"] = None


def get_active_engine_and_context():
    """Returns (engine, schema_description, dialect_note, label) for whichever
    database is currently active — a connected custom one, or the built-in default."""
    if st.session_state["custom_engine"] is not None:
        return (
            st.session_state["custom_engine"],
            st.session_state["custom_schema"],
            st.session_state["custom_dialect_note"],
            st.session_state["custom_db_label"],
        )
    return (get_default_engine(), DEFAULT_SCHEMA_DESCRIPTION, DEFAULT_DIALECT_NOTE, "Default (Supabase demo data)")


# ---- SIDEBAR ----
with st.sidebar:
    st.header("Connect your database")

    if st.session_state["custom_engine"] is not None:
        st.markdown(
            f'<div class="db-badge db-badge-connected"><span class="db-dot"></span>'
            f'Connected · {st.session_state["custom_db_label"]}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Disconnect", use_container_width=True):
            st.session_state["custom_engine"] = None
            st.session_state["custom_schema"] = None
            st.session_state["custom_dialect_note"] = None
            st.session_state["custom_db_label"] = None
            st.session_state["history"] = []
            st.rerun()

        with st.expander("View detected schema"):
            st.code(st.session_state["custom_schema"], language=None)
    else:
        st.markdown(
            '<div class="db-badge db-badge-default"><span class="db-dot"></span>'
            "Using default demo data</div>",
            unsafe_allow_html=True,
        )
        db_url = st.text_input(
            "Connection string",
            placeholder="postgresql://user:pass@host:port/dbname",
            type="password",
            help=(
                "Postgres: postgresql://user:pass@host:port/dbname\n"
                "MySQL: mysql+pymysql://user:pass@host:port/dbname\n"
                "SQL Server: mssql+pyodbc://user:pass@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server "
                "(requires an ODBC driver installed on the machine running this app — "
                "works locally, may not work on Streamlit Cloud)"
            ),
        )
        if st.button("Connect", use_container_width=True):
            if not db_url.strip():
                st.error("Paste a connection string first.")
            else:
                with st.spinner("Connecting and reading schema…"):
                    try:
                        engine = create_engine_from_url(db_url)
                        schema = introspect_schema(engine)
                        dialect_note = get_dialect_note(engine)
                        dialect_name = get_dialect_name(engine)
                        st.session_state["custom_engine"] = engine
                        st.session_state["custom_schema"] = schema
                        st.session_state["custom_dialect_note"] = dialect_note
                        st.session_state["custom_db_label"] = dialect_name
                        st.session_state["history"] = []
                        st.success("Connected!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't connect: {e}")
        st.caption("Your credentials are used only for this session and are never stored.")

    st.divider()
    if st.session_state["custom_engine"] is None:
        st.header("Try a sample question")
        for q in SAMPLE_QUESTIONS:
            if st.button(q, use_container_width=True):
                st.session_state["pending_question"] = q
        st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state["history"] = []
        st.rerun()

    st.divider()
    st.caption(
        "**About this project**\n\n"
        "This chatbot translates natural-language questions into SQL "
        "queries against a Sales Data Warehouse (bronze/silver/gold "
        "architecture), using Google's Gemini API. Only SELECT queries "
        "are permitted — a safety guardrail blocks any query that could "
        "modify or delete data."
    )

# ---- SESSION STATE ----
if "history" not in st.session_state:
    st.session_state["history"] = []


def is_probably_categorical(series: pd.Series) -> bool:
    return series.dtype == object or pd.api.types.is_bool_dtype(series)


def is_probably_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def is_probably_datelike(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    name = str(series.name).lower()
    return any(token in name for token in ["date", "month", "year", "day"])


CHART_BG = "transparent"
CHART_GRID = "#232D45"
CHART_LABEL = "#8A93A8"
CHART_TITLE = "#E7ECF5"
CHART_TEAL = "#22D3B0"


def render_chart(df: pd.DataFrame):
    """Best-effort auto chart, dark-themed to match the rest of the UI."""
    if df.empty or len(df.columns) < 2:
        return

    numeric_cols = [c for c in df.columns if is_probably_numeric(df[c])]
    date_cols = [c for c in df.columns if is_probably_datelike(df[c])]
    categorical_cols = [
        c for c in df.columns if is_probably_categorical(df[c]) and c not in date_cols
    ]

    if not numeric_cols:
        return  # nothing measurable to plot

    value_col = numeric_cols[0]
    axis_style = dict(labelColor=CHART_LABEL, titleColor=CHART_TITLE, gridColor=CHART_GRID)

    if date_cols:
        x_col = date_cols[0]
        chart = (
            alt.Chart(df[[x_col, value_col]])
            .mark_line(color=CHART_TEAL, point=alt.OverlayMarkDef(color=CHART_TEAL))
            .encode(
                x=alt.X(f"{x_col}:T", axis=alt.Axis(**axis_style)),
                y=alt.Y(f"{value_col}:Q", axis=alt.Axis(**axis_style)),
            )
        )
    elif categorical_cols and df.shape[0] <= 30:
        x_col = categorical_cols[0]
        chart = (
            alt.Chart(df[[x_col, value_col]])
            .mark_bar(color=CHART_TEAL, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X(f"{x_col}:N", axis=alt.Axis(**axis_style), sort="-y"),
                y=alt.Y(f"{value_col}:Q", axis=alt.Axis(**axis_style)),
            )
        )
    else:
        return  # otherwise: skip charting silently, table is enough

    chart = chart.properties(background=CHART_BG).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)


def render_table(df: pd.DataFrame, max_rows: int = 500):
    """Renders results as a dark-themed HTML table matching the rest of the UI
    (Streamlit's built-in dataframe widget ignores the app theme)."""
    total_rows = len(df)
    show_df = df.head(max_rows)
    table_html = show_df.to_html(index=False, border=0, classes="data-table", escape=True, na_rep="—")
    st.markdown(f'<div class="table-wrap">{table_html}</div>', unsafe_allow_html=True)
    if total_rows > max_rows:
        st.caption(f"Showing first {max_rows:,} of {total_rows:,} rows.")


def handle_question(question: str):
    """Runs the question live with a step-by-step status indicator, then
    stores the result in history. Renders its own chat bubbles for this
    turn so the person sees progress instead of a silent pause."""
    entry = {"question": question, "sql": None, "df": None, "error": None}
    engine, schema_description, dialect_note, db_label = get_active_engine_and_context()

    with st.chat_message("user", avatar="🧑‍💻"):
        st.write(question)

    with st.chat_message("assistant", avatar="⚙️"):
        try:
            with st.status("Interpreting your question…", expanded=True) as status:
                sql = generate_sql(question, schema_description, dialect_note)
                entry["sql"] = sql
                status.update(label=f"Querying {db_label}…", state="running")
                df = run_query(sql, engine)
                entry["df"] = df
                status.update(label="Done", state="complete", expanded=False)
        except Exception as e:
            entry["error"] = str(e)

    st.session_state["history"].append(entry)


# ---- RENDER PAST CHAT HISTORY (already resolved, no status needed) ----
for entry in st.session_state["history"]:
    with st.chat_message("user", avatar="🧑‍💻"):
        st.write(entry["question"])

    with st.chat_message("assistant", avatar="⚙️"):
        if entry["error"]:
            st.error(f"Something went wrong: {entry['error']}")
        else:
            df = entry["df"]
            if df is None or df.empty:
                st.info("The query ran successfully but returned no rows.")
            else:
                render_table(df)
                render_chart(df)

        if entry["sql"]:
            with st.expander("View generated SQL"):
                render_sql_terminal(entry["sql"])

# ---- HANDLE SAMPLE QUESTION CLICK ----
if "pending_question" in st.session_state:
    q = st.session_state.pop("pending_question")
    handle_question(q)
    st.rerun()

# ---- CHAT INPUT ----
user_question = st.chat_input("Ask a question about the sales data...")
if user_question:
    handle_question(user_question)
    st.rerun()
