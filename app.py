import html
import re

import pandas as pd
import streamlit as st

from db import run_query
from nl_to_sql import generate_sql

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

    /* ---- Dataframe / chart containers ---- */
    [data-testid="stDataFrame"], [data-testid="stArrowVegaLiteChart"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
        padding: 0.25rem;
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------

st.markdown('<div class="eyebrow">GOLD SCHEMA · NATURAL LANGUAGE → SQL</div>', unsafe_allow_html=True)
st.title("📊 Sales NL-to-SQL Chatbot")
st.caption(
    "Ask questions about the sales data warehouse in plain English. "
    "Your question is turned into SQL by Gemini, run against a Postgres "
    "database (Supabase), and returned as a table + chart."
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


# ---- SIDEBAR ----
with st.sidebar:
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


def render_chart(df: pd.DataFrame):
    """Best-effort auto chart: only draws one if the shape clearly suggests it."""
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

    if date_cols:
        x_col = date_cols[0]
        chart_df = df[[x_col, value_col]].set_index(x_col)
        st.line_chart(chart_df)
    elif categorical_cols and df.shape[0] <= 30:
        x_col = categorical_cols[0]
        chart_df = df[[x_col, value_col]].set_index(x_col)
        st.bar_chart(chart_df)
    # otherwise: skip charting silently, table is enough


def handle_question(question: str):
    """Runs the question live with a step-by-step status indicator, then
    stores the result in history. Renders its own chat bubbles for this
    turn so the person sees progress instead of a silent pause."""
    entry = {"question": question, "sql": None, "df": None, "error": None}

    with st.chat_message("user", avatar="🧑‍💻"):
        st.write(question)

    with st.chat_message("assistant", avatar="⚙️"):
        try:
            with st.status("Interpreting your question…", expanded=True) as status:
                sql = generate_sql(question)
                entry["sql"] = sql
                status.update(label="Querying Supabase…", state="running")
                df = run_query(sql)
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
                st.dataframe(df, use_container_width=True)
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
